/**
 * POST /api/livekit/room/create
 *
 * Create a new LiveKit room with a unique name.
 * Supports both session auth and ephemeral key auth.
 */
import { getAnyAuth } from "../../../utils/ephemeral-auth";
import {
  createRoom,
  generateUniqueRoomName,
  getLivekitUrl,
  isLivekitConfigured,
} from "../../../utils/livekit";

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

  const body = await readBody(event);
  const { roomName, emptyTimeout, maxParticipants, metadata = {} } = body;

  try {
    // If no room name provided, generate a unique one
    const finalRoomName = roomName || (await generateUniqueRoomName());

    // Add creator info to room metadata
    const roomMetadata = {
      createdBy: auth.userId,
      authType: auth.type,
      ...(auth.type === "ephemeral" && {
        ephemeralKeyId: (auth.context as { keyId?: string }).keyId,
      }),
      ...metadata,
    };

    const room = await createRoom(finalRoomName, {
      emptyTimeout,
      maxParticipants,
      metadata: roomMetadata,
    });

    return {
      success: true,
      room: {
        name: room.name,
        sid: room.sid,
        creationTime: room.creationTime.toString(),
        metadata: roomMetadata,
      },
      url: getLivekitUrl(),
    };
  }
  catch (error) {
    console.error("Failed to create room:", error);
    throw createError({
      statusCode: 500,
      statusMessage: "Internal Server Error",
      message: error instanceof Error ? error.message : "Failed to create room",
    });
  }
});
