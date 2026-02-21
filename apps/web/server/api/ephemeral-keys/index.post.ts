import type { GenerateKeyOptions } from "../../../lib/ephemeral-keys";

/**
 * POST /api/ephemeral-keys
 *
 * Generate a new ephemeral key for the authenticated user.
 *
 * Request body:
 * {
 *   name?: string;          // Human-readable name
 *   scopes?: string[];      // Permissions (e.g., ["voice:connect", "memory:read"])
 *   ttlSeconds?: number;    // Time-to-live (default: 3600 = 1 hour)
 *   maxUsage?: number;      // Max times the key can be used
 *   metadata?: object;      // Additional context
 * }
 *
 * Response:
 * {
 *   key: string;            // The full key (only returned once!)
 *   id: string;             // Key ID for reference
 *   expiresAt: string;      // ISO timestamp
 *   scopes: string[];
 * }
 */
import { auth } from "../../../lib/auth";
import { generateEphemeralKey } from "../../../lib/ephemeral-keys";

export default defineEventHandler(async (event) => {
  // Require authentication
  const session = await auth.api.getSession({
    headers: event.headers,
  });

  if (!session?.user) {
    throw createError({
      statusCode: 401,
      statusMessage: "Unauthorized",
      message: "You must be logged in to generate ephemeral keys",
    });
  }

  // Parse request body
  const body = await readBody<Partial<GenerateKeyOptions>>(event);

  // Validate scopes (optional: restrict allowed scopes)
  const allowedScopes = [
    "voice:connect",
    "voice:speak",
    "memory:read",
    "memory:write",
    "assistant:query",
    "*", // Admin scope
  ];

  const requestedScopes = body?.scopes ?? [];
  const invalidScopes = requestedScopes.filter(s => !allowedScopes.includes(s));

  if (invalidScopes.length > 0) {
    throw createError({
      statusCode: 400,
      statusMessage: "Bad Request",
      message: `Invalid scopes: ${invalidScopes.join(", ")}`,
    });
  }

  // Validate TTL (max 24 hours for user-generated keys)
  const maxTtl = 24 * 60 * 60; // 24 hours
  const ttlSeconds = Math.min(body?.ttlSeconds ?? 3600, maxTtl);

  // Generate the key
  const result = await generateEphemeralKey({
    name: body?.name,
    scopes: requestedScopes,
    userId: session.user.id,
    ttlSeconds,
    maxUsage: body?.maxUsage,
    metadata: {
      ...body?.metadata,
      createdBy: session.user.email,
      createdVia: "api",
    },
  });

  return {
    key: result.key,
    id: result.id,
    expiresAt: result.expiresAt.toISOString(),
    scopes: result.scopes,
  };
});
