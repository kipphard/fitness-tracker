import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

type Theme = "light" | "dark";

interface ChartColors {
  grid: string;
  axis: string;
  weight: string;
  trend: string;
}

interface ThemeContextValue {
  theme: Theme;
  toggle: () => void;
  // Recharts needs explicit color values (it can't read CSS variables).
  chart: ChartColors;
}

const ThemeContext = createContext<ThemeContextValue>(null!);

export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}

function initialTheme(): Theme {
  const saved = localStorage.getItem("fit_theme");
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("fit_theme", theme);
  }, [theme]);

  const chart: ChartColors =
    theme === "dark"
      ? { grid: "#262a36", axis: "#99a0b1", weight: "#5b6472", trend: "#1bb583" }
      : { grid: "#ecedf3", axis: "#98a0b3", weight: "#aab0bd", trend: "#11936a" };

  return (
    <ThemeContext.Provider
      value={{ theme, toggle: () => setTheme((t) => (t === "light" ? "dark" : "light")), chart }}
    >
      {children}
    </ThemeContext.Provider>
  );
}
