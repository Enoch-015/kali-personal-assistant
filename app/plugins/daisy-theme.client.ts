// Keep DaisyUI theme in sync with OS preference and Tailwind's `.dark` variant.
export default defineNuxtPlugin(() => {
  const media = window.matchMedia("(prefers-color-scheme: dark)");

  const apply = () => {
    const isDark = media.matches;
    const theme = isDark ? "business" : "light";

    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.classList.toggle("dark", isDark);
  };

  try {
    apply();
  }
  catch {}

  media.addEventListener("change", apply);
});
