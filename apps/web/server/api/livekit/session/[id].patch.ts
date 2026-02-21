/**
 * PATCH /api/livekit/session/[id]
 *
 * Update a LiveKit session (transcript URL, metadata, etc.).
 * Supports both session auth and ephemeral key auth.
 */
import { and, eq } from "drizzle-orm";

import db from "../../../../lib/db";
import { livekitSession } from "../../../../lib/db/schema";
import { getAnyAuth } from "../../../utils/ephemeral-auth";

export default defineEventHandler(async (event) => {
  const auth = await getAnyAuth(event);

  if (!auth) {
    throw createError({
      statusCode: 401,
      statusMessage: "Unauthorized",
      message: "Authentication required",
    });
  }

  const sessionId = getRouterParam(event, "id");

  if (!sessionId) {
    throw createError({
      statusCode: 400,
      statusMessage: "Bad Request",
      message: "Session ID is required",
    });
  }

  const body = await readBody(event);
  const { transcriptUrl, recordingUrl, metadata, status } = body;

  try {
    // Find the session
    const [session] = await db
      .select()
      .from(livekitSession)
      .where(
        and(
          eq(livekitSession.id, sessionId),
          eq(livekitSession.userId, auth.userId),
        ),
      )
      .limit(1);

    if (!session) {
      throw createError({
        statusCode: 404,
        statusMessage: "Not Found",
        message: "Session not found",
      });
    }

    // Prepare update object
    const updates: Record<string, unknown> = {};

    if (transcriptUrl !== undefined) {
      updates.transcriptUrl = transcriptUrl;
    }

    if (recordingUrl !== undefined) {
      updates.recordingUrl = recordingUrl;
    }

    if (status !== undefined) {
      const validStatuses = ["pending", "active", "ended", "failed"];
      if (!validStatuses.includes(status)) {
        throw createError({
          statusCode: 400,
          statusMessage: "Bad Request",
          message: `Invalid status. Must be one of: ${validStatuses.join(", ")}`,
        });
      }
      updates.status = status;

      // Set timing based on status change
      if (status === "active" && !session.startedAt) {
        updates.startedAt = new Date();
      }
      if (status === "ended" && !session.endedAt) {
        updates.endedAt = new Date();
      }
    }

    if (metadata !== undefined) {
      // Merge with existing metadata
      updates.metadata = {
        ...(session.metadata as Record<string, unknown> || {}),
        ...metadata,
      };
    }

    if (Object.keys(updates).length === 0) {
      throw createError({
        statusCode: 400,
        statusMessage: "Bad Request",
        message: "No valid fields to update",
      });
    }

    // Update session
    await db
      .update(livekitSession)
      .set(updates)
      .where(eq(livekitSession.id, sessionId));

    // Fetch updated session
    const [updated] = await db
      .select()
      .from(livekitSession)
      .where(eq(livekitSession.id, sessionId))
      .limit(1);

    return {
      success: true,
      session: {
        id: updated.id,
        roomName: updated.roomName,
        status: updated.status,
        participantName: updated.participantName,
        transcriptUrl: updated.transcriptUrl,
        recordingUrl: updated.recordingUrl,
        metadata: updated.metadata,
        startedAt: updated.startedAt?.toISOString() ?? null,
        endedAt: updated.endedAt?.toISOString() ?? null,
        createdAt: updated.createdAt.toISOString(),
        updatedAt: updated.updatedAt.toISOString(),
      },
    };
  }
  catch (error) {
    if (error instanceof Error && "statusCode" in error) {
      throw error;
    }
    console.error("Failed to update session:", error);
    throw createError({
      statusCode: 500,
      statusMessage: "Internal Server Error",
      message: error instanceof Error ? error.message : "Failed to update session",
    });
  }
});
