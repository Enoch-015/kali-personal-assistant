/**
 * GET /api/livekit/room/list
 *
 * List all active LiveKit rooms.
 * Supports both session auth and ephemeral key auth.
 */
import { getAnyAuth } from "../../../utils/ephemeral-auth";
import { isLivekitConfigured, listRooms } from "../../../utils/livekit";

export default defineEventHandler(async (event) => {
  // Check for any auth (session or ephemeral key)
  const auth = getAnyAuth(event);

  if (!auth) {
    throw createError({
      statusCode: 401,
      statusMessage: "Unauthorized",
      message: "Authentication required (session or ephemeral key)",
    });
  }

  if (!isLivekitConfigured()) {
    throw createError({
      statusCode: 503,
      statusMessage: "Service Unavailable",
      message: "LiveKit is not configured",
    });
  }

  try {
    const rooms = await listRooms();

    return {
      success: true,
      rooms: rooms.map(r => ({
        name: r.name,
        sid: r.sid,
        numParticipants: r.numParticipants,
        creationTime: r.creationTime.toString(),
        metadata: r.metadata ? JSON.parse(r.metadata) : null,
      })),
    };
  }
  catch (error) {
    console.error("Failed to list rooms:", error);
    throw createError({
      statusCode: 500,
      statusMessage: "Internal Server Error",
      message: error instanceof Error ? error.message : "Failed to list rooms",
    });
  }
});
