import { eq } from "drizzle-orm";

/**
 * DELETE /api/ephemeral-keys/:id
 *
 * Revoke an ephemeral key by ID.
 */
import { auth } from "../../../lib/auth";
import db from "../../../lib/db";
import { ephemeralKey } from "../../../lib/db/schema";
import { revokeEphemeralKey } from "../../../lib/ephemeral-keys";

export default defineEventHandler(async (event) => {
  // Require authentication
  const session = await auth.api.getSession({
    headers: event.headers,
  });

  if (!session?.user) {
    throw createError({
      statusCode: 401,
      statusMessage: "Unauthorized",
      message: "You must be logged in to revoke ephemeral keys",
    });
  }

  const keyId = getRouterParam(event, "id");

  if (!keyId) {
    throw createError({
      statusCode: 400,
      statusMessage: "Bad Request",
      message: "Key ID is required",
    });
  }

  // Check if the key belongs to the user
  const [key] = await db
    .select()
    .from(ephemeralKey)
    .where(eq(ephemeralKey.id, keyId))
    .limit(1);

  if (!key) {
    throw createError({
      statusCode: 404,
      statusMessage: "Not Found",
      message: "Key not found",
    });
  }

  if (key.userId !== session.user.id) {
    throw createError({
      statusCode: 403,
      statusMessage: "Forbidden",
      message: "You can only revoke your own keys",
    });
  }

  const revoked = await revokeEphemeralKey(keyId);

  if (!revoked) {
    throw createError({
      statusCode: 400,
      statusMessage: "Bad Request",
      message: "Key already revoked or not found",
    });
  }

  return { success: true, message: "Key revoked" };
});
