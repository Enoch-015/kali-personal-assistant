/**
 * POST /api/livekit/token
 *
 * Generate a LiveKit access token for a participant.
 * Supports both session auth and ephemeral key auth.
 */
import { getAnyAuth } from "../../utils/ephemeral-auth";
import {
  buildLivekitToken,
  getLivekitUrl,
  isLivekitConfigured,
} from "../../utils/livekit";

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
  const { roomName, participantName, metadata = {} } = body;

  if (!roomName || !participantName) {
    throw createError({
      statusCode: 400,
      statusMessage: "Bad Request",
      message: "roomName and participantName are required",
    });
  }

  try {
    // Build token metadata including auth info
    const tokenMetadata = {
      participant: participantName,
      userId: auth.userId,
      authType: auth.type,
      ...(auth.type === "ephemeral" && {
        ephemeralKeyId: (auth.context as { keyId?: string }).keyId,
      }),
      ...metadata,
    };

    const token = await buildLivekitToken(
      roomName,
      `${auth.userId}-${participantName}`,
      tokenMetadata,
    );

    return {
      success: true,
      token,
      url: getLivekitUrl(),
      roomName,
      participantIdentity: `${auth.userId}-${participantName}`,
    };
  }
  catch (error) {
    console.error("Failed to generate LiveKit token:", error);
    throw createError({
      statusCode: 500,
      statusMessage: "Internal Server Error",
      message: error instanceof Error ? error.message : "Failed to generate token",
    });
  }
});
