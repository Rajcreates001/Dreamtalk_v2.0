"use client"

import { cn } from "@/lib/utils"

export interface AuroraFieldProps {
  /** Higher = more visible. 1 is a whisper behind content; 3 is a hero. */
  intensity?: 1 | 2 | 3
  className?: string
}

/**
 * The ambient colour field that sits behind glass.
 *
 * Glass has nothing to refract over a flat background — this is what gives the
 * panes something to pick up. Built from three drifting radial gradients in
 * the brand palette plus grain.
 *
 * Pure CSS on purpose: the hero already spends a WebGL context on the 3D head,
 * and a second canvas for background colour would be a poor trade on the 8 GB
 * laptop GPUs we target. `position: fixed` keeps it off the scroll path.
 */
export function AuroraField({ intensity = 2, className }: AuroraFieldProps) {
  const alpha = { 1: 0.16, 2: 0.26, 3: 0.4 }[intensity]

  return (
    <div
      aria-hidden
      className={cn(
        "pointer-events-none fixed inset-0 -z-10 overflow-hidden grain",
        className,
      )}
    >
      <div
        className="absolute -left-1/4 -top-1/3 size-[70vw] rounded-full blur-3xl animate-drift-slow motion-reduce:animate-none"
        style={{
          background: `radial-gradient(circle, rgba(204,58,99,${alpha}) 0%, transparent 68%)`,
        }}
      />
      <div
        className="absolute -right-1/4 top-1/4 size-[60vw] rounded-full blur-3xl animate-float-slow motion-reduce:animate-none"
        style={{
          background: `radial-gradient(circle, rgba(97,45,83,${alpha}) 0%, transparent 68%)`,
        }}
      />
      <div
        className="absolute -bottom-1/3 left-1/4 size-[55vw] rounded-full blur-3xl animate-glow-soft motion-reduce:animate-none"
        style={{
          background: `radial-gradient(circle, rgba(162,171,115,${alpha * 0.8}) 0%, transparent 68%)`,
        }}
      />
    </div>
  )
}

export default AuroraField
