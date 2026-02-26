/**
 * POST /api/mcp
 *
 * Add a new MCP configuration.
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
      message: "You must be logged in to add MCP configurations",
    });
  }

  const body = await readBody(event);
  const { url, name, description, isActive = true } = body;

  if (!url || !name || !description) {
    throw createError({
      statusCode: 400,
      statusMessage: "Bad Request",
      message: "url, name, and description are required",
    });
  }

  // Validate URL format
  if (!URL.canParse(url)) {
    throw createError({
      statusCode: 400,
      statusMessage: "Bad Request",
      message: "Invalid URL format",
    });
  }

  try {
    const [created] = await db.insert(mcp).values({
      url,
      name,
      description,
      isActive: Boolean(isActive),
    }).returning();

    return {
      success: true,
      mcp: {
        id: created.id,
        url: created.url,
        name: created.name,
        description: created.description,
        isActive: created.isActive,
        createdAt: created.createdAt.toISOString(),
        updatedAt: created.updatedAt.toISOString(),
      },
    };
  }
  catch (error) {
    // Check for unique constraint violation
    if (error instanceof Error && error.message.includes("UNIQUE")) {
      throw createError({
        statusCode: 409,
        statusMessage: "Conflict",
        message: "An MCP configuration with this URL already exists",
      });
    }

    console.error("Failed to create MCP config:", error);
    throw createError({
      statusCode: 500,
      statusMessage: "Internal Server Error",
      message: error instanceof Error ? error.message : "Failed to create MCP config",
    });
  }
});
