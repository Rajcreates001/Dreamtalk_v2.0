"use client"

import { forwardRef } from "react"
import { cn } from "@/lib/utils"

type Tone = "subtle" | "default" | "strong"

export interface GlassPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  /** How much the pane obscures what is behind it. */
  tone?: Tone
  /** The specular hairline along the leading edges. On by default — it is the
   *  detail that makes glass read as glass. */
  rim?: boolean
  /** Film grain, for large panels where soft gradients band on wide-gamut panels. */
  grain?: boolean
  as?: "div" | "section" | "aside" | "header" | "nav" | "article"
}

/**
 * A pane of glass.
 *
 * Use for chrome that floats ABOVE content — nav bars, modals, popovers,
 * toolbars, overlays. Do not use it for ordinary page cards: glass over a
 * plain background has nothing to refract, so it just looks like a grey box.
 * Those want `shadow-elev-*` instead.
 *
 * Contrast note: translucent surfaces cannot guarantee a contrast ratio on
 * their own, because the ratio depends on whatever scrolls behind them. Keep
 * body text on `tone="strong"`, or over a scrim.
 */
export const GlassPanel = forwardRef<HTMLDivElement, GlassPanelProps>(
  function GlassPanel(
    { tone = "default", rim = true, grain = false, as = "div", className, children, ...rest },
    ref,
  ) {
    const Tag = as

    return (
      <Tag
        ref={ref as never}
        className={cn(
          "rounded-2xl",
          tone === "strong" && "glass-strong",
          tone === "default" && "glass",
          tone === "subtle" && "glass-subtle",
          rim && "glass-rim",
          grain && "grain",
          className,
        )}
        {...rest}
      >
        {children}
      </Tag>
    )
  },
)

export default GlassPanel
