"use client"

import { useCallback, useRef } from "react"
import { cn } from "@/lib/utils"
import { useFinePointer, useReducedMotion } from "@/hooks/useReducedMotion"

export interface SpotlightProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Radius of the lit area, in px. */
  size?: number
  /** Any CSS colour. Defaults to the brand pink at low alpha. */
  color?: string
  /** Also light up the border, which is what makes it read as a rim-lit edge. */
  border?: boolean
  children: React.ReactNode
}

/**
 * A cursor-tracked radial light over a surface.
 *
 * Same performance contract as TiltCard: positions go straight to CSS custom
 * properties inside a rAF, never through React state.
 *
 * The effect is decorative — it conveys no information, so it is skipped
 * entirely for touch and for reduced-motion users with no fallback needed.
 */
export function Spotlight({
  size = 320,
  color = "rgba(200, 90, 58, 0.14)",
  border = true,
  className,
  children,
  ...rest
}: SpotlightProps) {
  const ref = useRef<HTMLDivElement>(null)
  const frame = useRef<number | null>(null)
  const reduced = useReducedMotion()
  const fine = useFinePointer()
  const enabled = fine && !reduced

  const onPointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!enabled || frame.current !== null) return
      const el = ref.current
      if (!el) return
      const { clientX, clientY } = e
      frame.current = requestAnimationFrame(() => {
        frame.current = null
        const r = el.getBoundingClientRect()
        el.style.setProperty("--sx", `${clientX - r.left}px`)
        el.style.setProperty("--sy", `${clientY - r.top}px`)
      })
    },
    [enabled],
  )

  const clear = useCallback(() => {
    if (frame.current !== null) {
      cancelAnimationFrame(frame.current)
      frame.current = null
    }
  }, [])

  return (
    <div
      ref={ref}
      className={cn("group relative isolate overflow-hidden", className)}
      onPointerMove={onPointerMove}
      onPointerLeave={clear}
      onPointerCancel={clear}
      style={{ "--spot-size": `${size}px`, "--spot-color": color } as React.CSSProperties}
      {...rest}
    >
      {enabled && (
        <>
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 -z-10 opacity-0 transition-opacity duration-500 group-hover:opacity-100 [background:radial-gradient(var(--spot-size)_circle_at_var(--sx,50%)_var(--sy,50%),var(--spot-color),transparent_75%)]"
          />
          {border && (
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 rounded-[inherit] opacity-0 transition-opacity duration-500 group-hover:opacity-100 [background:radial-gradient(var(--spot-size)_circle_at_var(--sx,50%)_var(--sy,50%),var(--spot-color),transparent_70%)] [mask:linear-gradient(#000_0_0)_content-box,linear-gradient(#000_0_0)] [mask-composite:exclude] [padding:1px] [-webkit-mask:linear-gradient(#000_0_0)_content-box,linear-gradient(#000_0_0)] [-webkit-mask-composite:xor]"
            />
          )}
        </>
      )}
      {children}
    </div>
  )
}

export default Spotlight
