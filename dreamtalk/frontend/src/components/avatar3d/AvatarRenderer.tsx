"use client"

import dynamic from "next/dynamic"
import { TalkingHeadVideo } from "./TalkingHeadVideo"
import type { AvatarProfile, RespondResult } from "@/services/avatar/types"

const loader = (
  <div className="grid h-full w-full place-items-center">
    <div className="h-16 w-16 rounded-full bg-gradient-to-br from-primary to-secondary opacity-70 blur-lg animate-pulse-glow" />
  </div>
)

// Rigged VRM head with real viseme-driven lip-sync (Phase 2).
const VRMAvatar = dynamic(() => import("./VRMAvatar").then((m) => m.VRMAvatar), {
  ssr: false, loading: () => loader,
})

export type AvatarMode = "2d" | "3d"

export interface AvatarRendererProps {
  mode?: AvatarMode
  profile?: AvatarProfile | null
  speech?: RespondResult | null
  className?: string
  glow?: string
  interactive?: boolean
  onEnded?: () => void
}

/**
 * Single surface for the digital human. `2d` plays the backend's talking-head
 * (real lip-sync of the user's face); `3d` shows the rigged VRM head, whose
 * mouth visemes are driven off the same cloned-voice audio + lipsync track.
 * Consumers switch modes without touching either implementation.
 */
export function AvatarRenderer({
  mode = "2d", profile, speech, className = "", glow = "#CC3A63", interactive = true, onEnded,
}: AvatarRendererProps) {
  if (mode === "3d") {
    return <VRMAvatar className={className} speech={speech} glow={glow} interactive={interactive} onEnded={onEnded} />
  }
  return (
    <TalkingHeadVideo profile={profile} speech={speech} className={className} glow={glow} onEnded={onEnded} />
  )
}

export default AvatarRenderer
