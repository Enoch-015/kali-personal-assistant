import { auth } from "../../../lib/auth";

export default defineEventHandler(async (event) => {
  const response = await auth.handler(toWebRequest(event));
  return response;
});
