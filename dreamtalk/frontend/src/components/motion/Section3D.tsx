"use client"

import { useRef, type ReactNode } from "react"
import { motion, useScroll, useTransform, useReducedMotion, type MotionValue } from "motion/react"

export type Section3DVariant = "tilt" | "swing" | "rise" | "zoom"

/**
 * Wraps a section so it performs a 3D transition as it scrolls through the
 * viewport — tilting/swinging/rising/zooming in on enter and out on exit.
 * Respects reduced-motion (renders children flat).
 */
export function Section3D({
  children,
  variant = "tilt",
  className = "",
}: {
  children: ReactNode
  variant?: Section3DVariant
  className?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const reduce = useReducedMotion()
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] })

  // GPU-cheap transforms only (no animated blur — that tanks FPS).
  const opacity = useTransform(scrollYProgress, [0, 0.2, 0.8, 1], [0.35, 1, 1, 0.35])
  const rotateX = useTransform(scrollYProgress, [0, 0.3, 0.7, 1], [16, 0, 0, -12])
  const rotateY = useTransform(scrollYProgress, [0, 0.3, 0.7, 1], [-20, 0, 0, 16])
  const y = useTransform(scrollYProgress, [0, 0.32, 0.68, 1], [70, 0, 0, -55])
  const scale = useTransform(scrollYProgress, [0, 0.3, 0.7, 1], [0.9, 1, 1, 0.93])

  if (reduce) {
    return <div ref={ref} className={className}>{children}</div>
  }

  const style: {
    opacity: MotionValue<number>
    rotateX?: MotionValue<number>
    rotateY?: MotionValue<number>
    y?: MotionValue<number>
    scale?: MotionValue<number>
    transformPerspective: number
  } = { opacity, transformPerspective: 1400 }

  if (variant === "tilt") { style.rotateX = rotateX; style.y = y }
  else if (variant === "swing") { style.rotateY = rotateY }
  else if (variant === "rise") { style.y = y; style.scale = scale }
  else if (variant === "zoom") { style.scale = scale }

  return (
    <div ref={ref} className={className} style={{ perspective: 1400 }}>
      <motion.div style={{ ...style, transformStyle: "preserve-3d", willChange: "transform, opacity" }}>
        {children}
      </motion.div>
    </div>
  )
}

export default Section3D
