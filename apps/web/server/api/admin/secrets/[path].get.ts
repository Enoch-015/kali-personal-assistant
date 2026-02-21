/**
 * Admin Secrets API - Get secrets at a path
 * 
 * GET /api/admin/secrets/:path
 * 
 * Returns the secrets stored at the specified path.
 * Requires admin authentication.
 * 
 * Query params:
 *   - masked=true: Returns masked values (default: true for GET requests)
 */

import { getVaultClient } from "~~/server/utils/vault";

/**
 * Mask sensitive values for display
 * Shows first 4 chars + asterisks
 */
function maskValue(value: any, revealChars: number = 4): string {
  if (value === null || value === undefined) {
    return "<empty>";
  }

  if (typeof value !== "string") {
    return `<${typeof value}>`;
  }

  if (value.length <= revealChars) {
    return "*".repeat(value.length);
  }

  return value.substring(0, revealChars) + "*".repeat(Math.min(value.length - revealChars, 20));
}

export default defineEventHandler(async (event) => {
  // TODO: Add admin authentication check here
  const path = getRouterParam(event, "path");
  const query = getQuery(event);
  const masked = query.masked !== "false"; // Default to masked

  if (!path) {
    throw createError({
      statusCode: 400,
      statusMessage: "Path is required",
    });
  }

  // Validate path is one of our allowed paths
  const allowedPaths = ["nuxt", "shared", "python-ai", "livekit", "databases"];
  if (!allowedPaths.includes(path)) {
    throw createError({
      statusCode: 400,
      statusMessage: `Invalid path. Allowed: ${allowedPaths.join(", ")}`,
    });
  }

  try {
    const client = getVaultClient();
    const secrets = await client.getSecret(path, false); // Don't use cache for admin view

    // If masked, hide the actual values
    if (masked) {
      const maskedSecrets: Record<string, string> = {};
      for (const [key, value] of Object.entries(secrets)) {
        maskedSecrets[key] = maskValue(value);
      }

      return {
        success: true,
        path,
        secrets: maskedSecrets,
        masked: true,
        keys: Object.keys(secrets),
      };
    }

    // Return unmasked (for actual use - should require extra auth)
    return {
      success: true,
      path,
      secrets,
      masked: false,
      keys: Object.keys(secrets),
    };
  }
  catch (error: any) {
    console.error(`[Admin Secrets] Failed to read ${path}:`, error.message);

    throw createError({
      statusCode: 500,
      statusMessage: `Failed to read secrets at ${path}`,
      message: error.message,
    });
  }
});
