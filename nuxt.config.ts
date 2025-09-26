import tailwindcss from "@tailwindcss/vite";

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "2025-07-15",
  devtools: { enabled: true },
  modules: ["@nuxt/eslint", "@nuxt/icon", "shadcn-nuxt", "@nuxt/image"],
  // Ensure we point to the actual CSS file location
  css: ["~/assets/css/main.css"],
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
});
