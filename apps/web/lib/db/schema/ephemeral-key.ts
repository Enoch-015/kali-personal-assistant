import { sql } from "drizzle-orm";
import { integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

import { user } from "./auth";

/**
 * Ephemeral keys are short-lived tokens used for authenticating
 * API requests without requiring full session authentication.
 *
 * Use cases:
 * - Voice agent authentication
 * - Temporary API access
 * - WebSocket connection tokens
 * - Cross-service communication
 */
export const ephemeralKey = sqliteTable("ephemeral_key", {
  id: text("id").primaryKey(),

  // The actual key value (hashed for security)
  keyHash: text("key_hash").notNull().unique(),

  // Optional prefix for easy identification (e.g., "ek_live_", "ek_test_")
  prefix: text("prefix").notNull().default("ek_"),

  // Human-readable name/purpose
  name: text("name"),

  // Scopes/permissions (JSON array of allowed actions)
  scopes: text("scopes", { mode: "json" }).$type<string[]>().default([]),

  // Associated user (optional - keys can be system-level)
  userId: text("user_id").references(() => user.id, { onDelete: "cascade" }),

  // Expiration
  expiresAt: integer("expires_at", { mode: "timestamp_ms" }).notNull(),

  // Usage tracking
  lastUsedAt: integer("last_used_at", { mode: "timestamp_ms" }),
  usageCount: integer("usage_count").notNull().default(0),

  // Optional max usage limit (null = unlimited)
  maxUsage: integer("max_usage"),

  // Revocation
  revokedAt: integer("revoked_at", { mode: "timestamp_ms" }),

  // Metadata (JSON for additional context)
  metadata: text("metadata", { mode: "json" }).$type<Record<string, unknown>>().default({}),

  // Timestamps
  createdAt: integer("created_at", { mode: "timestamp_ms" })
    .default(sql`(cast(unixepoch('subsecond') * 1000 as integer))`)
    .notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" })
    .default(sql`(cast(unixepoch('subsecond') * 1000 as integer))`)
    .$onUpdate(() => new Date())
    .notNull(),
});

export type EphemeralKey = typeof ephemeralKey.$inferSelect;
export type NewEphemeralKey = typeof ephemeralKey.$inferInsert;
