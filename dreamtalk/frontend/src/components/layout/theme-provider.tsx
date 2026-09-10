"use client"

import { ThemeProvider as NextThemesProvider, useTheme as useNextTheme } from "next-themes"
import type { ReactNode } from "react"

/**
 * Real theme provider (next-themes). Toggles the `.dark` class on <html>,
 * which flips the token palette in globals.css. Dark-first (cinematic),
 * but fully switchable to the warm light theme.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="dark"
      enableSystem={false}
      storageKey="dreamtalk-theme"
      disableTransitionOnChange={false}
    >
      {children}
    </NextThemesProvider>
  )
}

/** Back-compat wrapper: `{ theme, resolvedTheme, setTheme, toggle }`. */
export function useTheme() {
  const { theme, resolvedTheme, setTheme } = useNextTheme()
  const current = (resolvedTheme || theme || "dark") as "light" | "dark"
  return {
    theme: current,
    resolvedTheme: current,
    setTheme,
    toggle: () => setTheme(current === "dark" ? "light" : "dark"),
  }
}
