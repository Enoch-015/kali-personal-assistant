/**
 * Vault Server Plugin
 *
 * Initializes Vault client on server startup and attaches secrets to event context.
 * Secrets are refreshed periodically and cached for performance.
 *
 * Usage in API routes:
 *   export default defineEventHandler(async (event) => {
 *     const secrets = event.context.vault;
 *     const apiKey = secrets?.nuxt?.['some-api-key'];
 *   })
 */

import { getVaultClient, type VaultSecrets } from "../utils/vault";

// Extend H3Event context type
declare module "h3" {
  interface H3EventContext {
    vault?: VaultSecrets;
  }
}

let vaultInitialized = false;
let cachedSecrets: VaultSecrets | null = null;
let lastRefresh = 0;
const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

/**
 * Refresh secrets from Vault
 */
async function refreshSecrets(): Promise<VaultSecrets | null> {
  try {
    const client = getVaultClient();

    // Fetch all secret paths in parallel
    const [nuxt, shared, livekit] = await Promise.all([
      client.getSecret("nuxt").catch(() => ({})),
      client.getSecret("shared").catch(() => ({})),
      client.getSecret("livekit").catch(() => ({})),
    ]);

    cachedSecrets = { nuxt, shared, livekit };
    lastRefresh = Date.now();

    console.log("[Vault] Secrets refreshed successfully");
    return cachedSecrets;
  }
  catch (error) {
    console.error("[Vault] Failed to refresh secrets:", error);
    return cachedSecrets; // Return cached on error
  }
}

/**
 * Get secrets, refreshing if needed
 */
async function getSecrets(): Promise<VaultSecrets | null> {
  const now = Date.now();

  // Refresh if stale or not initialized
  if (!cachedSecrets || now - lastRefresh > REFRESH_INTERVAL) {
    return await refreshSecrets();
  }

  return cachedSecrets;
}

export default defineNitroPlugin((nitroApp) => {
  const config = useRuntimeConfig();

  // Check if Vault is configured
  if (!config.vaultRoleId || !config.vaultSecretId) {
    console.warn(
      "[Vault] AppRole credentials not configured. "
        + "Set VAULT_ROLE_ID and VAULT_SECRET_ID environment variables.",
    );
    console.warn("[Vault] Vault integration disabled - secrets will not be available.");
    return;
  }

  console.log("[Vault] Initializing Vault integration...");
  console.log(`[Vault] Connecting to: ${config.vaultAddr}`);

  // Initialize on first request (lazy initialization)
  nitroApp.hooks.hook("request", async (event) => {
    // Skip for static assets and internal routes
    const path = event.path;
    if (
      path.startsWith("/_nuxt")
      || path.startsWith("/__nuxt")
      || path.endsWith(".js")
      || path.endsWith(".css")
      || path.endsWith(".ico")
    ) {
      return;
    }

    try {
      // Initialize Vault client on first request
      if (!vaultInitialized) {
        console.log("[Vault] First request - initializing client...");
        await refreshSecrets();
        vaultInitialized = true;
      }

      // Attach secrets to event context
      const secrets = await getSecrets();
      event.context.vault = secrets || undefined;
    }
    catch (error) {
      console.error("[Vault] Error attaching secrets to request:", error);
      // Don't throw - allow request to continue without secrets
    }
  });

  // Cleanup on shutdown
  nitroApp.hooks.hook("close", async () => {
    console.log("[Vault] Shutting down Vault integration...");
    cachedSecrets = null;
    vaultInitialized = false;
  });

  console.log("[Vault] Plugin registered successfully");
});
