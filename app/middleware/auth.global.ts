export default defineNuxtRouteMiddleware(async (to) => {
  // Public routes list (extend as needed)
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
    // Encode redirect safely (avoid raw & in nested querystring)
    const redirect = to.fullPath;
    return navigateTo({ path: "/login", query: { redirect } });
  }
});
