import { AccessToken, RoomServiceClient } from "livekit-server-sdk";
import crypto from "uncrypto";

import env from "../../lib/env";

// ============================================================
// Configuration
// ============================================================

/**
 * Convert WebSocket URL to HTTP URL for API calls
 */
function getHttpUrlFromWs(wsUrl: string): string {
  return wsUrl.replace(/^ws:/, "http:").replace(/^wss:/, "https:");
}

const LIVEKIT_API_KEY = env.LIVEKIT_API_KEY;
const LIVEKIT_API_SECRET = env.LIVEKIT_API_SECRET;
const LIVEKIT_URL = env.LIVEKIT_URL || "ws://localhost:7880";
// Server-side URL for API calls (defaults to converting WebSocket URL to HTTP)
const LIVEKIT_SERVER_URL = env.LIVEKIT_SERVER_URL || getHttpUrlFromWs(LIVEKIT_URL);

// Log the URLs being used for debugging
console.log("[LiveKit] Client URL:", LIVEKIT_URL);
console.log("[LiveKit] Server URL:", LIVEKIT_SERVER_URL);

// ============================================================
// Types
// ============================================================

export type RoomInfo = {
  name: string;
  sid: string;
  numParticipants: number;
  creationTime: bigint;
  metadata?: string;
};

export type TokenMetadata = {
  participant: string;
  ephemeralKeyId?: string;
  userId?: string;
  sessionId?: string;
  [key: string]: unknown;
};

export type CreateRoomOptions = {
  emptyTimeout?: number; // timeout in seconds
  maxParticipants?: number;
  metadata?: Record<string, unknown>;
};

// ============================================================
// Helpers
// ============================================================

/**
 * Generate a random UUID using Web Crypto API
 */
function generateUUID(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0F) | 0x40; // Version 4
  bytes[8] = (bytes[8] & 0x3F) | 0x80; // Variant 10

  const hex = Array.from(bytes)
    .map(b => b.toString(16).padStart(2, "0"))
    .join("");

  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/**
 * Generate a random room name with optional uniqueness check
 */
function generateRoomName(existing?: Set<string>): string {
  const existingSet = existing || new Set<string>();
  let name = `room-${generateUUID().slice(0, 8)}`;

  while (existingSet.has(name)) {
    name = `room-${generateUUID().slice(0, 8)}`;
  }

  return name;
}

/**
 * Get HTTP URL for server-side API calls
 */
function getHttpUrl(): string {
  return LIVEKIT_SERVER_URL;
}

/**
 * Check if LiveKit credentials are configured
 */
export function isLivekitConfigured(): boolean {
  return !!(LIVEKIT_API_KEY && LIVEKIT_API_SECRET);
}

/**
 * Get the LiveKit WebSocket URL
 */
export function getLivekitUrl(): string {
  return LIVEKIT_URL;
}

// ============================================================
// Room Name Generation
// ============================================================

/**
 * Attempt to generate a unique room name by querying existing rooms from LiveKit.
 * Falls back to purely local generation if API is not available.
 */
export async function generateUniqueRoomName(): Promise<string> {
  if (!isLivekitConfigured()) {
    return generateRoomName();
  }

  try {
    const roomService = new RoomServiceClient(
      getHttpUrl(),
      LIVEKIT_API_KEY!,
      LIVEKIT_API_SECRET!,
    );

    const rooms = await roomService.listRooms();
    const existing = new Set(rooms.map(r => r.name));

    return generateRoomName(existing);
  }
  catch (error) {
    console.warn("Failed to list rooms, using local generation:", error);
    return generateRoomName();
  }
}

// ============================================================
// Token Generation
// ============================================================

/**
 * Build a LiveKit access token using the official SDK.
 * Metadata is JSON encoded and attached; grants limited to provided room with roomJoin permission.
 */
export async function buildLivekitToken(
  room: string,
  participantIdentity: string,
  metadata: TokenMetadata,
): Promise<string> {
  if (!isLivekitConfigured()) {
    throw new Error("LiveKit credentials not configured");
  }

  const at = new AccessToken(LIVEKIT_API_KEY!, LIVEKIT_API_SECRET!, {
    identity: participantIdentity,
    name: metadata.participant || participantIdentity,
    metadata: JSON.stringify(metadata),
  });

  at.addGrant({
    roomJoin: true,
    room,
    canPublish: true,
    canSubscribe: true,
    canPublishData: true,
  });

  // Note: In v2 of livekit-server-sdk, toJwt() is async
  return await at.toJwt();
}

// ============================================================
// Room Management
// ============================================================

/**
 * Create a room explicitly (optional - rooms are auto-created on first join)
 */
export async function createRoom(
  roomName: string,
  options?: CreateRoomOptions,
): Promise<RoomInfo> {
  if (!isLivekitConfigured()) {
    throw new Error("LiveKit credentials not configured");
  }

  const roomService = new RoomServiceClient(
    getHttpUrl(),
    LIVEKIT_API_KEY!,
    LIVEKIT_API_SECRET!,
  );

  const room = await roomService.createRoom({
    name: roomName,
    emptyTimeout: options?.emptyTimeout || 10 * 60, // 10 minutes default
    maxParticipants: options?.maxParticipants || 20,
    metadata: options?.metadata ? JSON.stringify(options.metadata) : undefined,
  });

  return {
    name: room.name,
    sid: room.sid,
    numParticipants: room.numParticipants,
    creationTime: room.creationTime,
    metadata: room.metadata,
  };
}

/**
 * List all active rooms
 */
export async function listRooms(): Promise<RoomInfo[]> {
  if (!isLivekitConfigured()) {
    throw new Error("LiveKit credentials not configured");
  }

  const roomService = new RoomServiceClient(
    getHttpUrl(),
    LIVEKIT_API_KEY!,
    LIVEKIT_API_SECRET!,
  );

  const rooms = await roomService.listRooms();

  return rooms.map(r => ({
    name: r.name,
    sid: r.sid,
    numParticipants: r.numParticipants,
    creationTime: r.creationTime,
    metadata: r.metadata,
  }));
}

/**
 * Get a specific room by name
 */
export async function getRoom(roomName: string): Promise<RoomInfo | null> {
  const rooms = await listRooms();
  return rooms.find(r => r.name === roomName) || null;
}

/**
 * Delete a room
 */
export async function deleteRoom(roomName: string): Promise<void> {
  if (!isLivekitConfigured()) {
    throw new Error("LiveKit credentials not configured");
  }

  const roomService = new RoomServiceClient(
    getHttpUrl(),
    LIVEKIT_API_KEY!,
    LIVEKIT_API_SECRET!,
  );

  await roomService.deleteRoom(roomName);
}

/**
 * Update room metadata
 */
export async function updateRoomMetadata(
  roomName: string,
  metadata: Record<string, unknown>,
): Promise<void> {
  if (!isLivekitConfigured()) {
    throw new Error("LiveKit credentials not configured");
  }

  const roomService = new RoomServiceClient(
    getHttpUrl(),
    LIVEKIT_API_KEY!,
    LIVEKIT_API_SECRET!,
  );

  await roomService.updateRoomMetadata(roomName, JSON.stringify(metadata));
}

// ============================================================
// Participant Management
// ============================================================

/**
 * List participants in a room
 */
export async function listParticipants(roomName: string): Promise<unknown[]> {
  if (!isLivekitConfigured()) {
    throw new Error("LiveKit credentials not configured");
  }

  const roomService = new RoomServiceClient(
    getHttpUrl(),
    LIVEKIT_API_KEY!,
    LIVEKIT_API_SECRET!,
  );

  return await roomService.listParticipants(roomName);
}

/**
 * Remove a participant from a room
 */
export async function removeParticipant(
  roomName: string,
  identity: string,
): Promise<void> {
  if (!isLivekitConfigured()) {
    throw new Error("LiveKit credentials not configured");
  }

  const roomService = new RoomServiceClient(
    getHttpUrl(),
    LIVEKIT_API_KEY!,
    LIVEKIT_API_SECRET!,
  );

  await roomService.removeParticipant(roomName, identity);
}
