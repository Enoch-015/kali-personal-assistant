/**
 * GET /api/config
 *
 * Get the current user's configuration.
 * Requires session authentication.
 */
import { eq } from "drizzle-orm";
import crypto from "uncrypto";

import { auth } from "../../../lib/auth";
import db from "../../../lib/db";
import { userConfig } from "../../../lib/db/schema";

function uint8ArrayToHex(bytes: Uint8Array): string {
  return Array.from(bytes).map(b => b.toString(16).padStart(2, "0")).join("");
}

export default defineEventHandler(async (event) => {
  const session = await auth.api.getSession({
    headers: event.headers,
  });

  if (!session?.user) {
    throw createError({
      statusCode: 401,
      statusMessage: "Unauthorized",
      message: "You must be logged in to view your configuration",
    });
  }

  try {
    let [config] = await db
      .select()
      .from(userConfig)
      .where(eq(userConfig.userId, session.user.id))
      .limit(1);

    // If no config exists, create default one
    if (!config) {
      const idBytes = crypto.getRandomValues(new Uint8Array(16));
      const id = uint8ArrayToHex(idBytes);

      await db.insert(userConfig).values({
        id,
        userId: session.user.id,
      });

      [config] = await db
        .select()
        .from(userConfig)
        .where(eq(userConfig.userId, session.user.id))
        .limit(1);
    }

    return {
      success: true,
      config: {
        id: config.id,
        // Voice settings
        voiceEnabled: config.voiceEnabled,
        preferredVoice: config.preferredVoice,
        speechRate: config.speechRate,
        // AI settings
        systemPrompt: config.systemPrompt,
        instructions: config.instructions,
        aiModel: config.aiModel,
        temperature: config.temperature,
        maxTokens: config.maxTokens,
        // Memory settings
        memoryEnabled: config.memoryEnabled,
        contextWindowSize: config.contextWindowSize,
        // Notifications
        notificationsEnabled: config.notificationsEnabled,
        emailNotifications: config.emailNotifications,
        // UI preferences
        theme: config.theme,
        language: config.language,
        // Custom
        customSettings: config.customSettings,
        // Timestamps
        createdAt: config.createdAt.toISOString(),
        updatedAt: config.updatedAt.toISOString(),
      },
    };
  }
  catch (error) {
    console.error("Failed to get user config:", error);
    throw createError({
      statusCode: 500,
      statusMessage: "Internal Server Error",
      message: error instanceof Error ? error.message : "Failed to get configuration",
    });
  }
});
