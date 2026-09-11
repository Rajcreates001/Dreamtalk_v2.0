"use client"

import { motion } from "motion/react"
import { ArrowLeft, Sparkles } from "lucide-react"
import Link from "next/link"

/**
 * BackToHome — a themed back-navigation pill fixed to the top-left corner.
 * Uses theme tokens so it reads correctly in both light and dark mode. The
 * anchor itself carries the layout/click target so navigation is reliable.
 */
export function BackToHome() {
  return (
    <Link
      href="/"
      aria-label="Back to home"
      className="group fixed top-4 left-4 z-50 inline-flex items-center gap-2 rounded-xl border border-border bg-card/80 px-2.5 py-1.5 sm:px-3 sm:py-2 backdrop-blur-xl shadow-sm transition-all duration-300 hover:scale-[1.02] hover:border-primary/30 hover:bg-card"
    >
      <motion.span
        initial={{ opacity: 0, x: -12 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="inline-flex items-center gap-2"
      >
        <ArrowLeft className="h-3.5 w-3.5 text-foreground-muted transition-colors group-hover:text-foreground" />
        <span className="hidden sm:flex items-center gap-1.5">
          <span className="grid h-4 w-4 place-items-center rounded-[4px] bg-gradient-to-br from-[#CC3A63] to-[#A2AB73]">
            <Sparkles className="h-2 w-2 text-white" />
          </span>
          <span className="text-[11px] font-medium text-foreground-muted transition-colors group-hover:text-foreground">DreamTalk</span>
        </span>
      </motion.span>
    </Link>
  )
}
