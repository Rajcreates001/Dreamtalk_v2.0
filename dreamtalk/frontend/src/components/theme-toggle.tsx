"use client"

import { useEffect, useState } from "react"
import { motion } from "motion/react"
import { Moon, Sun } from "lucide-react"
import { useTheme } from "@/components/layout/theme-provider"

/**
 * Animated light/dark toggle. Guards against hydration mismatch by only
 * rendering the themed icon after mount.
 */
export function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, toggle } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  const isDark = theme === "dark"

  return (
    <button
      onClick={toggle}
      aria-label={mounted ? `Switch to ${isDark ? "light" : "dark"} theme` : "Toggle theme"}
      className={`relative grid h-9 w-9 place-items-center rounded-xl border border-border bg-card/60 text-foreground-muted transition-colors hover:text-foreground hover:border-primary/40 ${className}`}
    >
      {mounted && (
        <motion.span
          key={isDark ? "moon" : "sun"}
          initial={{ rotate: -90, opacity: 0, scale: 0.6 }}
          animate={{ rotate: 0, opacity: 1, scale: 1 }}
          transition={{ type: "spring", stiffness: 260, damping: 20 }}
          className="grid place-items-center"
        >
          {isDark ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4 text-primary" />}
        </motion.span>
      )}
    </button>
  )
}
