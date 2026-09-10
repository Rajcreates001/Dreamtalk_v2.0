"use client"

import { useRef } from "react"
import { motion, useScroll, useTransform } from "motion/react"
import { SectionBackground } from "@/components/background/BackgroundEngine"

interface SectionWrapperProps {
  children: React.ReactNode
  className?: string
  id?: string
  reveal?: "fade" | "slide" | "scale" | "rotate" | "blur" | "none"
  bg?: "default" | "alt" | "dark" | "aurora" | "problem" | "solution" | "memory" | "knowledge" | "voice" | "deploy" | "cta" | "avatar" | "humanization" | "reasoning" | "industry" | "security"
  label?: string
  /** Spacing variant: normal (default), compact, spacious */
  spacing?: "normal" | "compact" | "spacious"
}

// Pre-allocated easing for GPU-friendly compositing
const EASE = [0.25, 0.1, 0.25, 1] as const
const EASE_SMOOTH = [0.16, 1, 0.3, 1] as const

const revealVariants = {
  fade: { hidden: { opacity: 0 }, visible: { opacity: 1, transition: { duration: 0.7, ease: EASE } } },
  slide: { hidden: { opacity: 0, y: 50 }, visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: EASE } } },
  scale: { hidden: { opacity: 0, scale: 0.94 }, visible: { opacity: 1, scale: 1, transition: { duration: 0.8, ease: EASE } } },
  rotate: { hidden: { opacity: 0, rotateX: 6, y: 30 }, visible: { opacity: 1, rotateX: 0, y: 0, transition: { duration: 0.8, ease: EASE_SMOOTH } } },
  blur: { hidden: { opacity: 0, filter: "blur(6px)", y: 25 }, visible: { opacity: 1, filter: "blur(0px)", y: 0, transition: { duration: 0.8, ease: EASE_SMOOTH } } },
  none: { hidden: {}, visible: {} },
}

function useParallax(sectionRef: React.RefObject<HTMLDivElement | null>, enabled: boolean) {
  const { scrollYProgress } = useScroll({
    target: enabled ? sectionRef : undefined,
    offset: ["start end", "end start"],
  })
  const parallax = useTransform(scrollYProgress, [0, 1], [0, -20])
  const opacityScale = useTransform(scrollYProgress, [0, 0.2, 0.8, 1], [0.7, 1, 1, 0.7])
  return enabled ? { y: parallax, opacity: opacityScale } : { y: 0, opacity: 1 }
}

function SectionInner({
  children,
  className = "",
  id,
  reveal = "slide",
  bg = "default",
  label,
  spacing = "normal",
  parallaxValues,
}: SectionWrapperProps & { parallaxValues: { y: any; opacity: any } }) {
  const spacingClasses = {
    compact: "py-16 lg:py-20",
    normal: "py-24 lg:py-32",
    spacious: "py-32 lg:py-40",
  }

  // Per-section Aurora color identity
  const bgClasses: Record<string, string> = {
    default: "bg-transparent",
    alt: "bg-white/[0.01] border-y border-white/[0.04]",
    dark: "bg-[#050816]",
    aurora: "bg-gradient-to-b from-transparent via-[#CC3A63]/[0.02] to-transparent",
    problem: "bg-gradient-to-b from-transparent via-[#D84C63]/[0.015] to-transparent",
    solution: "bg-gradient-to-b from-transparent via-[#CC3A63]/[0.025] via-[#A2AB73]/[0.01] to-transparent",
    memory: "bg-gradient-to-b from-transparent via-[#CC3A63]/[0.02] to-transparent",
    knowledge: "bg-gradient-to-b from-transparent via-[#A2AB73]/[0.015] to-transparent",
    voice: "bg-gradient-to-b from-transparent via-[#CC3A63]/[0.02] via-[#A2AB73]/[0.01] to-transparent",
    deploy: "bg-gradient-to-b from-transparent via-[#CC3A63]/[0.015] to-transparent",
    cta: "bg-gradient-to-b from-transparent via-[#CC3A63]/[0.03] via-[#A2AB73]/[0.015] to-transparent",
  }

  // Per-section accent colors for the blurred radial blobs
  const accentColors: Record<string, { primary: string; secondary: string }> = {
    default: { primary: "#CC3A63", secondary: "#A2AB73" },
    alt: { primary: "#CC3A63", secondary: "#A2AB73" },
    dark: { primary: "#CC3A63", secondary: "#A2AB73" },
    aurora: { primary: "#CC3A63", secondary: "#A2AB73" },
    problem: { primary: "#D84C63", secondary: "#CC3A63" },
    solution: { primary: "#CC3A63", secondary: "#A2AB73" },
    memory: { primary: "#CC3A63", secondary: "#B03A5E" },
    knowledge: { primary: "#A2AB73", secondary: "#CC3A63" },
    voice: { primary: "#CC3A63", secondary: "#A2AB73" },
    deploy: { primary: "#CC3A63", secondary: "#A2AB73" },
    cta: { primary: "#CC3A63", secondary: "#A2AB73" },
    avatar: { primary: "#CC3A63", secondary: "#CC3A63" },
    humanization: { primary: "#CC3A63", secondary: "#CC3A63" },
    reasoning: { primary: "#D6A44C", secondary: "#CC3A63" },
    industry: { primary: "#8F9A5E", secondary: "#CC3A63" },
    security: { primary: "#A2AB73", secondary: "#CC3A63" },
  }

  const ac = accentColors[bg] || accentColors.default

  return (
    <motion.section
      id={id}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-40px" }}
      variants={revealVariants[reveal]}
      className={`relative z-10 ${spacingClasses[spacing]} px-4 sm:px-6 lg:px-8 overflow-hidden contain-layout ${bgClasses[bg]} ${className}`}
      style={reveal !== "none" ? { willChange: "transform, opacity" } : undefined}
    >
      {label && (
        <motion.div
          className="absolute top-8 left-1/2 -translate-x-1/2 z-20"
          initial={{ opacity: 0, y: -8 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2 }}
        >
          <span className="text-[10px] uppercase tracking-[0.25em] text-foreground/20 font-mono">{label}</span>
        </motion.div>
      )}

      {/* Background engine with per-section colors */}
      <SectionBackground theme={bg} />

      {/* Parallax background layer */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        style={{ y: parallaxValues.y, opacity: parallaxValues.opacity, willChange: "transform, opacity" }}
      >
        <div
          className="absolute top-1/4 left-1/4 w-80 h-80 rounded-full blur-[120px]"
          style={{ background: ac.primary, opacity: 0.02 }}
        />
        <div
          className="absolute bottom-1/4 right-1/4 w-64 h-64 rounded-full blur-[100px]"
          style={{ background: ac.secondary, opacity: 0.015 }}
        />
      </motion.div>

      <div className="relative z-10">{children}</div>
    </motion.section>
  )
}

export function SectionWrapper(props: SectionWrapperProps) {
  const sectionRef = useRef<HTMLDivElement>(null)
  // Only create scroll subscriptions for sections with labels (chapters)
  // This reduces motion value subscriptions from ~17 to ~5
  const parallaxValues = useParallax(sectionRef, !!props.label)

  return (
    <div ref={sectionRef}>
      <SectionInner {...props} parallaxValues={parallaxValues} />
    </div>
  )
}

/** Section heading — FIXED: inline-block no longer swallows spaces */
function RenderTitle({ title }: { title: string }) {
  // Check if any word needs gradient treatment
  const needsSplit = /Digital/i.test(title)
  
  if (!needsSplit) {
    return <>{title}</>
  }

  return (
    <>
      {title.split(" ").map((word, i) => {
        const isGradientWord = /Digital/i.test(word)
        return (
          <span key={i}>
            {i > 0 && <>{' '}</>}
            {isGradientWord ? (
              <span className="bg-gradient-to-r from-[#CC3A63] via-[#A2AB73] to-[#A2AB73] bg-clip-text text-transparent">
                {word}
              </span>
            ) : (
              <>{word}</>
            )}
          </span>
        )
      })}
    </>
  )
}

export function SectionHeading({
  label,
  title,
  description,
  align = "center",
}: {
  label?: string
  title: string
  description?: string
  align?: "center" | "left"
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.5, ease: EASE }}
      className={`mb-14 ${align === "center" ? "text-center" : "text-left"}`}
      style={{ willChange: "transform, opacity" }}
    >
      {label && (
        <motion.span
          initial={{ opacity: 0, y: 8 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.35, delay: 0.08 }}
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#CC3A63]/10 border border-[#CC3A63]/20 text-xs font-medium text-[#CC3A63] mb-4"
        >
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#CC3A63] opacity-75" />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-[#CC3A63]" />
          </span>
          {label}
        </motion.span>
      )}
      <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4 tracking-tight">
        <RenderTitle title={title} />
      </h2>
      {description && (
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="text-lg text-foreground-muted max-w-2xl mx-auto leading-relaxed"
        >
          {description}
        </motion.p>
      )}
    </motion.div>
  )
}

/** Stagger grid — reduced stagger delay for snappier feel */
export function StaggerGrid({
  children,
  className = "",
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <motion.div
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-40px" }}
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: 0.06, delayChildren: 0.1 } },
      }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

export const staggerItem = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: EASE },
  },
}

/** Premium glass card — CSS hover instead of JS for better perf */
export function GlassCard({
  children,
  className = "",
  hover = true,
}: {
  children: React.ReactNode
  className?: string
  hover?: boolean
}) {
  return (
    <motion.div
      variants={staggerItem}
      className={`rounded-[20px] bg-card/80 backdrop-blur-2xl border border-white/[0.06] p-6 ${
        hover
          ? "hover:-translate-y-1 hover:bg-white/[0.04] hover:border-[#CC3A63]/20 transition-all duration-300 ease-out group cursor-default"
          : ""
      } ${className}`}
    >
      {children}
    </motion.div>
  )
}
