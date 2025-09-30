import { auth } from "../../../lib/auth";

function buildHeaders(event: any) {
  return new Headers(Object.entries(getRequestHeaders(event)) as [string, string][]);
}

export default defineEventHandler(async (event) => {
  const body = await readBody(event);
  const { email, callbackURL } = body || {};
  const data = await auth.api.sendVerificationEmail({
    body: { email, callbackURL },
    headers: buildHeaders(event),
  });
  return data;
});
