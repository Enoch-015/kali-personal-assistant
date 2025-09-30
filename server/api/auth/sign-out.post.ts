import { auth } from "../../../lib/auth";

function buildHeaders(event: any) {
  return new Headers(Object.entries(getRequestHeaders(event)) as [string, string][]);
}

export default defineEventHandler(async (event) => {
  await auth.api.signOut({ headers: buildHeaders(event) });
  return { success: true };
});
