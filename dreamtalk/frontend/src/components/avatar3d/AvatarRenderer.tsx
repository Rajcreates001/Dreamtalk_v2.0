"use client"

import dynamic from "next/dynamic"
import { TalkingHeadVideo } from "./TalkingHeadVideo"
import type { AvatarProfile, RespondResult } from "@/services/avatar/types"

const AvatarStage = dynamic(() => import("./AvatarStage").then((m) => m.AvatarStage), {
  ssr: false,
  loading: () => (
    <div className="grid h-full w-full place-items-center">
      <div className="h-16 w-16 rounded-full bg-gradient-to-br from-primary to-secondary opacity-70 blur-lg animate-pulse-glow" />
    </div>
  ),
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
 * (real lip-sync of the user's face); `3d` shows the interactive rig (viseme
 * driving lands in Phase 2). Consumers switch modes without touching either
 * implementation.
 */
export function AvatarRenderer({
  mode = "2d", profile, speech, className = "", glow = "#CC3A63", interactive = true, onEnded,
}: AvatarRendererProps) {
  if (mode === "3d") {
    return <AvatarStage className={className} colors={{ glow }} interactive={interactive} />
  }
  return (
    <TalkingHeadVideo profile={profile} speech={speech} className={className} glow={glow} onEnded={onEnded} />
  )
}

export default AvatarRenderer
