import { sql } from "drizzle-orm";
import { jsonb, pgTable, text, timestamp } from "drizzle-orm/pg-core";

import { user } from "./auth";

/**
 * LiveKit sessions track voice/video sessions with metadata
 * like transcript URLs, ephemeral key references, and status.
 */
export const livekitSession = pgTable("livekit_session", {
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
  metadata: jsonb("metadata")
    .$type<Record<string, unknown>>()
    .default(sql`'{}'::jsonb`),

  // Timing
  startedAt: timestamp("started_at", { withTimezone: true, mode: "date" }),
  endedAt: timestamp("ended_at", { withTimezone: true, mode: "date" }),

  // Timestamps
  createdAt: timestamp("created_at", { withTimezone: true, mode: "date" })
    .defaultNow()
    .notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true, mode: "date" })
    .defaultNow()
    .$onUpdate(() => new Date())
    .notNull(),
});

export type LivekitSession = typeof livekitSession.$inferSelect;
export type NewLivekitSession = typeof livekitSession.$inferInsert;
