import { sql } from "drizzle-orm";
import { integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

import { user } from "./auth";

/**
 * LiveKit sessions track voice/video sessions with metadata
 * like transcript URLs, ephemeral key references, and status.
 */
export const livekitSession = sqliteTable("livekit_session", {
  id: text("id").primaryKey(),

  // Room information
  roomName: text("room_name").notNull(),
  roomSid: text("room_sid"),

  // Associated user (optional - can be anonymous sessions)
  userId: text("user_id").references(() => user.id, { onDelete: "set null" }),

  // Ephemeral key used for this session
  ephemeralKeyId: text("ephemeral_key_id"),

  // Session status
  status: text("status", { enum: ["pending", "active", "ended", "failed"] })
    .notNull()
    .default("pending"),

  // Participant info
  participantName: text("participant_name"),
  participantIdentity: text("participant_identity"),

  // Transcript and recordings
  transcriptUrl: text("transcript_url"),
  recordingUrl: text("recording_url"),

  // Session metadata (JSON)
  metadata: text("metadata", { mode: "json" }).$type<Record<string, unknown>>().default({}),

  // Timing
  startedAt: integer("started_at", { mode: "timestamp_ms" }),
  endedAt: integer("ended_at", { mode: "timestamp_ms" }),

  // Timestamps
  createdAt: integer("created_at", { mode: "timestamp_ms" })
    .default(sql`(cast(unixepoch('subsecond') * 1000 as integer))`)
    .notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" })
    .default(sql`(cast(unixepoch('subsecond') * 1000 as integer))`)
    .$onUpdate(() => new Date())
    .notNull(),
});

export type LivekitSession = typeof livekitSession.$inferSelect;
export type NewLivekitSession = typeof livekitSession.$inferInsert;
