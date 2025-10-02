export type ToastType = "info" | "error" | "success";
let counter = 0;

export default defineNuxtPlugin(() => {
  function push(message: string, type: ToastType = "info", timeout = 4500) {
    const toasts = useState<{ id: number; message: string; type: ToastType }[]>("toasts", () => []);
    const id = ++counter;
    toasts.value.push({ id, message, type });
    if (timeout > 0) {
      setTimeout(() => {
        toasts.value = toasts.value.filter(t => t.id !== id);
      }, timeout);
    }
  }
  return { provide: { toast: { push } } };
});
