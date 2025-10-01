/* Email sending utility.
 * Uses Resend if RESEND_API_KEY + RESEND_FROM_EMAIL are set, otherwise logs.
 */
import { env } from "./env";

export type SendEmailInput = { to: string; subject: string; text: string; html?: string };

async function sendViaResend(input: SendEmailInput) {
  const { RESEND_API_KEY, RESEND_FROM_EMAIL } = env;
  if (!RESEND_API_KEY || !RESEND_FROM_EMAIL)
    return false;
  const payload = {
    from: RESEND_FROM_EMAIL,
    to: [input.to],
    subject: input.subject,
    text: input.text,
    html: input.html || `<pre>${input.text.replace(/</g, "&lt;")}</pre>`,
  };
  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      console.warn(`[email:resend] Failed status=${res.status}`);
      return false;
    }
    return true;
  }
  catch (e) {
    console.warn("[email:resend] Error", e);
    return false;
  }
}

export async function sendEmail(opts: SendEmailInput): Promise<void> {
  const usedResend = await sendViaResend(opts);
  if (!usedResend) {
    console.warn(`[email:fallback-log] To: ${opts.to}\nSubject: ${opts.subject}\n---\n${opts.text}`);
  }
}
