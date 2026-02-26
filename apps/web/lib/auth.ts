import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";

import db from "./db";
import { sendEmail } from "./email";
import { env } from "./env";

const baseUrl = env.BETTER_AUTH_BASE_URL;

export const auth = betterAuth({
  database: drizzleAdapter(db, { provider: "pg" }),
  baseURL: baseUrl, // Add this - tells Better Auth your base URL
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: true,
    sendResetPassword: async ({ user, url }) => {
      await sendEmail({
        to: user.email,
        subject: "Reset your password",
        text: `Click the link to reset your password: ${url}`,
      });
    },
  },
  emailVerification: {
    sendVerificationEmail: async ({ user, url }) => {
      await sendEmail({
        to: user.email,
        subject: "Verify your email address",
        text: `Click the link to verify your email: ${url}`,
      });
    },
    autoSignInAfterVerification: true,
  },
  urls: {
    signIn: new URL("/login", baseUrl).toString(),
    signUp: new URL("/sign", baseUrl).toString(),
    afterVerification: new URL("/", baseUrl).toString(),
    afterPasswordReset: new URL("/login", baseUrl).toString(),
  },
});
