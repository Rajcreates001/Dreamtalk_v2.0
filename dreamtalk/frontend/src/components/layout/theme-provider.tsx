"use client"

import { createContext, useContext, type ReactNode } from "react"

type Theme = "light" | "dark"

interface ThemeContextValue {
  theme: Theme
  toggle: () => void
  setTheme: (t: Theme) => void
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: "dark",
  toggle: () => {},
  setTheme: () => {},
})

export function useTheme() {
  return useContext(ThemeContext)
}

/**
 * ThemeProvider — always provides "dark" theme.
 * All theme toggle buttons have been removed across the app.
 * We keep the context so existing useTheme() calls still compile.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  return (
    <ThemeContext.Provider value={{ theme: "dark", toggle: () => {}, setTheme: () => {} }}>
      {children}
    </ThemeContext.Provider>
  )
}
