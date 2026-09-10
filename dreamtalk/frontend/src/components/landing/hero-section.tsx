"use client"

import { useRef } from "react"
import { motion, useScroll, useTransform } from "motion/react"
import { ArrowRight, Sparkles } from "lucide-react"
import { ShimmerButton } from "@/components/magic/shimmer-button"
import { MorphingText } from "@/components/magic/morphing-text"
import { SceneCanvas, ParticleField, FloatingShapes } from "@/components/3d"
import Link from "next/link"

export function HeroSection() {
  const sectionRef = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: sectionRef, offset: ["start start", "end start"] })
  const heroScale = useTransform(scrollYProgress, [0, 1], [1, 0.92])
  const heroOpacity = useTransform(scrollYProgress, [0, 0.8], [1, 0])

  return (
    <section ref={sectionRef} className="relative min-h-dvh w-full overflow-hidden bg-background">
      {/* 3D Background Scene */}
      <SceneCanvas className="fixed inset-0 -z-10">
        <ParticleField count={2500} color="#10b981" speed={0.4} spread={18} size={0.025} />
        <FloatingShapes count={15} />
      </SceneCanvas>

      {/* Gradient overlays */}
      <motion.div style={{ opacity: heroOpacity }} className="absolute inset-0 z-[1]">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[1000px] rounded-full bg-emerald-500/5 blur-[200px]" />
        <div className="absolute bottom-0 right-0 w-[700px] h-[700px] rounded-full bg-blue-500/5 blur-[160px]" />
        <div className="absolute top-1/3 left-1/4 w-[400px] h-[400px] rounded-full bg-purple-500/5 blur-[120px]" />
      </motion.div>

      <motion.div style={{ scale: heroScale }} className="relative z-[2] flex flex-col items-center justify-center min-h-dvh px-6 pt-24 pb-16">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-sm text-emerald-400 mb-8 backdrop-blur-sm"
        >
          <Sparkles className="h-3.5 w-3.5" />
          <span>Digital Humans — The Future of Interaction</span>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="text-center max-w-4xl mx-auto space-y-6"
        >
          <h1 className="text-5xl sm:text-6xl lg:text-7xl xl:text-8xl font-bold tracking-tight leading-[1.1]">
            <span className="text-foreground">Create </span>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-accent to-secondary">
              Digital Humans
            </span>
            <br />
            <span className="text-foreground/90">Bring Anyone to Life</span>
          </h1>

          <div className="h-14 flex items-center justify-center">
            <MorphingText
              texts={[
                "Digital humans for healthcare",
                "Digital humans for business",
                "Digital humans for education",
                "Digital humans for creativity",
                "Digital humans for companionship",
                "The future is here",
              ]}
              className="text-center text-lg sm:text-xl text-muted-foreground !h-auto !max-w-none !font-normal !text-[1.1rem] sm:!text-[1.25rem]"
            />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6 }}
          className="flex flex-wrap items-center justify-center gap-4 pt-8"
        >
          <Link href="/signup">
            <ShimmerButton
              shimmerColor="#10b981"
              background="rgba(16, 185, 129, 0.15)"
              className="text-foreground font-medium text-base px-8 py-3"
            >
              <span className="flex items-center gap-2">
                Get Started Free <ArrowRight className="h-4 w-4" />
              </span>
            </ShimmerButton>
          </Link>
          <Link href="/login">
            <button
              type="button"
              className="flex items-center gap-2 px-6 py-3 rounded-full border border-border text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-all text-sm font-medium backdrop-blur-sm"
            >
              Sign In
            </button>
          </Link>
        </motion.div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2, duration: 1 }}
        className="absolute bottom-6 left-1/2 -translate-x-1/2 z-[2]"
      >
        <motion.div
          animate={{ y: [0, 6, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          className="flex flex-col items-center gap-2 text-muted-foreground/40"
        >
          <span className="text-xs">Explore</span>
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
        </motion.div>
      </motion.div>
    </section>
  )
}
