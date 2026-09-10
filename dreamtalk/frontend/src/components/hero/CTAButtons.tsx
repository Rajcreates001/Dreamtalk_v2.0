"use client"

import { useRef, useState, useCallback } from "react"
import { motion, AnimatePresence } from "motion/react"
import { ArrowRight, Play } from "lucide-react"
import Link from "next/link"

export function PrimaryButton() {
  const [hovered, setHovered] = useState(false)
  const [ripples, setRipples] = useState<{ x: number; y: number; id: number }[]>([])
  const btnRef = useRef<HTMLAnchorElement>(null)
  const rippleCounter = useRef(0)

  const handleClick = useCallback((e: React.MouseEvent) => {
    const rect = btnRef.current?.getBoundingClientRect()
    if (!rect) return
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const id = rippleCounter.current++
    setRipples(prev => [...prev, { x, y, id }])
    setTimeout(() => {
      setRipples(prev => prev.filter(r => r.id !== id))
    }, 800)
  }, [])

  return (
    <Link
      ref={btnRef}
      href="/signup"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={handleClick}
      className="group relative inline-flex items-center gap-2.5 px-9 py-4 overflow-hidden rounded-2xl cursor-pointer"
    >
      {/* Animated gradient background */}
      <motion.div
        className="absolute inset-0"
        style={{
          backgroundSize: "300% 300%",
        }}
        animate={{
          background: hovered
            ? "linear-gradient(135deg, #CC3A63, #A2AB73, #A2AB73, #CC3A63)"
            : "linear-gradient(135deg, #CC3A63, #A2AB73)",
        }}
        transition={{ duration: 0.4 }}
      />

      {/* Hover highlight */}
      <motion.div
        className="absolute inset-0 opacity-0"
        animate={{ opacity: hovered ? 1 : 0 }}
        transition={{ duration: 0.5 }}
        style={{
          background: "radial-gradient(circle at 50% 50%, rgba(255,255,255,0.12), transparent 70%)",
        }}
      />

      {/* Ripple effects */}
      <AnimatePresence>
        {ripples.map((ripple) => (
          <motion.span
            key={ripple.id}
            initial={{ scale: 0, opacity: 0.5 }}
            animate={{ scale: 6, opacity: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="absolute pointer-events-none rounded-full"
            style={{
              left: ripple.x - 25,
              top: ripple.y - 25,
              width: 50,
              height: 50,
              background: "radial-gradient(circle, rgba(255,255,255,0.4), transparent)",
            }}
          />
        ))}
      </AnimatePresence>

      {/* Text */}
      <span className="relative z-10 text-white font-semibold text-sm tracking-wide">
        Get Started Free
      </span>

      {/* Arrow */}
      <motion.div
        className="relative z-10"
        animate={{ x: hovered ? 5 : 0, rotate: hovered ? -5 : 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
      >
        <ArrowRight className="h-4 w-4 text-white" />
      </motion.div>

      {/* Glow shadow */}
      <motion.div
        className="absolute inset-0 rounded-2xl"
        animate={{
          boxShadow: hovered
            ? "0 0 40px rgba(204,58,99,0.3), 0 0 80px rgba(162,171,115,0.15), inset 0 0 20px rgba(255,255,255,0.05)"
            : "0 4px 20px rgba(204,58,99,0.2)",
        }}
        transition={{ duration: 0.3 }}
      />
    </Link>
  )
}

export function SecondaryButton() {
  const [hovered, setHovered] = useState(false)

  return (
    <motion.button
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="group relative inline-flex items-center gap-2.5 px-9 py-4 rounded-2xl overflow-hidden cursor-pointer"
      animate={{
        background: hovered
          ? "rgba(255,255,255,0.06)"
          : "rgba(255,255,255,0.03)",
        borderColor: hovered
          ? "rgba(255,255,255,0.15)"
          : "rgba(255,255,255,0.08)",
      }}
      transition={{ duration: 0.3 }}
      style={{ border: "1px solid" }}
    >
      {/* Glass blur background */}
      <motion.div
        className="absolute inset-0 opacity-0"
        animate={{ opacity: hovered ? 1 : 0 }}
        transition={{ duration: 0.3 }}
        style={{
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          background: "radial-gradient(circle at 50% 50%, rgba(204,58,99,0.08), transparent)",
        }}
      />

      <Play className="relative z-10 h-4 w-4 text-[#D8D2C8] group-hover:text-white transition-colors" />
      <span className="relative z-10 text-[#D8D2C8] group-hover:text-white font-medium text-sm tracking-wide transition-colors">
        Watch Demo
      </span>

      {/* Arrow on hover */}
      <motion.div
        className="relative z-10"
        animate={{ x: hovered ? 3 : 0, opacity: hovered ? 1 : 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
      >
        <ArrowRight className="h-3.5 w-3.5 text-white/60" />
      </motion.div>
    </motion.button>
  )
}
