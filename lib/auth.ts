import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";

import db from "./db";
import { sendEmail } from "./email"; // wraps Resend
import { env } from "./env";

// Minimal, default-centric Better Auth configuration using Resend for emails.
const baseUrl = env.BETTER_AUTH_BASE_URL;
const abs = (url: string) => (url.startsWith("http") ? url : new URL(url, baseUrl).toString());

export const auth = betterAuth({
  database: drizzleAdapter(db, { provider: "sqlite" }),
  advanced: { database: { generateId: false } },
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: true,
    sendResetPassword: async ({ user, url }) => {
      const link = abs(url);
      await sendEmail({
        to: user.email,
        subject: "Reset your password",
        text: `Click the link to reset your password: ${link}`,
      });
    },
  },
  emailVerification: {
    sendVerificationEmail: async ({ user, url }) => {
      const link = abs(url);
      await sendEmail({
        to: user.email,
        subject: "Verify your email address",
        text: `Click the link to verify your email: ${link}`,
      });
    },
  },
  urls: {
    signIn: new URL("/login", baseUrl).toString(),
    signUp: new URL("/sign", baseUrl).toString(),
    afterVerification: new URL("/", baseUrl).toString(),
    afterPasswordReset: new URL("/login", baseUrl).toString(),
  },
});
