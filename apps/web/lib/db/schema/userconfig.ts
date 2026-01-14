import { sql } from "drizzle-orm";
import { integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

import { user } from "./auth";

/**
 * User configuration stores per-user settings and preferences.
 */
export const userConfig = sqliteTable("user_config", {
  id: text("id").primaryKey(),

  // Associated user
  userId: text("user_id")
    .notNull()
    .unique()
    .references(() => user.id, { onDelete: "cascade" }),

  // Voice assistant settings
  voiceEnabled: integer("voice_enabled", { mode: "boolean" }).default(true),
  preferredVoice: text("preferred_voice").default("alloy"),
  speechRate: integer("speech_rate").default(100), // percentage, 100 = normal

  // AI settings
  systemPrompt: text("system_prompt"),
  instructions: text("instructions"),
  aiModel: text("ai_model").default("gpt-4"),
  temperature: integer("temperature").default(70), // 0-100, maps to 0.0-1.0
  maxTokens: integer("max_tokens").default(2048),

  // Memory settings
  memoryEnabled: integer("memory_enabled", { mode: "boolean" }).default(true),
  contextWindowSize: integer("context_window_size").default(10),

  // Notification preferences
  notificationsEnabled: integer("notifications_enabled", { mode: "boolean" }).default(true),
  emailNotifications: integer("email_notifications", { mode: "boolean" }).default(false),

  // UI preferences
  theme: text("theme", { enum: ["light", "dark", "system"] }).default("system"),
  language: text("language").default("en"),

  // Custom settings (JSON for extensibility)
  customSettings: text("custom_settings", { mode: "json" })
    .$type<Record<string, unknown>>()
    .default({}),

  // Timestamps
  createdAt: integer("created_at", { mode: "timestamp_ms" })
    .default(sql`(cast(unixepoch('subsecond') * 1000 as integer))`)
    .notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" })
    .default(sql`(cast(unixepoch('subsecond') * 1000 as integer))`)
    .$onUpdate(() => new Date())
    .notNull(),
});

export type UserConfig = typeof userConfig.$inferSelect;
export type NewUserConfig = typeof userConfig.$inferInsert;
