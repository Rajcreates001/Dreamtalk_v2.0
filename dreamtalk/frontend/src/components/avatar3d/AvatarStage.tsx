"use client"

import dynamic from "next/dynamic"

// Defer the Three.js + GLB bundle; render a themed placeholder while it loads.
const GLBAvatar = dynamic(() => import("./GLBAvatar").then((m) => m.GLBAvatar), {
  ssr: false,
  loading: () => (
    <div className="grid h-full w-full place-items-center">
      <div className="relative h-24 w-24">
        <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary to-secondary opacity-70 blur-xl animate-pulse-glow" />
        <div className="absolute inset-3 rounded-full bg-gradient-to-br from-primary to-secondary animate-breathe" />
      </div>
    </div>
  ),
})

export interface AvatarStageProps {
  colors?: { primary?: string; secondary?: string; base?: string; glow?: string }
  speaking?: boolean
  autoSpeak?: boolean
  interactive?: boolean
  className?: string
  url?: string
  skinColor?: string
  autoRotate?: boolean
}

/** App-wide avatar wrapper. Maps the theme `colors` to the GLB avatar's glow. */
export function AvatarStage({ colors, ...rest }: AvatarStageProps) {
  const glow = colors?.glow || colors?.primary || "#CC3A63"
  return <GLBAvatar glow={glow} {...rest} />
}

export default AvatarStage
