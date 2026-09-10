"use client"

import dynamic from "next/dynamic"
import type { DigitalHuman3DProps } from "./DigitalHuman3D"

// Defer the Three.js bundle; render a themed placeholder while it loads.
const DigitalHuman3D = dynamic(
  () => import("./DigitalHuman3D").then((m) => m.DigitalHuman3D),
  {
    ssr: false,
    loading: () => (
      <div className="grid h-full w-full place-items-center">
        <div className="relative h-24 w-24">
          <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary to-secondary opacity-70 blur-xl animate-pulse-glow" />
          <div className="absolute inset-3 rounded-full bg-gradient-to-br from-primary to-secondary animate-breathe" />
        </div>
      </div>
    ),
  },
)

/** Convenience wrapper used across the app. */
export function AvatarStage(props: DigitalHuman3DProps) {
  return <DigitalHuman3D {...props} />
}

export default AvatarStage
