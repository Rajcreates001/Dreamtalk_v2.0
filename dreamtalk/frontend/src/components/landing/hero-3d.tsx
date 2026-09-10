"use client"

import { useRef, useEffect, useState } from "react"
import { motion } from "motion/react"
import { ArrowRight, Sparkles, Box } from "lucide-react"
import { cn } from "@/lib/utils"
import Link from "next/link"

function FloatingOrbs({ mousePos }: { mousePos: { x: number; y: number } }) {
  return (
    <div className="relative flex items-center justify-center w-full h-[520px]">
      <div className="absolute w-[300px] h-[300px] rounded-full bg-gradient-to-r from-primary/20 via-accent/20 to-secondary/20 animate-pulse" />

      {[{ size: 16, color: "bg-primary/20", x: 20, y: -15, delay: 0 },
        { size: 12, color: "bg-accent/20", x: -15, y: 10, delay: 0.5 },
        { size: 10, color: "bg-secondary/20", x: 10, y: -8, delay: 1 },
        { size: 8, color: "bg-primary/15", x: -20, y: -5, delay: 0.3 },
        { size: 14, color: "bg-accent/15", x: 5, y: 20, delay: 0.7 },
        { size: 6, color: "bg-secondary/15", x: -10, y: -20, delay: 1.2 },
      ].map((orb, i) => (
        <motion.div
          key={i}
          animate={{
            y: [0, orb.y, 0],
            x: mousePos.x * (orb.x > 0 ? 20 : -20),
          }}
          transition={{
            y: { repeat: Infinity, duration: 3 + i * 0.5, ease: "easeInOut", delay: orb.delay },
            x: { type: "spring", stiffness: 40 },
          }}
          className={`absolute rounded-full ${orb.color} blur-sm`}
          style={{ width: orb.size * 4, height: orb.size * 4 }}
        />
      ))}
    </div>
  )
}

export function Hero3D() {
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleMove = (e: MouseEvent) => {
      setMousePos({
        x: (e.clientX / window.innerWidth - 0.5) * 2,
        y: (e.clientY / window.innerHeight - 0.5) * 2,
      })
    }
    window.addEventListener("mousemove", handleMove)
    return () => window.removeEventListener("mousemove", handleMove)
  }, [])

  return (
    <section ref={containerRef} className="relative w-full min-h-dvh flex items-center justify-center overflow-hidden">
      <div className="absolute top-0 left-1/4 w-[600px] h-[600px] rounded-full bg-primary/5 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] rounded-full bg-accent/5 blur-[100px] pointer-events-none" />

      <div className="relative z-20 grid lg:grid-cols-2 gap-12 items-center w-full max-w-7xl mx-auto px-6 lg:px-16 xl:px-24 py-20">
        <motion.div
          initial={{ opacity: 0, x: -60 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, ease: [0.25, 0.46, 0.45, 0.94] }}
          className="space-y-8"
        >
          <motion.div
            animate={{ x: mousePos.x * -8, y: mousePos.y * -5 }}
            transition={{ type: "spring", stiffness: 50, damping: 30 }}
          >
            <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-xs font-medium text-primary">
              <Sparkles className="h-3.5 w-3.5" />
              Next-Generation AI Platform
            </span>
          </motion.div>

          <motion.h1
            animate={{ x: mousePos.x * -12, y: mousePos.y * -8 }}
            transition={{ type: "spring", stiffness: 40, damping: 25 }}
            className="text-4xl sm:text-5xl lg:text-7xl font-bold tracking-tight leading-[1.1]"
          >
            Digital Humans
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-accent to-secondary">
              Powered by AI
            </span>
          </motion.h1>

          <motion.p
            animate={{ x: mousePos.x * -5, y: mousePos.y * -3 }}
            transition={{ type: "spring", stiffness: 60, damping: 30 }}
            className="text-lg text-muted-foreground max-w-xl leading-relaxed"
          >
            Create, customize, and interact with lifelike digital humans 
            for healthcare, business, and personal connection.
          </motion.p>

          <motion.div
            animate={{ x: mousePos.x * -3, y: mousePos.y * -2 }}
            transition={{ type: "spring", stiffness: 70, damping: 35 }}
            className="flex items-center gap-4"
          >
            <Link
              href="/signup"
              className="group relative px-8 py-3.5 rounded-2xl bg-primary text-primary-foreground font-semibold text-sm overflow-hidden transition-all hover:shadow-xl hover:shadow-primary/20 hover:scale-[1.02] active:scale-[0.98]"
            >
              <span className="relative z-10 flex items-center gap-2">
                Get Started Free
                <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </span>
              <div className="absolute inset-0 bg-gradient-to-r from-primary via-accent to-primary opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-xl" />
            </Link>
            <Link
              href="/login"
              className="px-8 py-3.5 rounded-2xl border border-border bg-background text-sm font-medium hover:bg-muted/30 transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              Sign In
            </Link>
          </motion.div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.2, ease: [0.25, 0.46, 0.45, 0.94] }}
          className="relative flex items-center justify-center"
        >
          <FloatingOrbs mousePos={mousePos} />
        </motion.div>
      </div>
    </section>
  )
}
