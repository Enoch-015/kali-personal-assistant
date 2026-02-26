import { sql } from "drizzle-orm";
import { boolean, integer, jsonb, pgTable, text, timestamp } from "drizzle-orm/pg-core";

import { user } from "./auth";

/**
 * User configuration stores per-user settings and preferences.
 */
export const userConfig = pgTable("user_config", {
  id: text("id").primaryKey(),

  // Associated user
  userId: text("user_id")
    .notNull()
    .unique()
    .references(() => user.id, { onDelete: "cascade" }),

  // Voice assistant settings
  voiceEnabled: boolean("voice_enabled").default(true),
  preferredVoice: text("preferred_voice").default("alloy"),
  speechRate: integer("speech_rate").default(100), // percentage, 100 = normal

  // AI settings
  systemPrompt: text("system_prompt"),
  instructions: text("instructions"),
  aiModel: text("ai_model").default("gpt-4"),
  temperature: integer("temperature").default(70), // 0-100, maps to 0.0-1.0
  maxTokens: integer("max_tokens").default(2048),

  // Memory settings
  memoryEnabled: boolean("memory_enabled").default(true),
  contextWindowSize: integer("context_window_size").default(10),

  // Notification preferences
  notificationsEnabled: boolean("notifications_enabled").default(true),
  emailNotifications: boolean("email_notifications").default(false),

  // UI preferences
  theme: text("theme", { enum: ["light", "dark", "system"] }).default("system"),
  language: text("language").default("en"),

  // Custom settings (JSON for extensibility)
  customSettings: jsonb("custom_settings")
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

export type UserConfig = typeof userConfig.$inferSelect;
export type NewUserConfig = typeof userConfig.$inferInsert;
