/**
 * DELETE /api/config
 *
 * Reset the current user's configuration to defaults.
 * Requires session authentication.
 */
import { eq } from "drizzle-orm";

import { auth } from "../../../lib/auth";
import db from "../../../lib/db";
import { userConfig } from "../../../lib/db/schema";

export default defineEventHandler(async (event) => {
  const session = await auth.api.getSession({
    headers: event.headers,
  });

  if (!session?.user) {
    throw createError({
      statusCode: 401,
      statusMessage: "Unauthorized",
      message: "You must be logged in to reset your configuration",
    });
  }

  try {
    // Delete existing config (it will be recreated with defaults on next GET)
    await db
      .delete(userConfig)
      .where(eq(userConfig.userId, session.user.id));

    return {
      success: true,
      message: "Configuration reset to defaults",
    };
  }
  catch (error) {
    console.error("Failed to reset user config:", error);
    throw createError({
      statusCode: 500,
      statusMessage: "Internal Server Error",
      message: error instanceof Error ? error.message : "Failed to reset configuration",
    });
  }
});
