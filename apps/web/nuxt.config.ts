import tailwindcss from "@tailwindcss/vite";

import "./lib/env";

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "2025-07-15",
  devtools: { enabled: true },
  modules: ["@nuxt/eslint", "@nuxt/icon", "shadcn-nuxt", "@nuxt/image"],
  // Ensure we point to the actual CSS file location
  css: ["~/assets/css/main.css"],

  // Runtime configuration for server-side secrets
  runtimeConfig: {
    // Private (server-only) - these come from environment variables
    // Default to localhost for local dev; use http://vault-dev:8200 for Docker
    vaultAddr: process.env.VAULT_ADDR || "http://127.0.0.1:8200",
    vaultRoleId: process.env.VAULT_ROLE_ID || "",
    vaultSecretId: process.env.VAULT_SECRET_ID || "",

    public: {
      // Public configuration (exposed to client)
      // Do NOT put secrets here
    },
  },

  // Apply DaisyUI base colors to the whole page
  app: {
    head: {
      bodyAttrs: {
        class: "bg-base-100 text-base-content",
      },
    },
  },
  eslint: {
    config: {
      standalone: false,
    },
  },
  vite: {
    plugins: [
      tailwindcss(),
    ],
    // Fix HMR (Hot Module Replacement) WebSocket issues in GitHub Codespaces
    server: {
      hmr: process.env.CODESPACE_NAME
        ? {
            protocol: "wss",
            clientPort: 443,
            path: "/_nuxt/",
          }
        : true,
    },
  },
  shadcn: {
    /**
     * Prefix for all the imported component
     */
    prefix: "",
    /**
     * Directory that the component lives in.
     * @default "./components/ui"
     */
    // Place generated UI components in the Nuxt components directory
    componentDir: "./app/components/ui",
  },
  image: {
    provider: "cloudinary", // 👈 if your service is Cloudinary-compatible
    cloudinary: {
      baseURL: "https://res.cloudinary.com/dqujwuelb/image/upload",
      // OR if using fetch for remote images:
      // baseURL: "https://res.cloudinary.com/YOUR_CLOUD_NAME/image/fetch/",
    },
  },
});
