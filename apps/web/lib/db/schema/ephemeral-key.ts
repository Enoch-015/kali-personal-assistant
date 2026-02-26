import { sql } from "drizzle-orm";
import { integer, jsonb, pgTable, text, timestamp } from "drizzle-orm/pg-core";

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
export const ephemeralKey = pgTable("ephemeral_key", {
  id: text("id").primaryKey(),

  // The actual key value (hashed for security)
  keyHash: text("key_hash").notNull().unique(),

  // Optional prefix for easy identification (e.g., "ek_live_", "ek_test_")
  prefix: text("prefix").notNull().default("ek_"),

  // Human-readable name/purpose
  name: text("name"),

  // Scopes/permissions (JSON array of allowed actions)
  scopes: jsonb("scopes")
    .$type<string[]>()
    .default(sql`'[]'::jsonb`),

  // Associated user (optional - keys can be system-level)
  userId: text("user_id").references(() => user.id, { onDelete: "cascade" }),

  // Expiration
  expiresAt: timestamp("expires_at", { withTimezone: true, mode: "date" }).notNull(),

  // Usage tracking
  lastUsedAt: timestamp("last_used_at", { withTimezone: true, mode: "date" }),
  usageCount: integer("usage_count").notNull().default(0),

  // Optional max usage limit (null = unlimited)
  maxUsage: integer("max_usage"),

  // Revocation
  revokedAt: timestamp("revoked_at", { withTimezone: true, mode: "date" }),

  // Metadata (JSON for additional context)
  metadata: jsonb("metadata")
    .$type<Record<string, unknown>>()
    .default(sql`'{}'::jsonb`),

  // Timestamps
  createdAt: timestamp("created_at", { withTimezone: true, mode: "date" })
    .defaultNow()
    .notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true, mode: "date" })
    .defaultNow()
    .$onUpdate(() => new Date())
    .notNull(),
});

export type EphemeralKey = typeof ephemeralKey.$inferSelect;
export type NewEphemeralKey = typeof ephemeralKey.$inferInsert;
