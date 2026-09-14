"use client"

import { useRef } from "react"
import { cn } from "@/lib/utils"
import { gsap, useGSAP } from "@/lib/gsap"

type Direction = "up" | "down" | "left" | "right" | "none"

export interface ScrollRevealProps extends React.HTMLAttributes<HTMLDivElement> {
  direction?: Direction
  /** Travel distance in px. Small is better — 24-48 reads as intent, 200 as a slide deck. */
  distance?: number
  /** Stagger direct children instead of animating the wrapper as one block. */
  stagger?: number
  delay?: number
  duration?: number
  /** Adds a blur-in. Costs a filter pass, so reserve it for hero-level content. */
  blur?: boolean
  /** Viewport position that fires it. GSAP syntax, e.g. "top 80%". */
  start?: string
  children: React.ReactNode
}

/**
 * Reveals content as it scrolls into view, via GSAP ScrollTrigger.
 *
 * Why ScrollTrigger rather than `whileInView` from motion: ScrollTrigger keeps
 * a single shared scroll listener and a cached layout for every trigger on the
 * page, where each motion element attaches its own IntersectionObserver. On a
 * landing page with 15 lazy sections that difference is measurable.
 *
 * Reduced motion lands the content at its final state instantly — never
 * stranded at opacity 0.
 */
export function ScrollReveal({
  direction = "up",
  distance = 32,
  stagger = 0,
  delay = 0,
  duration = 0.8,
  blur = false,
  start = "top 85%",
  className,
  children,
  ...rest
}: ScrollRevealProps) {
  const scope = useRef<HTMLDivElement>(null)

  useGSAP(
    () => {
      const root = scope.current
      if (!root) return
      const targets: Element[] | Element =
        stagger > 0 ? Array.from(root.children) : root
      if (Array.isArray(targets) && targets.length === 0) return

      const offset: Record<Direction, { x?: number; y?: number }> = {
        up: { y: distance },
        down: { y: -distance },
        left: { x: distance },
        right: { x: -distance },
        none: {},
      }

      const mm = gsap.matchMedia()

      mm.add("(prefers-reduced-motion: no-preference)", () => {
        gsap.fromTo(
          targets,
          {
            opacity: 0,
            ...offset[direction],
            ...(blur ? { filter: "blur(10px)" } : {}),
          },
          {
            opacity: 1,
            x: 0,
            y: 0,
            ...(blur ? { filter: "blur(0px)" } : {}),
            duration,
            delay,
            stagger,
            ease: "power3.out",
            // Clearing the props afterwards hands layout back to CSS, so a
            // later responsive reflow is not fighting an inline transform.
            clearProps: "filter",
            scrollTrigger: { trigger: root, start, once: true },
          },
        )
      })

      mm.add("(prefers-reduced-motion: reduce)", () => {
        gsap.set(targets, { opacity: 1, x: 0, y: 0, filter: "none" })
      })

      return () => mm.revert()
    },
    { scope, dependencies: [direction, distance, stagger, delay, duration, blur, start] },
  )

  return (
    <div ref={scope} className={cn(className)} {...rest}>
      {children}
    </div>
  )
}

export interface ParallaxProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Percent of its own height the layer travels. Keep to 5-15. */
  speed?: number
  children: React.ReactNode
}

/**
 * A layer that drifts against the scroll.
 *
 * Decorative and background layers only. Parallaxing body copy hurts reading
 * comfort and is a known motion-sickness trigger, so this is deliberately not
 * wired to text.
 */
export function Parallax({ speed = 10, className, children, ...rest }: ParallaxProps) {
  const ref = useRef<HTMLDivElement>(null)

  useGSAP(
    () => {
      const el = ref.current
      if (!el) return
      const mm = gsap.matchMedia()
      mm.add("(prefers-reduced-motion: no-preference)", () => {
        const tween = gsap.to(el, {
          yPercent: speed,
          ease: "none",
          scrollTrigger: {
            trigger: el.parentElement ?? el,
            scrub: true,
            // will-change is set only while the trigger is live; leaving it on
            // permanently pins GPU memory for every parallax layer on the page.
            onToggle: ({ isActive }) => {
              el.style.willChange = isActive ? "transform" : "auto"
            },
          },
        })
        return () => tween.kill()
      })
      return () => mm.revert()
    },
    { scope: ref, dependencies: [speed] },
  )

  return (
    <div ref={ref} aria-hidden className={cn(className)} {...rest}>
      {children}
    </div>
  )
}

export default ScrollReveal
