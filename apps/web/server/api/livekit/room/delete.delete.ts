/**
 * DELETE /api/livekit/room/delete
 *
 * Delete a LiveKit room by name.
 * Supports both session auth and ephemeral key auth.
 */
import { getAnyAuth } from "../../../utils/ephemeral-auth";
import { deleteRoom, isLivekitConfigured } from "../../../utils/livekit";

export default defineEventHandler(async (event) => {
  // Check for any auth (session or ephemeral key)
  const auth = await getAnyAuth(event);

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

  const query = getQuery(event);
  const { roomName } = query;

  if (!roomName || typeof roomName !== "string") {
    throw createError({
      statusCode: 400,
      statusMessage: "Bad Request",
      message: "roomName query parameter is required",
    });
  }

  try {
    await deleteRoom(roomName);

    return {
      success: true,
      message: `Room ${roomName} deleted successfully`,
    };
  }
  catch (error) {
    console.error("Failed to delete room:", error);
    throw createError({
      statusCode: 500,
      statusMessage: "Internal Server Error",
      message: error instanceof Error ? error.message : "Failed to delete room",
    });
  }
});
