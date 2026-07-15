export const THEME_KEY = "my-car-theme";

export function getStoredTheme() {
  if (typeof window === "undefined") return "system";
  return localStorage.getItem(THEME_KEY) || "system";
}

export function resolveTheme(theme) {
  if (theme === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return theme;
}

export function applyTheme(theme) {
  document.documentElement.classList.toggle("dark", resolveTheme(theme) === "dark");
}
