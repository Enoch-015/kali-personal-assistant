import { z } from "zod";

/*
 Centralized environment variable validation.
 Add new env vars here with proper validation to get typed, safe access.
*/

const envSchema = z.object({
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
  TURSO_DATABASE_URL: z.string(),
  TURSO_AUTH_TOKEN: z.string(),
  BETTER_AUTH_SECRET: z.string(),
  BETTER_AUTH_BASE_URL: z
    .string()
    .transform((raw) => {
      // Strip inline comments and extra whitespace, remove trailing slash.
      if (!raw)
        return raw;
      const trimmed = raw.trim();
      // Remove everything after a space followed by # (inline comment) or a # directly.
      const commentIndex = (() => {
        const hash = trimmed.indexOf("#");
        if (hash === -1)
          return -1;
        return hash; // treat any # as start of comment for simplicity
      })();
      const noComment = commentIndex >= 0 ? trimmed.slice(0, commentIndex).trim() : trimmed;
      // Collapse internal whitespace to single spaces then take first whitespace-delimited token
      const firstToken = noComment.replace(/\s+/g, " ").split(" ")[0];
      return (firstToken || "").replace(/\/$/, "");
    })
    .refine(v => !v.includes("..."), {
      message:
        "BETTER_AUTH_BASE_URL contains ellipsis '...' placeholder. Replace it with the real domain (e.g. https://your-codespace-3000.app.github.dev)",
    })
    .refine((v) => {
      try {
        const u = new URL(v);
        return u.protocol === "http:" || u.protocol === "https:";
      }
      catch {
        return false;
      }
    }, { message: "BETTER_AUTH_BASE_URL must be a valid absolute http(s) URL without inline comments" }),
  RESEND_API_KEY: z.string().optional(),
  RESEND_FROM_EMAIL: z.string().optional(),

  // LiveKit configuration
  LIVEKIT_API_KEY: z.string().optional(),
  LIVEKIT_API_SECRET: z.string().optional(),
  LIVEKIT_URL: z.string().default("ws://localhost:7880"),
  // Server-side URL for LiveKit API calls (use localhost in dev containers)
  LIVEKIT_SERVER_URL: z.string().optional(),

  // Vault configuration (AppRole authentication)
  // Default to localhost for local dev; use http://vault-dev:8200 for Docker
  VAULT_ADDR: z.string().default("http://127.0.0.1:8200"),
  VAULT_ROLE_ID: z.string().optional(),
  VAULT_SECRET_ID: z.string().optional(),
});

export type Env = z.infer<typeof envSchema>;

// This dedicated file is allowed to read process.env directly.
// eslint-disable-next-line node/no-process-env
const parsed = envSchema.parse(process.env);

// Extra runtime guard: warn if original value (before transform) had inline comment or spaces
// eslint-disable-next-line node/no-process-env
const original = process.env.BETTER_AUTH_BASE_URL || "";
if (original && original !== parsed.BETTER_AUTH_BASE_URL) {
  console.warn(
    `[env] Sanitized BETTER_AUTH_BASE_URL from '${original}' to '${parsed.BETTER_AUTH_BASE_URL}'. Move any comments to their own line.`,
  );
}

export const env: Env = parsed;

export default env;
