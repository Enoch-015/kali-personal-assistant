// Centralized toast helper so pages don't reach into nuxtApp.$toast directly
// Provides semantic helpers for common auth scenarios.

export type ToastType = "success" | "error" | "info";

export function useToast() {
  const nuxtApp = useNuxtApp();
  function push(message: string, type: ToastType = "info") {
    (nuxtApp as any).$toast?.push(message, type);
  }
  return {
    push,
    success: (m: string) => push(m, "success"),
    error: (m: string) => push(m, "error"),
    info: (m: string) => push(m, "info"),
  };
}
