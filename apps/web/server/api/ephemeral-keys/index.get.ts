/**
 * GET /api/ephemeral-keys
 *
 * List all active ephemeral keys for the authenticated user.
 * Note: The actual key values are NOT returned (they're hashed).
 */
import type { EphemeralKey } from "../../../lib/db/schema";

import { auth } from "../../../lib/auth";
import { getUserKeys } from "../../../lib/ephemeral-keys";

export default defineEventHandler(async (event) => {
  // Require authentication
  const session = await auth.api.getSession({
    headers: event.headers,
  });

  if (!session?.user) {
    throw createError({
      statusCode: 401,
      statusMessage: "Unauthorized",
      message: "You must be logged in to view ephemeral keys",
    });
  }

  const keys = await getUserKeys(session.user.id);

  // Return sanitized key info (no key values)
  return keys.map((key: EphemeralKey) => ({
    id: key.id,
    name: key.name,
    scopes: key.scopes,
    expiresAt: key.expiresAt.toISOString(),
    lastUsedAt: key.lastUsedAt?.toISOString() ?? null,
    usageCount: key.usageCount,
    maxUsage: key.maxUsage,
    createdAt: key.createdAt.toISOString(),
  }));
});
