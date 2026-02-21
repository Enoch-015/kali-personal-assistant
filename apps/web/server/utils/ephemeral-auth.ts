import type { H3Event } from "h3";

import { auth } from "../../lib/auth";

export type EphemeralAuthContext = {
  userId: string | null;
  keyId: string;
  scopes: string[] | null;
  name: string | null;
};

/**
 * Requires ephemeral key authentication for the current request.
 * Throws a 401 error if no valid ephemeral key is provided.
 *
 * @param event - The H3 event
 * @param requiredScope - Optional specific scope to require
 * @returns The ephemeral auth context
 *
 * @example
 * ```ts
 * export default defineEventHandler(async (event) => {
 *   const auth = requireEphemeralAuth(event);
 *   // auth.userId is now available
 * });
 * ```
 */
export function requireEphemeralAuth(
  event: H3Event,
  requiredScope?: string,
): EphemeralAuthContext {
  const auth = event.context.ephemeralAuth as EphemeralAuthContext | null;
  const error = event.context.ephemeralAuthError as string | undefined;

  if (!auth) {
    const errorMessage = getErrorMessage(error);
    throw createError({
      statusCode: 401,
      statusMessage: "Unauthorized",
      message: errorMessage,
    });
  }

  // Check scope if required
  const scopes = auth.scopes ?? [];
  if (requiredScope && !scopes.includes("*") && !scopes.includes(requiredScope)) {
    throw createError({
      statusCode: 403,
      statusMessage: "Forbidden",
      message: `Ephemeral key does not have required scope: ${requiredScope}`,
    });
  }

  return auth;
}

/**
 * Checks if the request has valid ephemeral key authentication.
 * Does not throw - returns null if not authenticated.
 *
 * @param event - The H3 event
 * @returns The ephemeral auth context or null
 */
export function getEphemeralAuth(event: H3Event): EphemeralAuthContext | null {
  return (event.context.ephemeralAuth as EphemeralAuthContext) || null;
}

/**
 * Checks if the request has either session auth or ephemeral key auth.
 * Useful for routes that accept both authentication methods.
 *
 * @param event - The H3 event
 * @returns Object with auth type and user ID, or null if not authenticated
 */
export async function getAnyAuth(event: H3Event): Promise<{
  type: "session" | "ephemeral";
  userId: string;
  context: EphemeralAuthContext | { session: unknown };
} | null> {
  // Check ephemeral auth first (it's already processed by middleware)
  const ephemeralAuth = getEphemeralAuth(event);
  if (ephemeralAuth?.userId) {
    return {
      type: "ephemeral",
      userId: ephemeralAuth.userId,
      context: ephemeralAuth,
    };
  }

  // Check session auth (from better-auth) - need to call the API
  try {
    const session = await auth.api.getSession({
      headers: event.headers,
    });

    if (session?.user?.id) {
      return {
        type: "session",
        userId: session.user.id,
        context: { session },
      };
    }
  }
  catch {
    // Session retrieval failed, continue to return null
  }

  return null;
}

function getErrorMessage(error?: string): string {
  switch (error) {
    case "invalid_format":
      return "Invalid ephemeral key format";
    case "key_not_found":
      return "Ephemeral key not found or already revoked";
    case "key_expired":
      return "Ephemeral key has expired";
    case "scope_mismatch":
      return "Ephemeral key does not have the required scope";
    case "validation_failed":
      return "Failed to validate ephemeral key";
    default:
      return "Ephemeral key authentication required";
  }
}
