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
    alt: "bg-foreground/[0.01] border-y border-foreground/[0.04]",
    dark: "bg-background",
    aurora: "bg-gradient-to-b from-transparent via-primary/[0.02] to-transparent",
    problem: "bg-gradient-to-b from-transparent via-destructive/[0.015] to-transparent",
    solution: "bg-gradient-to-b from-transparent via-primary/[0.025] via-secondary/[0.01] to-transparent",
    memory: "bg-gradient-to-b from-transparent via-primary/[0.02] to-transparent",
    knowledge: "bg-gradient-to-b from-transparent via-secondary/[0.015] to-transparent",
    voice: "bg-gradient-to-b from-transparent via-primary/[0.02] via-secondary/[0.01] to-transparent",
    deploy: "bg-gradient-to-b from-transparent via-primary/[0.015] to-transparent",
    cta: "bg-gradient-to-b from-transparent via-primary/[0.03] via-secondary/[0.015] to-transparent",
  }

  // Per-section accent colors for the blurred radial blobs
  const accentColors: Record<string, { primary: string; secondary: string }> = {
    default: { primary: "var(--primary)", secondary: "var(--secondary)" },
    alt: { primary: "var(--primary)", secondary: "var(--secondary)" },
    dark: { primary: "var(--primary)", secondary: "var(--secondary)" },
    aurora: { primary: "var(--primary)", secondary: "var(--secondary)" },
    problem: { primary: "var(--destructive)", secondary: "var(--primary)" },
    solution: { primary: "var(--primary)", secondary: "var(--secondary)" },
    memory: { primary: "var(--primary)", secondary: "var(--primary)" },
    knowledge: { primary: "var(--secondary)", secondary: "var(--primary)" },
    voice: { primary: "var(--primary)", secondary: "var(--secondary)" },
    deploy: { primary: "var(--primary)", secondary: "var(--secondary)" },
    cta: { primary: "var(--primary)", secondary: "var(--secondary)" },
    avatar: { primary: "var(--primary)", secondary: "var(--primary)" },
    humanization: { primary: "var(--primary)", secondary: "var(--primary)" },
    reasoning: { primary: "var(--warning)", secondary: "var(--primary)" },
    industry: { primary: "var(--secondary)", secondary: "var(--primary)" },
    security: { primary: "var(--secondary)", secondary: "var(--primary)" },
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
      style={{
        // Skip layout + paint for sections far off-screen (biggest single win on
        // this long page); the intrinsic size keeps the scrollbar stable.
        contentVisibility: "auto",
        containIntrinsicSize: "1px 800px",
        // No permanent will-change. It was applied to every section, which
        // promoted ~94 elements to their own compositor layers for the entire
        // page lifetime; transform/opacity reveals are GPU-composited without
        // it, and the hint is only a win when set immediately before a change
        // and cleared after.
      }}
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

      {/* Parallax background layer.
          These were `blur-[120px]` / `blur-[100px]` on solid colour at 2% and
          1.5% opacity — 2 per section across 19 sections, i.e. ~38 full blur
          passes for something imperceptible at that alpha. A radial-gradient
          produces the same soft falloff with no filter pass at all.
          `will-change` is also NOT set here: it was pinned permanently on every
          section, promoting ~94 elements to their own GPU layers for the whole
          page lifetime. Transform/opacity animations are composited anyway. */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        style={{ y: parallaxValues.y, opacity: parallaxValues.opacity }}
      >
        <div
          className="absolute top-1/4 left-1/4 w-[32rem] h-[32rem] rounded-full"
          style={{ background: `radial-gradient(circle, ${ac.primary} 0%, transparent 70%)`, opacity: 0.05 }}
        />
        <div
          className="absolute bottom-1/4 right-1/4 w-96 h-96 rounded-full"
          style={{ background: `radial-gradient(circle, ${ac.secondary} 0%, transparent 70%)`, opacity: 0.04 }}
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
              <span className="bg-gradient-to-r from-primary via-secondary to-secondary bg-clip-text text-transparent">
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
    >
      {label && (
        <motion.span
          initial={{ opacity: 0, y: 8 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.35, delay: 0.08 }}
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-xs font-medium text-primary mb-4"
        >
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-primary" />
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
      // NOT glass. There are ~20 of these on the landing page, and each
      // backdrop-filter is an uncacheable full blur pass while the page
      // scrolls — measured at 29 live glass layers and 11 FPS during scroll.
      // Glass is reserved for chrome (nav, modals, toolbars). These get the
      // specular rim and layered shadow, which is what actually reads as
      // depth, at roughly zero per-frame cost.
      className={`card-solid glass-rim rounded-[20px] p-6 shadow-elev-2 ${
        hover
          ? "hover:-translate-y-1 hover:border-primary/30 hover:shadow-elev-3 transition-all duration-300 ease-out group cursor-default"
          : ""
      } ${className}`}
    >
      {children}
    </motion.div>
  )
}
