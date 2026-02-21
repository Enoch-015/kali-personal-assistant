import { hasScope, validateEphemeralKey } from "../../lib/ephemeral-keys";

/**
 * Middleware to validate ephemeral key authentication.
 *
 * This middleware checks for the `X-Ephemeral-Key` header and validates it.
 * If valid, it attaches the user context to the event.
 *
 * Protected routes can check for `event.context.ephemeralAuth` to verify
 * ephemeral key authentication, or use the helper `requireEphemeralAuth`.
 */
export default defineEventHandler(async (event) => {
  const keyValue = getHeader(event, "x-ephemeral-key");

  // No ephemeral key provided - skip this middleware
  // Routes that require ephemeral auth should check event.context.ephemeralAuth
  if (!keyValue) {
    event.context.ephemeralAuth = null;
    return;
  }

  // Extract scope from the route if needed
  // Routes can be prefixed like /api/livekit/* or /api/ai/*
  const path = event.path;
  let requiredScope: string | undefined;

  if (path.startsWith("/api/livekit")) {
    requiredScope = "livekit";
  }
  else if (path.startsWith("/api/ai")) {
    requiredScope = "ai";
  }

  try {
    const result = await validateEphemeralKey(keyValue);

    if (result.valid && result.key) {
      // Check scope if required
      if (requiredScope && !hasScope(result.key, requiredScope)) {
        event.context.ephemeralAuth = null;
        event.context.ephemeralAuthError = "scope_mismatch";
        return;
      }

      // Attach ephemeral auth context to the event
      event.context.ephemeralAuth = {
        userId: result.key.userId,
        keyId: result.key.id,
        scopes: result.key.scopes,
        name: result.key.name,
      };
    }
    else {
      // Invalid key - attach error info but don't block yet
      // Let the route handler decide how to respond
      event.context.ephemeralAuth = null;
      event.context.ephemeralAuthError = result.error;
    }
  }
  catch (error) {
    console.error("Ephemeral key validation error:", error);
    event.context.ephemeralAuth = null;
    event.context.ephemeralAuthError = "validation_failed";
  }
});
