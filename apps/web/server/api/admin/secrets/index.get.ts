/**
 * Admin Secrets API - List all secret paths
 * 
 * GET /api/admin/secrets
 * 
 * Returns a list of all available secret paths.
 * Requires admin authentication.
 */

import { getVaultClient } from "~~/server/utils/vault";

export default defineEventHandler(async (event) => {
  // TODO: Add admin authentication check here
  // For now, this endpoint is open - you'll want to add auth middleware

  try {
    const client = getVaultClient();

    // List all top-level secret paths
    const paths = await client.listSecrets("");

    // Return structured response
    return {
      success: true,
      paths: paths.map((path: string) => ({
        path: path.replace(/\/$/, ""), // Remove trailing slash
        isDirectory: path.endsWith("/"),
      })),
      availablePaths: [
        { path: "nuxt", description: "Nuxt-specific secrets (auth, sessions)" },
        { path: "shared", description: "Shared API keys (Resend, etc.)" },
        { path: "python-ai", description: "AI service secrets (OpenAI, Anthropic, Google)" },
        { path: "livekit", description: "LiveKit voice/video secrets" },
        { path: "databases", description: "Database connection strings" },
      ],
    };
  }
  catch (error: any) {
    console.error("[Admin Secrets] Failed to list paths:", error.message);

    throw createError({
      statusCode: 500,
      statusMessage: "Failed to list secret paths",
      message: error.message,
    });
  }
});
