/**
 * GET /api/livekit/session/list
 *
 * List all LiveKit sessions for the authenticated user.
 * Supports both session auth and ephemeral key auth.
 */
import { desc, eq } from "drizzle-orm";

import type { LivekitSession } from "../../../../lib/db/schema";

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

  const query = getQuery(event);
  const { status, limit = "20", offset = "0" } = query;

  try {
    const dbQuery = db
      .select()
      .from(livekitSession)
      .where(eq(livekitSession.userId, auth.userId))
      .orderBy(desc(livekitSession.createdAt))
      .limit(Number(limit))
      .offset(Number(offset));

    // Note: status filter would require additional where clause
    // For simplicity, we filter in-memory if status is provided
    let sessions = await dbQuery;

    if (status && typeof status === "string") {
      sessions = sessions.filter(s => s.status === status);
    }

    return {
      success: true,
      sessions: sessions.map((session: LivekitSession) => ({
        id: session.id,
        roomName: session.roomName,
        status: session.status,
        participantName: session.participantName,
        transcriptUrl: session.transcriptUrl,
        startedAt: session.startedAt?.toISOString() ?? null,
        endedAt: session.endedAt?.toISOString() ?? null,
        createdAt: session.createdAt.toISOString(),
        duration: session.startedAt && session.endedAt
          ? Math.floor((session.endedAt.getTime() - session.startedAt.getTime()) / 1000)
          : null,
      })),
      pagination: {
        limit: Number(limit),
        offset: Number(offset),
      },
    };
  }
  catch (error) {
    console.error("Failed to list sessions:", error);
    throw createError({
      statusCode: 500,
      statusMessage: "Internal Server Error",
      message: error instanceof Error ? error.message : "Failed to list sessions",
    });
  }
});
