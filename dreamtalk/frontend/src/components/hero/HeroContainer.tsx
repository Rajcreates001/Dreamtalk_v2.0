"use client"

import { useRef, useEffect, useState } from "react"
import { motion, useScroll, useTransform } from "motion/react"
import { AuroraBackdrop } from "./AuroraBackground"
import { CinematicText } from "./CinematicText"
import { PrimaryButton, SecondaryButton } from "./CTAButtons"
import { AvatarStage } from "@/components/avatar3d/AvatarStage"
import { useTheme } from "@/components/layout/theme-provider"

/* ─── DIGITAL HUMAN — real 3D avatar centerpiece ─── */
function DigitalChamber({ colors }: { colors: { primary: string; secondary: string; accent: string } }) {
  const { theme } = useTheme()
  const base = theme === "dark" ? "#3a2f33" : "#e4d4bf"

  return (
    <div className="relative w-full max-w-[620px] aspect-square">
      {/* Ambient bloom behind the avatar */}
      <div
        className="absolute inset-[8%] rounded-full blur-[90px] animate-pulse-glow"
        style={{ background: `radial-gradient(circle, ${colors.primary}22, transparent 70%)` }}
      />

      {/* 3D avatar */}
      <AvatarStage
        className="absolute inset-0"
        colors={{ primary: colors.primary, secondary: colors.secondary, base, glow: colors.primary }}
        autoSpeak
        interactive
      />

      {/* Status label */}
      <div className="absolute bottom-[4%] left-1/2 -translate-x-1/2 z-20">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.6, duration: 0.5 }}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border bg-card/50 backdrop-blur-md"
        >
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style={{ backgroundColor: colors.accent }} />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5" style={{ backgroundColor: colors.accent }} />
          </span>
          <span className="label-mono !text-[10px]">Digital Human — Live</span>
        </motion.div>
      </div>
    </div>
  )
}

/* ─── LIVE METRICS ─── */
const METRICS = [
  { value: "50K+", label: "Avatars Created", delay: 2.2 },
  { value: "10M+", label: "Conversations", delay: 2.4 },
  { value: "50+", label: "Languages", delay: 2.6 },
  { value: "<200ms", label: "Response Time", delay: 2.8 },
]

/* ─── MAIN HERO CONTAINER ─── */
export function HeroContainer({ showStats = true }: { showStats?: boolean }) {
  const heroRef = useRef<HTMLDivElement>(null)
  const [, setMounted] = useState(false)
  const cyclePhaseRef = useRef(0)
  const [cyclePhase, setCyclePhase] = useState(0)

  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  })

  const heroScale = useTransform(scrollYProgress, [0, 1], [1, 0.88])
  const heroOpacity = useTransform(scrollYProgress, [0, 0.7], [1, 0])
  const contentY = useTransform(scrollYProgress, [0, 1], [0, -80])
  const avatarY = useTransform(scrollYProgress, [0, 1], [0, 120])
  const avatarRotate = useTransform(scrollYProgress, [0, 1], [0, 10])

  useEffect(() => {
    setMounted(true)
    const interval = setInterval(() => {
      cyclePhaseRef.current = (cyclePhaseRef.current + 1) % 12
      if (cyclePhaseRef.current % 2 === 0) setCyclePhase(cyclePhaseRef.current)
    }, 4000)
    return () => clearInterval(interval)
  }, [])

  const emotionColors = [
    { primary: "#CC3A63", secondary: "#A2AB73", accent: "#A2AB73" },
    { primary: "#A2AB73", secondary: "#CC3A63", accent: "#CC3A63" },
    { primary: "#CC3A63", secondary: "#853953", accent: "#A2AB73" },
  ]
  const currentColors = emotionColors[cyclePhase % emotionColors.length]

  return (
    <section
      ref={heroRef}
      data-hero-section
      className="relative min-h-dvh flex items-center overflow-hidden bg-background"
    >
      <AuroraBackdrop />

      <motion.div style={{ scale: heroScale, opacity: heroOpacity }} className="relative z-10 w-full">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 lg:py-28">
          <div className="grid lg:grid-cols-5 gap-8 lg:gap-12 items-center">
            {/* LEFT: Content */}
            <motion.div style={{ y: contentY }} className="lg:col-span-2 space-y-6 lg:space-y-8">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.2 }}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-primary/25 bg-primary/10"
              >
                <span className="relative flex h-1.5 w-1.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                  <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-primary" />
                </span>
                <span className="text-[10px] font-mono tracking-[0.2em] text-primary uppercase">
                  Introducing the Digital Twin OS
                </span>
              </motion.div>

              <CinematicText
                lines={[
                  {
                    text: "The Operating System",
                    className: "text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-bold leading-[1.05] tracking-tight text-foreground",
                    delay: 0.3,
                    revealType: "blur",
                  },
                  {
                    text: "for Digital Humans",
                    gradient: true,
                    className: "text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-bold leading-[1.05] tracking-tight",
                    delay: 0.8,
                    revealType: "scale",
                  },
                ]}
              />

              <motion.p
                initial={{ opacity: 0, y: 20, filter: "blur(4px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                transition={{ duration: 0.7, delay: 1.4, ease: [0.16, 1, 0.3, 1] }}
                className="text-base sm:text-lg text-foreground-muted max-w-xl leading-relaxed"
              >
                Create intelligent digital humans that speak, understand,
                learn, and evolve across personal, healthcare, and enterprise environments.
              </motion.p>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 1.7 }}
                className="flex flex-wrap gap-4"
              >
                <PrimaryButton />
                <SecondaryButton />
              </motion.div>

              {showStats && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.6, delay: 2.0 }}
                  className="grid grid-cols-2 sm:grid-cols-4 gap-4 sm:gap-6 pt-4"
                >
                  {METRICS.map((stat) => (
                    <motion.div
                      key={stat.label}
                      initial={{ opacity: 0, y: 15 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.5, delay: stat.delay }}
                    >
                      <div className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                        {stat.value}
                      </div>
                      <div className="text-xs text-foreground-muted mt-1 tracking-wide">{stat.label}</div>
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </motion.div>

            {/* RIGHT: 3D avatar */}
            <motion.div
              style={{ y: avatarY, rotateZ: avatarRotate }}
              initial={{ opacity: 0, scale: 0.85, filter: "blur(8px)" }}
              animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
              transition={{ duration: 1.2, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
              className="lg:col-span-3 relative flex items-center justify-center"
            >
              <DigitalChamber colors={currentColors} />
            </motion.div>
          </div>
        </div>
      </motion.div>

      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-background to-transparent z-10 pointer-events-none" />
    </section>
  )
}
