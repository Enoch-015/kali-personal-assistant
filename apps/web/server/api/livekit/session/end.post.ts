/**
 * POST /api/livekit/session/end
 *
 * End a LiveKit session (update status to ended).
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

  const body = await readBody(event);
  const { sessionId, transcriptUrl, recordingUrl, metadata } = body;

  if (!sessionId) {
    throw createError({
      statusCode: 400,
      statusMessage: "Bad Request",
      message: "sessionId is required",
    });
  }

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

    if (session.status === "ended") {
      throw createError({
        statusCode: 400,
        statusMessage: "Bad Request",
        message: "Session has already ended",
      });
    }

    const endedAt = new Date();

    // Merge metadata
    const updatedMetadata = {
      ...(session.metadata as Record<string, unknown> || {}),
      ...(metadata || {}),
    };

    // Update session to ended
    await db
      .update(livekitSession)
      .set({
        status: "ended",
        endedAt,
        transcriptUrl: transcriptUrl || session.transcriptUrl,
        recordingUrl: recordingUrl || session.recordingUrl,
        metadata: updatedMetadata,
      })
      .where(eq(livekitSession.id, sessionId));

    return {
      success: true,
      sessionId,
      status: "ended",
      endedAt: endedAt.toISOString(),
      duration: session.startedAt
        ? Math.floor((endedAt.getTime() - session.startedAt.getTime()) / 1000)
        : null,
      transcriptUrl: transcriptUrl || session.transcriptUrl,
      recordingUrl: recordingUrl || session.recordingUrl,
    };
  }
  catch (error) {
    if (error instanceof Error && "statusCode" in error) {
      throw error;
    }
    console.error("Failed to end session:", error);
    throw createError({
      statusCode: 500,
      statusMessage: "Internal Server Error",
      message: error instanceof Error ? error.message : "Failed to end session",
    });
  }
});
