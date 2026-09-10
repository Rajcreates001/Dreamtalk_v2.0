"use client"

import { useRef, useEffect, useState } from "react"
import { motion, useScroll, useTransform } from "motion/react"
import { AuroraBackdrop } from "./AuroraBackground"
import { CinematicText } from "./CinematicText"
import { PrimaryButton, SecondaryButton } from "./CTAButtons"

/* ─── SIMPLIFIED RING CONFIGURATION (4 rings instead of 7) ─── */
const CHAMBER_RINGS = [
  { label: "Knowledge", color: "#7C5CFF", radius: 220, speed: 20, orbitDelay: 0 },
  { label: "Memory", color: "#00E5FF", radius: 170, speed: 24, orbitDelay: 0.5 },
  { label: "Voice", color: "#42FFC6", radius: 120, speed: 18, orbitDelay: 1.0 },
  { label: "Reasoning", color: "#8B5CF6", radius: 70, speed: 22, orbitDelay: 1.5 },
]

/* ─── DIGITAL CHAMBER — Simplified, CSS-only animated Digital Human environment ─── */
function DigitalChamber({ colors }: { colors: { primary: string; secondary: string; accent: string } }) {
  return (
    <div className="relative w-full max-w-[650px] aspect-square">
      {/* Outer glow layer */}
      <div
        className="absolute inset-[5%] rounded-full blur-[80px] animate-pulse-glow"
        style={{
          background: `radial-gradient(circle, ${colors.primary}15, transparent 70%)`,
        }}
      />

      {/* Orbiting Rings (4 rings, CSS-only) */}
      {CHAMBER_RINGS.map((ring) => (
        <div
          key={ring.label}
          className="absolute inset-0 flex items-center justify-center pointer-events-none"
          style={{
            animation: `orbit-ring ${ring.speed}s linear infinite`,
            animationDirection: ring.radius % 2 === 0 ? "normal" : "reverse",
            animationDelay: `${ring.orbitDelay}s`,
            zIndex: 10 - Math.floor(ring.radius / 30),
          }}
        >
          {/* Ring circle */}
          <div
            className="absolute rounded-full border"
            style={{
              width: ring.radius * 2,
              height: ring.radius * 2,
              borderColor: `${ring.color}10`,
              borderWidth: "1px",
            }}
          />
          {/* Orbiting node */}
          <div
            className="absolute w-1.5 h-1.5 rounded-full"
            style={{
              background: ring.color,
              left: `calc(50% + ${ring.radius - 1}px)`,
              top: "50%",
              marginTop: -3,
              boxShadow: `0 0 6px ${ring.color}50`,
            }}
          />
        </div>
      ))}

      {/* Digital Human avatar (CSS-only) */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="relative w-28 h-28">
          {/* Inner glow */}
          <div
            className="absolute inset-[10%] rounded-full blur-[25px]"
            style={{
              background: `radial-gradient(circle, ${colors.primary}20, transparent 70%)`,
              animation: "body-glow 4s ease-in-out infinite",
            }}
          />

          {/* Avatar body */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[60px] h-[60px]">
            {/* Head */}
            <div
              className="w-full h-full rounded-[40%_40%_45%_45%] p-[2px]"
              style={{
                background: `linear-gradient(to bottom, ${colors.primary}, ${colors.secondary})`,
                animation: "breathe 4s ease-in-out infinite",
              }}
            >
              <div className="w-full h-full rounded-[40%_40%_45%_45%] bg-[#070B14] flex items-center justify-center flex-col gap-1.5">
                {/* Eyes */}
                <div className="flex gap-4">
                  <div
                    className="w-[3px] h-[3px] rounded-full"
                    style={{
                      background: colors.secondary,
                      boxShadow: `0 0 4px ${colors.secondary}`,
                      animation: "blink 4s ease-in-out infinite",
                    }}
                  />
                  <div
                    className="w-[3px] h-[3px] rounded-full"
                    style={{
                      background: colors.secondary,
                      boxShadow: `0 0 4px ${colors.secondary}`,
                      animation: "blink 4s ease-in-out infinite 0.1s",
                    }}
                  />
                </div>
                {/* Mouth */}
                <div
                  className="w-3 h-[1.5px] rounded-full"
                  style={{
                    background: colors.primary,
                    opacity: 0.4,
                    animation: "breathe 4s ease-in-out infinite 0.5s",
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Chamber status indicator — single subtle label */}
      <div className="absolute bottom-[3%] left-1/2 -translate-x-1/2 z-20">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 2.5, duration: 0.5 }}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
          style={{
            background: "rgba(15,23,42,0.4)",
            border: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          <span className="relative flex h-1.5 w-1.5">
            <span
              className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
              style={{ backgroundColor: colors.accent }}
            />
            <span
              className="relative inline-flex rounded-full h-1.5 w-1.5"
              style={{ backgroundColor: colors.accent }}
            />
          </span>
          <span className="text-[10px] font-mono text-white/40 tracking-[0.15em] uppercase">
            Digital Human Chamber — Active
          </span>
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
  const [mounted, setMounted] = useState(false)
  const cyclePhaseRef = useRef(0)
  const [cyclePhase, setCyclePhase] = useState(0)

  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  })

  const heroScale = useTransform(scrollYProgress, [0, 1], [1, 0.88])
  const heroOpacity = useTransform(scrollYProgress, [0, 0.7], [1, 0])
  const contentY = useTransform(scrollYProgress, [0, 1], [0, -80])

  useEffect(() => {
    setMounted(true)
    const interval = setInterval(() => {
      cyclePhaseRef.current = (cyclePhaseRef.current + 1) % 12
      if (cyclePhaseRef.current % 2 === 0) {
        setCyclePhase(cyclePhaseRef.current)
      }
    }, 4000)
    return () => clearInterval(interval)
  }, [])

  const emotionColors = [
    { primary: "#7C5CFF", secondary: "#00E5FF", accent: "#42FFC6" },
    { primary: "#00E5FF", secondary: "#42FFC6", accent: "#7C5CFF" },
    { primary: "#FF6B9D", secondary: "#7C5CFF", accent: "#00E5FF" },
  ]
  const currentColors = emotionColors[cyclePhase % emotionColors.length]

  return (
    <section
      ref={heroRef}
      data-hero-section
      className="relative min-h-dvh flex items-center overflow-hidden bg-[#070B14]"
    >
      {/* CSS Aurora Backdrop */}
      <AuroraBackdrop />

      {/* Main Content */}
      <motion.div
        style={{ scale: heroScale, opacity: heroOpacity }}
        className="relative z-10 w-full"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 lg:py-28">
          <div className="grid lg:grid-cols-5 gap-8 lg:gap-12 items-center">
            {/* ─── LEFT: Content (2/5) ─── */}
            <motion.div style={{ y: contentY }} className="lg:col-span-2 space-y-6 lg:space-y-8">
              {/* Tagline */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.2 }}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full"
                style={{
                  background: "rgba(124,92,255,0.1)",
                  border: "1px solid rgba(124,92,255,0.2)",
                }}
              >
                <span className="relative flex h-1.5 w-1.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#7C5CFF] opacity-75" />
                  <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-[#7C5CFF]" />
                </span>
                <span className="text-[10px] font-mono tracking-[0.2em] text-[#7C5CFF] uppercase">
                  Introducing the Digital Twin OS
                </span>
              </motion.div>

              {/* Cinematic Headline */}
              <CinematicText
                lines={[
                  {
                    text: "The Operating System",
                    className: "text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-bold leading-[1.05] tracking-tight text-[#F8FAFC]",
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

              {/* Subheadline */}
              <motion.p
                initial={{ opacity: 0, y: 20, filter: "blur(4px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                transition={{ duration: 0.7, delay: 1.4, ease: [0.16, 1, 0.3, 1] }}
                className="text-base sm:text-lg text-[#94A3B8] max-w-xl leading-relaxed"
              >
                Create intelligent digital humans that speak, understand,
                learn, and evolve across personal, healthcare, and enterprise environments.
              </motion.p>

              {/* CTAs */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 1.7 }}
                className="flex flex-wrap gap-4"
              >
                <PrimaryButton />
                <SecondaryButton />
              </motion.div>

              {/* Live Metrics */}
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
                      <div className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-[#7C5CFF] to-[#00E5FF] bg-clip-text text-transparent">
                        {stat.value}
                      </div>
                      <div className="text-xs text-[#64748B] mt-1 tracking-wide">{stat.label}</div>
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </motion.div>

            {/* ─── RIGHT: Digital Chamber (3/5) ─── */}
            <motion.div
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

      {/* Bottom Gradient Fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#070B14] to-transparent z-10 pointer-events-none" />
    </section>
  )
}
