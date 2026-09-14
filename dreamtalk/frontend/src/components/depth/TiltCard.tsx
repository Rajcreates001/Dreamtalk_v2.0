"use client"

import { useCallback, useRef } from "react"
import { cn } from "@/lib/utils"
import { useFinePointer, useReducedMotion } from "@/hooks/useReducedMotion"

export interface TiltCardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Max rotation in degrees. Past ~12° the perspective distortion reads as a bug. */
  max?: number
  /** Scale on hover. Keep near 1 — a card that leaps is a card that flickers. */
  scale?: number
  /** Radial sheen that tracks the cursor, as if a light were above the card. */
  glare?: boolean
  /** Children marked `.layer-pop` float above the card face for real parallax. */
  children: React.ReactNode
}

/**
 * A card that tilts toward the cursor in 3D.
 *
 * Written against the DOM directly rather than through React state: this
 * updates on every pointermove, and a setState per move would re-render the
 * subtree ~120×/second. Writes go to CSS custom properties so the browser
 * composites them without a style recalc of the children.
 *
 * Disabled entirely for coarse pointers and for reduced-motion users — in both
 * cases the card renders flat and still, which is the correct final state.
 */
export function TiltCard({
  max = 9,
  scale = 1.015,
  glare = true,
  className,
  children,
  ...rest
}: TiltCardProps) {
  const ref = useRef<HTMLDivElement>(null)
  const frame = useRef<number | null>(null)
  const reduced = useReducedMotion()
  const fine = useFinePointer()
  const enabled = fine && !reduced

  const onPointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!enabled) return
      const el = ref.current
      if (!el) return
      // Coalesce to one write per frame; pointermove can outrun the compositor.
      if (frame.current !== null) return
      const { clientX, clientY } = e
      frame.current = requestAnimationFrame(() => {
        frame.current = null
        const r = el.getBoundingClientRect()
        // -0.5..0.5 from the card centre.
        const px = (clientX - r.left) / r.width - 0.5
        const py = (clientY - r.top) / r.height - 0.5
        // Y follows horizontal travel, X follows vertical, inverted: moving the
        // cursor up should tip the TOP of the card away from you.
        el.style.setProperty("--rx", `${(-py * max).toFixed(2)}deg`)
        el.style.setProperty("--ry", `${(px * max).toFixed(2)}deg`)
        el.style.setProperty("--mx", `${((px + 0.5) * 100).toFixed(1)}%`)
        el.style.setProperty("--my", `${((py + 0.5) * 100).toFixed(1)}%`)
      })
    },
    [enabled, max],
  )

  const reset = useCallback(() => {
    const el = ref.current
    if (!el) return
    if (frame.current !== null) {
      cancelAnimationFrame(frame.current)
      frame.current = null
    }
    el.style.setProperty("--rx", "0deg")
    el.style.setProperty("--ry", "0deg")
    el.style.setProperty("--mx", "50%")
    el.style.setProperty("--my", "50%")
  }, [])

  return (
    <div
      className={cn("group perspective-scene", className)}
      onPointerMove={onPointerMove}
      onPointerLeave={reset}
      // A pointer that vanishes mid-card (drag, scroll-away, tab switch) never
      // fires pointerleave, which would strand the card tilted.
      onPointerCancel={reset}
      onBlur={reset}
      {...rest}
    >
      <div
        ref={ref}
        className={cn(
          "relative h-full w-full preserve-3d",
          // 300ms only smooths the RETURN to rest; during a move the rAF writes
          // land faster than the transition, so tracking still feels direct.
          enabled &&
            "transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] group-hover:scale-[var(--tilt-scale)]",
        )}
        style={
          {
            "--tilt-scale": scale,
            transform: enabled
              ? "rotateX(var(--rx, 0deg)) rotateY(var(--ry, 0deg))"
              : undefined,
          } as React.CSSProperties
        }
      >
        {children}
        {glare && enabled && (
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 rounded-[inherit] opacity-0 transition-opacity duration-300 [background:radial-gradient(35%_45%_at_var(--mx,50%)_var(--my,50%),rgba(255,255,255,0.28),transparent_70%)] group-hover:opacity-100"
          />
        )}
      </div>
    </div>
  )
}

export default TiltCard
