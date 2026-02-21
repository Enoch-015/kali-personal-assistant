/**
 * Admin Secrets API - Delete secrets at a path
 * 
 * DELETE /api/admin/secrets/:path
 * 
 * Deletes all secrets at the specified path.
 * ⚠️ WARNING: This is irreversible!
 * 
 * Requires admin authentication.
 * 
 * Query params:
 *   - key=<keyname>: Delete only a specific key (recommended)
 *   - confirm=true: Required to delete entire path
 */

import { getVaultClient } from "~~/server/utils/vault";

export default defineEventHandler(async (event) => {
  // TODO: Add admin authentication check here
  const path = getRouterParam(event, "path");
  const query = getQuery(event);
  const keyToDelete = query.key as string | undefined;
  const confirmed = query.confirm === "true";

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

  try {
    const client = getVaultClient();

    // If a specific key is provided, delete just that key
    if (keyToDelete) {
      // Read existing secrets
      const existingSecrets = await client.getSecret(path, false);

      if (!(keyToDelete in existingSecrets)) {
        throw createError({
          statusCode: 404,
          statusMessage: `Key '${keyToDelete}' not found in '${path}'`,
        });
      }

      // Remove the key
      delete existingSecrets[keyToDelete];

      // Write back without the deleted key
      await client.setSecret(path, existingSecrets);

      console.log(`[Admin Secrets] Deleted key '${keyToDelete}' from '${path}'`);

      return {
        success: true,
        path,
        message: `Key '${keyToDelete}' has been deleted from '${path}'`,
        deletedKey: keyToDelete,
      };
    }

    // Deleting entire path requires confirmation
    if (!confirmed) {
      throw createError({
        statusCode: 400,
        statusMessage: "Deleting entire path requires confirm=true query parameter",
      });
    }

    // Delete the entire path
    await client.deleteSecret(path);

    console.log(`[Admin Secrets] Deleted entire path '${path}'`);

    return {
      success: true,
      path,
      message: `All secrets at '${path}' have been deleted`,
    };
  }
  catch (error: any) {
    // Re-throw createError exceptions
    if (error.statusCode) {
      throw error;
    }

    console.error(`[Admin Secrets] Failed to delete ${path}:`, error.message);

    throw createError({
      statusCode: 500,
      statusMessage: `Failed to delete secrets at ${path}`,
      message: error.message,
    });
  }
});
