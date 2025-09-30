import { auth } from "../../../lib/auth";

function buildHeaders(event: any) {
  return new Headers(Object.entries(getRequestHeaders(event)) as [string, string][]);
}

export default defineEventHandler(async (event) => {
  const body = await readBody(event);
  const { newPassword, currentPassword, revokeOtherSessions } = body || {};
  return auth.api.changePassword({ body: { newPassword, currentPassword, revokeOtherSessions }, headers: buildHeaders(event) });
});
