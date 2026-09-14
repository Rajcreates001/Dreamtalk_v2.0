"use client"

import { useRef } from "react"
import { cn } from "@/lib/utils"
import { gsap, useGSAP } from "@/lib/gsap"
import { useFinePointer, useReducedMotion } from "@/hooks/useReducedMotion"

export interface MagneticButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Pull strength, 0-1. Clamped so the element never leaves its own hit box. */
  strength?: number
  children: React.ReactNode
}

/**
 * A control that leans toward the cursor as it approaches.
 *
 * Use on one or two focal elements per screen at most — a page where
 * everything is magnetic just feels unstable.
 *
 * The inner span carries a counter-translation so the label trails the button
 * slightly; that lag is what sells it as weight rather than as a jump.
 */
export function MagneticButton({
  strength = 0.3,
  className,
  children,
  ...rest
}: MagneticButtonProps) {
  const ref = useRef<HTMLButtonElement>(null)
  const inner = useRef<HTMLSpanElement>(null)
  const reduced = useReducedMotion()
  const fine = useFinePointer()
  const enabled = fine && !reduced

  useGSAP(
    () => {
      const el = ref.current
      const label = inner.current
      if (!el || !label || !enabled) return

      // quickTo gives an interruptible tween per axis — far cheaper than a new
      // gsap.to() on every pointermove, and it eases rather than snapping.
      const xTo = gsap.quickTo(el, "x", { duration: 0.45, ease: "elastic.out(1, 0.4)" })
      const yTo = gsap.quickTo(el, "y", { duration: 0.45, ease: "elastic.out(1, 0.4)" })
      const lxTo = gsap.quickTo(label, "x", { duration: 0.6, ease: "power3.out" })
      const lyTo = gsap.quickTo(label, "y", { duration: 0.6, ease: "power3.out" })

      const clamped = Math.min(Math.max(strength, 0), 1)

      const onMove = (e: PointerEvent) => {
        const r = el.getBoundingClientRect()
        const dx = (e.clientX - r.left - r.width / 2) * clamped
        const dy = (e.clientY - r.top - r.height / 2) * clamped
        xTo(dx)
        yTo(dy)
        lxTo(dx * 0.35)
        lyTo(dy * 0.35)
      }
      const onLeave = () => {
        xTo(0)
        yTo(0)
        lxTo(0)
        lyTo(0)
      }

      el.addEventListener("pointermove", onMove)
      el.addEventListener("pointerleave", onLeave)
      // A pointer captured by a drag or lost to a tab switch never fires leave.
      el.addEventListener("pointercancel", onLeave)
      el.addEventListener("blur", onLeave)

      return () => {
        el.removeEventListener("pointermove", onMove)
        el.removeEventListener("pointerleave", onLeave)
        el.removeEventListener("pointercancel", onLeave)
        el.removeEventListener("blur", onLeave)
        gsap.set([el, label], { x: 0, y: 0 })
      }
    },
    { dependencies: [enabled, strength] },
  )

  return (
    <button
      ref={ref}
      className={cn(
        "relative inline-flex min-h-11 items-center justify-center",
        enabled && "will-change-transform",
        className,
      )}
      {...rest}
    >
      <span ref={inner} className="inline-flex items-center gap-2">
        {children}
      </span>
    </button>
  )
}

export default MagneticButton
