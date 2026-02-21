/**
 * DELETE /api/mcp/[id]
 *
 * Delete an MCP configuration.
 * Requires session authentication.
 */
import { eq } from "drizzle-orm";

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
      message: "You must be logged in to delete MCP configurations",
    });
  }

  const mcpId = getRouterParam(event, "id");

  if (!mcpId) {
    throw createError({
      statusCode: 400,
      statusMessage: "Bad Request",
      message: "MCP ID is required",
    });
  }

  try {
    // Check if MCP exists
    const [existing] = await db
      .select()
      .from(mcp)
      .where(eq(mcp.id, Number(mcpId)))
      .limit(1);

    if (!existing) {
      throw createError({
        statusCode: 404,
        statusMessage: "Not Found",
        message: "MCP configuration not found",
      });
    }

    await db.delete(mcp).where(eq(mcp.id, Number(mcpId)));

    return {
      success: true,
      message: `MCP configuration "${existing.name}" deleted successfully`,
    };
  }
  catch (error) {
    if (error instanceof Error && "statusCode" in error) {
      throw error;
    }

    console.error("Failed to delete MCP config:", error);
    throw createError({
      statusCode: 500,
      statusMessage: "Internal Server Error",
      message: error instanceof Error ? error.message : "Failed to delete MCP config",
    });
  }
});
