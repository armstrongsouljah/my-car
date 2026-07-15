export const THEME_KEY = "my-car-theme";
const VALID_THEMES = ["light", "dark", "system"];

export function getStoredTheme() {
  if (typeof window === "undefined") return "system";
  const stored = localStorage.getItem(THEME_KEY);
  return VALID_THEMES.includes(stored) ? stored : "system";
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
