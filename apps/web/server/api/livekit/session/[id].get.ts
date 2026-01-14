/**
 * GET /api/livekit/session/[id]
 *
 * Get a specific LiveKit session by ID.
 * Supports both session auth and ephemeral key auth.
 */
import { and, eq } from "drizzle-orm";

import db from "../../../../lib/db";
import { livekitSession } from "../../../../lib/db/schema";
import { getAnyAuth } from "../../../utils/ephemeral-auth";

export default defineEventHandler(async (event) => {
  const auth = getAnyAuth(event);

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

  try {
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

    return {
      success: true,
      session: {
        id: session.id,
        roomName: session.roomName,
        roomSid: session.roomSid,
        status: session.status,
        participantName: session.participantName,
        participantIdentity: session.participantIdentity,
        transcriptUrl: session.transcriptUrl,
        recordingUrl: session.recordingUrl,
        metadata: session.metadata,
        startedAt: session.startedAt?.toISOString() ?? null,
        endedAt: session.endedAt?.toISOString() ?? null,
        createdAt: session.createdAt.toISOString(),
        updatedAt: session.updatedAt.toISOString(),
        duration: session.startedAt && session.endedAt
          ? Math.floor((session.endedAt.getTime() - session.startedAt.getTime()) / 1000)
          : null,
      },
    };
  }
  catch (error) {
    if (error instanceof Error && "statusCode" in error) {
      throw error;
    }
    console.error("Failed to get session:", error);
    throw createError({
      statusCode: 500,
      statusMessage: "Internal Server Error",
      message: error instanceof Error ? error.message : "Failed to get session",
    });
  }
});
