/**
 * Add Permissions-Policy headers to enable display-capture for screen sharing
 */
export default defineEventHandler((event) => {
  // Set Permissions-Policy to enable display-capture (screen sharing)
  setResponseHeader(event, "Permissions-Policy", "display-capture=(self)");

  // Also set the older Feature-Policy for broader compatibility
  setResponseHeader(event, "Feature-Policy", "display-capture 'self'");
});
