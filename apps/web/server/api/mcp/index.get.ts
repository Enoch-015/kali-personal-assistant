/**
 * GET /api/mcp
 *
 * List all MCP configurations.
 * Requires session authentication.
 */
import { auth } from "../../../lib/auth";
import db from "../../../lib/db";
import { mcp } from "../../../lib/db/schema";

export default defineEventHandler(async (event) => {
  // Require session auth for admin operations
  const session = await auth.api.getSession({
    headers: event.headers,
  });

  if (!session?.user) {
    throw createError({
      statusCode: 401,
      statusMessage: "Unauthorized",
      message: "You must be logged in to view MCP configurations",
    });
  }

  try {
    const mcpConfigs = await db.select().from(mcp);

    return {
      success: true,
      mcps: mcpConfigs.map(config => ({
        id: config.id,
        url: config.url,
        name: config.name,
        description: config.description,
        isActive: config.isActive === 1,
        createdAt: new Date(config.createdAt).toISOString(),
        updatedAt: new Date(config.updatedAt).toISOString(),
      })),
    };
  }
  catch (error) {
    console.error("Failed to list MCP configs:", error);
    throw createError({
      statusCode: 500,
      statusMessage: "Internal Server Error",
      message: error instanceof Error ? error.message : "Failed to list MCP configs",
    });
  }
});
