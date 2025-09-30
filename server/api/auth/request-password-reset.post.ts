import { auth } from "../../../lib/auth";

function buildHeaders(event: any) {
  return new Headers(Object.entries(getRequestHeaders(event)) as [string, string][]);
}

export default defineEventHandler(async (event) => {
  const body = await readBody(event);
  const { email, redirectTo } = body || {};
  return auth.api.requestPasswordReset({ body: { email, redirectTo }, headers: buildHeaders(event) });
});
