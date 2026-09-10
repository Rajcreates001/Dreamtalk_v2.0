"use client"

import { useMemo } from "react"
import { sectionThemes, type SectionTheme } from "@/constants/design-tokens"

interface BackgroundEngineProps {
  theme?: keyof typeof sectionThemes | string
  style?: React.CSSProperties
  className?: string
}

/**
 * BackgroundEngine — Simplified CSS-only animated section backgrounds.
 *
 * Renders 2 layers of GPU-composited visual effects:
 *   1. Base gradient (deep space)
 *   2. Animated mesh gradient blobs (2x radial gradients with aurora-drift)
 *   3. Depth vignette overlay
 *
 * Zero JavaScript cost after initial render. All animation via CSS.
 */
export function BackgroundEngine({
  theme = "hero",
  className = "",
  style,
}: BackgroundEngineProps) {
  const config = useMemo(() => {
    return (sectionThemes as Record<string, SectionTheme>)[theme] || sectionThemes.hero
  }, [theme])

  return (
    <div
      className={`fixed inset-0 pointer-events-none z-0 overflow-hidden ${className}`}
      style={style}
      aria-hidden="true"
    >
      {/* Layer 1: Animated mesh gradient blobs (2x) */}
      <div
        className="absolute w-[700px] h-[700px] rounded-full animate-aurora-drift"
        style={{
          background: `radial-gradient(circle, ${config.background.blob1}, transparent 70%)`,
          left: "30%",
          top: "20%",
          transform: "translate(-50%, -50%)",
        }}
      />
      <div
        className="absolute w-[500px] h-[500px] rounded-full animate-aurora-drift"
        style={{
          background: `radial-gradient(circle, ${config.background.blob2}, transparent 70%)`,
          animationDelay: "5s",
          left: "60%",
          top: "60%",
          transform: "translate(-50%, -50%)",
        }}
      />

      {/* Layer 2: Depth vignette (fades to theme background) */}
      <div className="absolute inset-0"
        style={{ background: "radial-gradient(ellipse at center, transparent 0%, var(--background) 72%)" }} />
    </div>
  )
}

/**
 * SectionBackground — lightweight per-section background.
 * Renders the animated blobs WITHIN the section bounds (not fixed).
 */
export function SectionBackground({
  theme = "hero",
}: {
  theme?: keyof typeof sectionThemes | string
}) {
  const config = useMemo(() => {
    return (sectionThemes as Record<string, SectionTheme>)[theme] || sectionThemes.hero
  }, [theme])

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
      <div
        className="absolute w-[400px] h-[400px] rounded-full animate-aurora-drift"
        style={{
          background: `radial-gradient(circle, ${config.background.blob1}, transparent 70%)`,
          left: "30%",
          top: "40%",
          transform: "translate(-50%, -50%)",
          opacity: 0.6,
        }}
      />
      <div
        className="absolute w-[300px] h-[300px] rounded-full animate-aurora-drift"
        style={{
          background: `radial-gradient(circle, ${config.background.blob2}, transparent 70%)`,
          animationDelay: "5s",
          left: "70%",
          top: "60%",
          transform: "translate(-50%, -50%)",
          opacity: 0.4,
        }}
      />
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-background opacity-30" />
    </div>
  )
}
