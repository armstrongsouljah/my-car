"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { THEME_KEY, applyTheme, getStoredTheme } from "@/lib/theme";

const ThemeContext = createContext({ theme: "system", setTheme: () => {} });

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState("system");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setThemeState(getStoredTheme());
    setLoaded(true);
  }, []);

  useEffect(() => {
    // Skip the pre-load pass — layout.jsx's inline script already applied the
    // correct class before paint, so re-applying "system" here first would
    // briefly override a stored light/dark choice that differs from the OS.
    if (!loaded) return;
    applyTheme(theme);
    if (theme !== "system") return;
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyTheme("system");
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [theme, loaded]);

  const setTheme = useCallback((next) => {
    localStorage.setItem(THEME_KEY, next);
    setThemeState(next);
  }, []);

  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>;
}

export const useTheme = () => useContext(ThemeContext);
