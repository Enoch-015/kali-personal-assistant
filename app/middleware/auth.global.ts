// Temporary no-op middleware for frontend-only phase.
// Intentionally does nothing so all routes are accessible without auth.
export default defineNuxtRouteMiddleware(() => {
  // no-op
});
