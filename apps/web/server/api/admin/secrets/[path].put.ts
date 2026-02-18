/**
 * Admin Secrets API - Replace all secrets at a path
 * 
 * PUT /api/admin/secrets/:path
 * 
 * Completely replaces all secrets at the specified path.
 * ⚠️ WARNING: This overwrites ALL existing secrets at this path!
 * Use PATCH to update individual keys without affecting others.
 * 
 * Requires admin authentication.
 * 
 * Body: { secrets: { key1: "value1", key2: "value2" } }
 */

import { getVaultClient } from "~/server/utils/vault";

export default defineEventHandler(async (event) => {
  // TODO: Add admin authentication check here
  const path = getRouterParam(event, "path");
  const body = await readBody(event);

  if (!path) {
    throw createError({
      statusCode: 400,
      statusMessage: "Path is required",
    });
  }

  // Validate path
  const allowedPaths = ["nuxt", "shared", "python-ai", "livekit", "databases"];
  if (!allowedPaths.includes(path)) {
    throw createError({
      statusCode: 400,
      statusMessage: `Invalid path. Allowed: ${allowedPaths.join(", ")}`,
    });
  }

  // Validate body
  if (!body || !body.secrets || typeof body.secrets !== "object") {
    throw createError({
      statusCode: 400,
      statusMessage: "Body must contain 'secrets' object",
    });
  }

  // Validate secrets - no empty keys, no undefined values
  const secrets = body.secrets;
  for (const [key, value] of Object.entries(secrets)) {
    if (!key || key.trim() === "") {
      throw createError({
        statusCode: 400,
        statusMessage: "Secret keys cannot be empty",
      });
    }
    if (value === undefined) {
      throw createError({
        statusCode: 400,
        statusMessage: `Value for key '${key}' cannot be undefined`,
      });
    }
  }

  try {
    const client = getVaultClient();

    // Write the secrets (full replacement)
    await client.setSecret(path, secrets);

    // Log the action (don't log actual values!)
    console.log(`[Admin Secrets] Replaced secrets at '${path}'. Keys: ${Object.keys(secrets).join(", ")}`);

    return {
      success: true,
      path,
      message: `Secrets at '${path}' have been replaced`,
      keys: Object.keys(secrets),
    };
  }
  catch (error: any) {
    console.error(`[Admin Secrets] Failed to write ${path}:`, error.message);

    throw createError({
      statusCode: 500,
      statusMessage: `Failed to write secrets at ${path}`,
      message: error.message,
    });
  }
});
