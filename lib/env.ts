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
  BETTER_AUTH_BASE_URL: z.string(),
  // Add more variables as needed, e.g.:
  // API_BASE_URL: z.string().url().optional(),
});

export type Env = z.infer<typeof envSchema>;

// This dedicated file is allowed to read process.env directly.
// eslint-disable-next-line node/no-process-env
export const env: Env = envSchema.parse(process.env);

export default env;
