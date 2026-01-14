/**
 * PATCH /api/config
 *
 * Update the current user's configuration.
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
      message: "You must be logged in to update your configuration",
    });
  }

  const body = await readBody(event);

  try {
    // Check if config exists, create if not
    let [config] = await db
      .select()
      .from(userConfig)
      .where(eq(userConfig.userId, session.user.id))
      .limit(1);

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

    // Build update object with validation
    const updates: Record<string, unknown> = {};

    // Voice settings
    if (body.voiceEnabled !== undefined) {
      updates.voiceEnabled = Boolean(body.voiceEnabled);
    }
    if (body.preferredVoice !== undefined) {
      const validVoices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"];
      if (!validVoices.includes(body.preferredVoice)) {
        throw createError({
          statusCode: 400,
          statusMessage: "Bad Request",
          message: `Invalid voice. Must be one of: ${validVoices.join(", ")}`,
        });
      }
      updates.preferredVoice = body.preferredVoice;
    }
    if (body.speechRate !== undefined) {
      const rate = Number(body.speechRate);
      if (Number.isNaN(rate) || rate < 25 || rate > 400) {
        throw createError({
          statusCode: 400,
          statusMessage: "Bad Request",
          message: "speechRate must be between 25 and 400",
        });
      }
      updates.speechRate = rate;
    }

    // AI settings
    if (body.systemPrompt !== undefined) {
      updates.systemPrompt = body.systemPrompt;
    }
    if (body.instructions !== undefined) {
      updates.instructions = body.instructions;
    }
    if (body.aiModel !== undefined) {
      updates.aiModel = body.aiModel;
    }
    if (body.temperature !== undefined) {
      const temp = Number(body.temperature);
      if (Number.isNaN(temp) || temp < 0 || temp > 100) {
        throw createError({
          statusCode: 400,
          statusMessage: "Bad Request",
          message: "temperature must be between 0 and 100",
        });
      }
      updates.temperature = temp;
    }
    if (body.maxTokens !== undefined) {
      const tokens = Number(body.maxTokens);
      if (Number.isNaN(tokens) || tokens < 1 || tokens > 128000) {
        throw createError({
          statusCode: 400,
          statusMessage: "Bad Request",
          message: "maxTokens must be between 1 and 128000",
        });
      }
      updates.maxTokens = tokens;
    }

    // Memory settings
    if (body.memoryEnabled !== undefined) {
      updates.memoryEnabled = Boolean(body.memoryEnabled);
    }
    if (body.contextWindowSize !== undefined) {
      const size = Number(body.contextWindowSize);
      if (Number.isNaN(size) || size < 1 || size > 100) {
        throw createError({
          statusCode: 400,
          statusMessage: "Bad Request",
          message: "contextWindowSize must be between 1 and 100",
        });
      }
      updates.contextWindowSize = size;
    }

    // Notification settings
    if (body.notificationsEnabled !== undefined) {
      updates.notificationsEnabled = Boolean(body.notificationsEnabled);
    }
    if (body.emailNotifications !== undefined) {
      updates.emailNotifications = Boolean(body.emailNotifications);
    }

    // UI preferences
    if (body.theme !== undefined) {
      const validThemes = ["light", "dark", "system"];
      if (!validThemes.includes(body.theme)) {
        throw createError({
          statusCode: 400,
          statusMessage: "Bad Request",
          message: `Invalid theme. Must be one of: ${validThemes.join(", ")}`,
        });
      }
      updates.theme = body.theme;
    }
    if (body.language !== undefined) {
      updates.language = body.language;
    }

    // Custom settings (merge with existing)
    if (body.customSettings !== undefined) {
      if (typeof body.customSettings !== "object") {
        throw createError({
          statusCode: 400,
          statusMessage: "Bad Request",
          message: "customSettings must be an object",
        });
      }
      updates.customSettings = {
        ...(config.customSettings as Record<string, unknown> || {}),
        ...body.customSettings,
      };
    }

    if (Object.keys(updates).length === 0) {
      throw createError({
        statusCode: 400,
        statusMessage: "Bad Request",
        message: "No valid fields to update",
      });
    }

    // Update config
    await db
      .update(userConfig)
      .set(updates)
      .where(eq(userConfig.userId, session.user.id));

    // Fetch updated config
    const [updated] = await db
      .select()
      .from(userConfig)
      .where(eq(userConfig.userId, session.user.id))
      .limit(1);

    return {
      success: true,
      config: {
        id: updated.id,
        voiceEnabled: updated.voiceEnabled,
        preferredVoice: updated.preferredVoice,
        speechRate: updated.speechRate,
        systemPrompt: updated.systemPrompt,
        instructions: updated.instructions,
        aiModel: updated.aiModel,
        temperature: updated.temperature,
        maxTokens: updated.maxTokens,
        memoryEnabled: updated.memoryEnabled,
        contextWindowSize: updated.contextWindowSize,
        notificationsEnabled: updated.notificationsEnabled,
        emailNotifications: updated.emailNotifications,
        theme: updated.theme,
        language: updated.language,
        customSettings: updated.customSettings,
        createdAt: updated.createdAt.toISOString(),
        updatedAt: updated.updatedAt.toISOString(),
      },
    };
  }
  catch (error) {
    if (error instanceof Error && "statusCode" in error) {
      throw error;
    }
    console.error("Failed to update user config:", error);
    throw createError({
      statusCode: 500,
      statusMessage: "Internal Server Error",
      message: error instanceof Error ? error.message : "Failed to update configuration",
    });
  }
});
