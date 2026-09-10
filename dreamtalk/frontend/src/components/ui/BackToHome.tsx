"use client"

import { motion } from "motion/react"
import { ArrowLeft } from "lucide-react"
import Link from "next/link"
import { Sparkles } from "lucide-react"

/**
 * BackToHome — a premium back-navigation pill that floats in the top-left corner.
 * Shows the DreamTalk logo + label on desktop, just an arrow on mobile.
 */
export function BackToHome() {
  return (
    <Link href="/">
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="group fixed top-4 left-4 z-50 flex items-center gap-2 px-2.5 py-1.5 sm:px-3 sm:py-2 rounded-xl transition-all duration-300 cursor-pointer hover:scale-[1.02]"
        style={{
          background: "rgba(15,23,42,0.7)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <ArrowLeft className="h-3.5 w-3.5 text-[#B0A79C] group-hover:text-[#F3F4F4] transition-colors" />
        <div className="hidden sm:flex items-center gap-1.5">
          <div className="w-4 h-4 rounded-[4px] bg-gradient-to-br from-[#CC3A63] to-[#A2AB73] flex items-center justify-center">
            <Sparkles className="h-2 w-2 text-white" />
          </div>
          <span className="text-[11px] font-medium text-[#B0A79C] group-hover:text-[#F3F4F4] transition-colors">DreamTalk</span>
        </div>
      </motion.div>
    </Link>
  )
}
