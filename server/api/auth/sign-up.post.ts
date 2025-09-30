import { auth } from "../../../lib/auth";

function buildHeaders(event: any) {
  return new Headers(Object.entries(getRequestHeaders(event)) as [string, string][]);
}

export default defineEventHandler(async (event) => {
  const body = await readBody(event);
  const { name, email, password, image, callbackURL } = body || {};
  const data = await auth.api.signUpEmail({
    body: { name, email, password, image, callbackURL },
    headers: buildHeaders(event),
  });
  return data;
});
