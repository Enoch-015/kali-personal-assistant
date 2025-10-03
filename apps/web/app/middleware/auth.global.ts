// In your middleware
export default defineNuxtRouteMiddleware(async (to) => {
  const publicRoutes = new Set([
    "/login",
    "/sign",
    "/auth-error",
    "/forgot-password",
    "/reset-password",
  ]);

  const { user, refreshSession } = useAuth();

  if (!user.value) {
    await refreshSession().catch(() => {});
  }

  const isAuthed = !!user.value;
  if (isAuthed && publicRoutes.has(to.path)) {
    return navigateTo("/");
  }
  if (!isAuthed && !publicRoutes.has(to.path)) {
    const redirect = to.fullPath;
    return navigateTo({ path: "/login", query: { redirect } });
  }
});
