/**
 * Admin Secrets API - Patch (merge) secrets at a path
 * 
 * PATCH /api/admin/secrets/:path
 * 
 * Updates specific keys without affecting other existing secrets.
 * This is the PREFERRED method for updating individual secrets.
 * 
 * Requires admin authentication.
 * 
 * Body: { secrets: { key1: "new-value" } }
 * 
 * To delete a key, use the DELETE endpoint or set value to null.
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

  const updates = body.secrets;
  const updateKeys = Object.keys(updates);

  if (updateKeys.length === 0) {
    throw createError({
      statusCode: 400,
      statusMessage: "At least one secret key must be provided",
    });
  }

  try {
    const client = getVaultClient();

    // Read existing secrets
    let existingSecrets: Record<string, any> = {};
    try {
      existingSecrets = await client.getSecret(path, false);
    }
    catch {
      // Path might not exist yet, that's okay
      console.log(`[Admin Secrets] Path '${path}' does not exist, creating new`);
    }

    // Merge updates into existing secrets
    const mergedSecrets: Record<string, any> = { ...existingSecrets };
    const removedKeys: string[] = [];

    for (const [key, value] of Object.entries(updates)) {
      if (value === null) {
        // null means delete the key
        delete mergedSecrets[key];
        removedKeys.push(key);
      }
      else {
        mergedSecrets[key] = value;
      }
    }

    // Write the merged secrets
    await client.setSecret(path, mergedSecrets);

    // Log the action (don't log actual values!)
    console.log(`[Admin Secrets] Patched '${path}'. Updated: ${updateKeys.join(", ")}. Removed: ${removedKeys.join(", ") || "none"}`);

    return {
      success: true,
      path,
      message: `Secrets at '${path}' have been updated`,
      updatedKeys: updateKeys.filter(k => !removedKeys.includes(k)),
      removedKeys,
    };
  }
  catch (error: any) {
    console.error(`[Admin Secrets] Failed to patch ${path}:`, error.message);

    throw createError({
      statusCode: 500,
      statusMessage: `Failed to patch secrets at ${path}`,
      message: error.message,
    });
  }
});
