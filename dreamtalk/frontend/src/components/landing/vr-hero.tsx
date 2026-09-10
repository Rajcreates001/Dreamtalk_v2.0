"use client"

import { useRef, useState, useEffect } from "react"
import { motion } from "motion/react"
import { ArrowRight, Sparkles } from "lucide-react"
import { VrmViewer } from "@/components/vrm/vrm-viewer"
import { Particles } from "@/components/magic/particles"
import { MorphingText } from "@/components/magic/morphing-text"
import { ShimmerButton } from "@/components/magic/shimmer-button"
import Link from "next/link"

export function VrmHero() {
  const [modelError, setModelError] = useState(false)
  const [modelLoaded, setModelLoaded] = useState(false)

  return (
    <section className="relative min-h-dvh w-full overflow-hidden bg-background">
      <Particles quantity={120} color="#8F9A5E" className="absolute inset-0 z-0" staticity={30} ease={80} />

      <div className="absolute inset-0 z-[1] bg-gradient-to-b from-transparent via-background/20 to-background" />

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1.5 }}
        className="absolute inset-0 z-[1]"
      >
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-emerald-500/10 blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] rounded-full bg-blue-500/8 blur-[100px]" />
      </motion.div>

      <div className="relative z-[2] flex flex-col lg:flex-row items-center justify-between min-h-dvh px-6 lg:px-16 xl:px-24 py-24 gap-8">
        <div className="flex-1 max-w-2xl space-y-8 pt-12 lg:pt-0">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-sm text-emerald-400"
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span>Powered by Advanced AI &amp; 3D Avatars</span>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
          >
            <h1 className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-bold tracking-tight">
              <span className="text-foreground">Your AI </span>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-accent to-secondary">
                Companion
              </span>
              <br />
              <span className="text-foreground/90">Brought to Life</span>
            </h1>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="h-12"
          >
            <MorphingText
              texts={[
                "Natural conversations",
                "Real-time emotions",
                "3D avatar presence",
                "Voice & vision aware",
                "Always available",
              ]}
              className="text-left text-lg sm:text-xl text-muted-foreground !h-auto !max-w-none !font-normal !text-[1.1rem] sm:!text-[1.25rem]"
            />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.8 }}
            className="flex flex-wrap items-center gap-4 pt-4"
          >
            <Link href="/conversations">
              <ShimmerButton
                shimmerColor="#8F9A5E"
                background="rgba(16, 185, 129, 0.15)"
                className="text-foreground font-medium"
              >
                <span className="flex items-center gap-2">
                  Start Talking <ArrowRight className="h-4 w-4" />
                </span>
              </ShimmerButton>
            </Link>
            <Link
              href="#features"
              className="px-6 py-3 rounded-full border border-border text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-all text-sm font-medium"
            >
              Explore Features
            </Link>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, delay: 0.5 }}
          className="flex-1 w-full max-w-lg lg:max-w-xl aspect-square relative"
        >
          <div className="absolute inset-0 rounded-full bg-gradient-to-br from-emerald-500/20 via-transparent to-blue-500/20 blur-3xl" />
          <div className="relative w-full h-full rounded-2xl overflow-hidden">
            {!modelLoaded && !modelError && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                  <div className="h-10 w-10 animate-spin rounded-full border-2 border-emerald-500/30 border-t-emerald-500" />
                  <span className="text-sm text-muted-foreground">Loading 3D avatar...</span>
                </div>
              </div>
            )}
            {modelError && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-64 h-64 rounded-full bg-gradient-to-br from-emerald-400/20 to-blue-400/20 flex items-center justify-center animate-pulse">
                  <span className="text-6xl font-bold text-emerald-500/30">AI</span>
                </div>
              </div>
            )}
            <VrmViewer
              modelUrl={process.env.NEXT_PUBLIC_VRM_MODEL_URL || null}
              onLoad={() => setModelLoaded(true)}
              onError={() => {
                setModelError(true)
                setModelLoaded(true)
              }}
              cameraDistance={4.5}
              className="w-full h-full"
            />
          </div>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5, duration: 1 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 z-[2]"
      >
        <motion.div
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          className="flex flex-col items-center gap-2 text-muted-foreground/50"
        >
          <span className="text-xs">Scroll</span>
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
        </motion.div>
      </motion.div>
    </section>
  )
}
