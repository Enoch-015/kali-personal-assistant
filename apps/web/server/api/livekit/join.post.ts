/**
 * POST /api/livekit/join
 *
 * Generate a room and token in one call (convenience endpoint).
 * Creates ephemeral key automatically and includes it in metadata.
 * Supports both session auth and ephemeral key auth.
 */
import crypto from "uncrypto";

import db from "../../../lib/db";
import { livekitSession } from "../../../lib/db/schema";
import { generateEphemeralKey } from "../../../lib/ephemeral-keys";
import { getAnyAuth } from "../../utils/ephemeral-auth";
import {
  buildLivekitToken,
  createRoom,
  generateUniqueRoomName,
  getLivekitUrl,
  isLivekitConfigured,
} from "../../utils/livekit";

function uint8ArrayToHex(bytes: Uint8Array): string {
  return Array.from(bytes).map(b => b.toString(16).padStart(2, "0")).join("");
}

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

  const body = await readBody(event);
  const {
    participantName,
    metadata = {},
    createNewRoom = true,
    roomName: providedRoomName,
    generateKey = true, // Generate new ephemeral key for this session
    keyTtlSeconds = 3600, // 1 hour default
  } = body;

  if (!participantName) {
    throw createError({
      statusCode: 400,
      statusMessage: "Bad Request",
      message: "participantName is required",
    });
  }

  try {
    // Generate unique room name if not provided
    const roomName = providedRoomName || (await generateUniqueRoomName());

    // Generate session ID
    const sessionIdBytes = crypto.getRandomValues(new Uint8Array(16));
    const sessionId = uint8ArrayToHex(sessionIdBytes);

    // Optionally generate a new ephemeral key for this session
    let ephemeralKey = null;
    let ephemeralKeyId = null;

    if (generateKey && auth.type === "session") {
      const keyResult = await generateEphemeralKey({
        name: `LiveKit session: ${roomName}`,
        scopes: ["livekit", "voice:connect"],
        userId: auth.userId,
        ttlSeconds: keyTtlSeconds,
        metadata: {
          roomName,
          sessionId,
          purpose: "livekit_session",
        },
      });
      ephemeralKey = keyResult.key;
      ephemeralKeyId = keyResult.id;
    }
    else if (auth.type === "ephemeral") {
      // Use existing ephemeral key ID
      ephemeralKeyId = (auth.context as { keyId?: string }).keyId;
    }

    // Optionally create the room explicitly
    if (createNewRoom) {
      await createRoom(roomName, {
        metadata: {
          createdBy: auth.userId,
          sessionId,
          ephemeralKeyId,
          ...metadata,
        },
      });
    }

    // Build token metadata
    const tokenMetadata = {
      participant: participantName,
      userId: auth.userId,
      sessionId,
      ephemeralKeyId,
      authType: auth.type,
      ...metadata,
    };

    // Generate token for the participant
    const participantIdentity = `${auth.userId}-${participantName}`;
    const token = await buildLivekitToken(roomName, participantIdentity, tokenMetadata);

    // Create session record in database
    await db.insert(livekitSession).values({
      id: sessionId,
      roomName,
      userId: auth.userId,
      ephemeralKeyId,
      status: "pending",
      participantName,
      participantIdentity,
      metadata: tokenMetadata,
    });

    return {
      success: true,
      sessionId,
      roomName,
      token,
      url: getLivekitUrl(),
      participantIdentity,
      ...(ephemeralKey && { ephemeralKey }), // Only return if newly generated
      ephemeralKeyId,
    };
  }
  catch (error) {
    console.error("Failed to join room:", error);
    throw createError({
      statusCode: 500,
      statusMessage: "Internal Server Error",
      message: error instanceof Error ? error.message : "Failed to join room",
    });
  }
});
