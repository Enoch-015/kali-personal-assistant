// Better Auth client setup for Nuxt (browser only)
import { createAuthClient } from "better-auth/client";

// In case environment base URL differs, we could inject; for now rely on relative fetch.
export const authClient = createAuthClient({
  // default options can be extended here
});

export default defineNuxtPlugin(() => {
  return {
    provide: {
      authClient,
    },
  };
});
