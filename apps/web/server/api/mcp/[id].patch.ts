/**
 * PATCH /api/mcp/[id]
 *
 * Update an MCP configuration.
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
      message: "You must be logged in to update MCP configurations",
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

  const body = await readBody(event);
  const { url, name, description, isActive } = body;

  // Validate URL if provided
  if (url !== undefined && !URL.canParse(url)) {
    throw createError({
      statusCode: 400,
      statusMessage: "Bad Request",
      message: "Invalid URL format",
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

    // Build update object
    const updates: Record<string, unknown> = {
      updatedAt: new Date(),
    };

    if (url !== undefined)
      updates.url = url;
    if (name !== undefined)
      updates.name = name;
    if (description !== undefined)
      updates.description = description;
    if (isActive !== undefined)
      updates.isActive = Boolean(isActive);

    await db
      .update(mcp)
      .set(updates)
      .where(eq(mcp.id, Number(mcpId)));

    // Fetch updated record
    const [updated] = await db
      .select()
      .from(mcp)
      .where(eq(mcp.id, Number(mcpId)))
      .limit(1);

    return {
      success: true,
      mcp: {
        id: updated.id,
        url: updated.url,
        name: updated.name,
        description: updated.description,
        isActive: updated.isActive,
        createdAt: updated.createdAt.toISOString(),
        updatedAt: updated.updatedAt.toISOString(),
      },
    };
  }
  catch (error) {
    if (error instanceof Error && "statusCode" in error) {
      throw error;
    }

    // Check for unique constraint violation
    if (error instanceof Error && error.message.includes("UNIQUE")) {
      throw createError({
        statusCode: 409,
        statusMessage: "Conflict",
        message: "An MCP configuration with this URL already exists",
      });
    }

    console.error("Failed to update MCP config:", error);
    throw createError({
      statusCode: 500,
      statusMessage: "Internal Server Error",
      message: error instanceof Error ? error.message : "Failed to update MCP config",
    });
  }
});
