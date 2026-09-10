"use client"

import { useState, useEffect } from "react"
import { motion } from "motion/react"

import { BackToHome } from "@/components/ui/BackToHome"
import { AuroraBackdrop } from "@/components/hero/AuroraBackground"
import { DigitalHumanScene } from "@/components/login/DigitalHumanScene"
import { SignupWizard } from "./SignupWizard"

const ROLE_COLORS: Record<string, string> = {
  personal: "#CC3A63",
  healthcare: "#A2AB73",
  business: "#A2AB73",
}

export function SignupExperience() {
  const [mounted, setMounted] = useState(false)


  useEffect(() => { setMounted(true) }, [])

  if (!mounted) {
    return (
      <main className="min-h-dvh flex bg-background" suppressHydrationWarning>
        <div className="flex-1 flex items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#8A8178]/30 border-t-[#CC3A63]" />
        </div>
      </main>
    )
  }

  return (
    <main className="relative min-h-dvh bg-background overflow-hidden flex flex-col">
      <AuroraBackdrop />

      {/* Back to Home */}
      <BackToHome />

      {/* Mobile Digital Human */}
      <div className="lg:hidden relative z-10 pt-16 pb-4 flex items-center justify-center overflow-hidden">
        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.8 }} className="w-full max-w-[280px]">
          <DigitalHumanScene />
        </motion.div>
      </div>

      {/* Split layout */}
      <div className="relative z-10 flex w-full flex-1">
        {/* LEFT: Digital Human + Mission */}
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.8 }}
          className="hidden lg:flex lg:w-1/2 relative items-center justify-center"
        >
          <div className="flex flex-col items-center gap-6 w-full max-w-[520px]">
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ duration: 1, delay: 0.2 }} className="w-full max-w-[480px]">
              <DigitalHumanScene />
            </motion.div>

            {/* Mission statement */}
            <motion.div
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
              className="text-center space-y-2 px-8"
            >
              <h2 className="text-lg font-bold text-foreground">Create Your Digital Twin</h2>
              <p className="text-xs text-foreground-muted leading-relaxed max-w-sm mx-auto">
                An intelligent Digital Human that learns, evolves, and works alongside you — across personal, healthcare, and enterprise environments.
              </p>
              <div className="flex items-center justify-center gap-4 pt-2">
                {[
                  { label: "Learn", color: "#CC3A63" },
                  { label: "Evolve", color: "#A2AB73" },
                  { label: "Remember", color: "#A2AB73" },
                ].map((f) => (
                  <span key={f.label} className="text-[10px] font-mono tracking-wider" style={{ color: `${f.color}99` }}>{f.label}</span>
                ))}
              </div>
            </motion.div>
          </div>
        </motion.div>

        {/* RIGHT: Signup Wizard */}
        <motion.div
          initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.6, delay: 0.15 }}
          className="w-full lg:w-1/2 flex items-center justify-center px-4 sm:px-6 lg:px-10 py-8"
        >
          <div className="w-full max-w-lg">
            {/* Header */}
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="text-center mb-6">
              <span className="text-xs uppercase tracking-[0.3em] text-white/20 font-mono">DreamTalk</span>
              <h1 className="text-2xl font-bold mt-2" style={{
                backgroundImage: "linear-gradient(135deg, #F3F4F4, #CC3A63, #A2AB73)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}>
                Begin Your Journey
              </h1>
              <p className="text-xs text-foreground-muted mt-1">Initialize your Digital Twin Operating System</p>
            </motion.div>

            {/* Glass panel */}
            <motion.div
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
              className="relative rounded-[24px] p-6 sm:p-8"
              style={{
                background: "rgba(15,23,42,0.75)",
                backdropFilter: "blur(32px)",
                WebkitBackdropFilter: "blur(32px)",
                border: "1px solid rgba(255,255,255,0.06)",
              }}
            >
              <SignupWizard />
            </motion.div>

            {/* Footer */}
            <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }} className="text-center text-[10px] text-foreground-muted mt-6">
              By signing up, you agree to DreamTalk&apos;s <a href="#" className="text-[#CC3A63] hover:text-[#A2AB73] transition-colors">Terms</a> and <a href="#" className="text-[#CC3A63] hover:text-[#A2AB73] transition-colors">Privacy Policy</a>
            </motion.p>
          </div>
        </motion.div>
      </div>
    </main>
  )
}
