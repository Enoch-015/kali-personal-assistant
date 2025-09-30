import { auth } from "../../../lib/auth";

function buildHeaders(event: any) {
  return new Headers(Object.entries(getRequestHeaders(event)) as [string, string][]);
}

export default defineEventHandler(async (event) => {
  const body = await readBody(event);
  const { email, password, rememberMe = true, callbackURL } = body || {};
  const data = await auth.api.signInEmail({
    body: { email, password, rememberMe, callbackURL },
    headers: buildHeaders(event),
  });
  return data;
});
