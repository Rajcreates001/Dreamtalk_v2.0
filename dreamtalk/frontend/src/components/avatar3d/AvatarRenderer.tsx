"use client"

import dynamic from "next/dynamic"
import { TalkingHeadVideo } from "./TalkingHeadVideo"
import type { AvatarProfile, RespondResult } from "@/services/avatar/types"

const loader = (
  <div className="grid h-full w-full place-items-center">
    <div className="h-16 w-16 rounded-full bg-gradient-to-br from-primary to-secondary opacity-70 blur-lg animate-pulse-glow" />
  </div>
)

// The user's own reconstructed FLAME head, animated via the morph targets the
// backend bakes into the GLB.
const TwinHead3D = dynamic(() => import("./TwinHead3D").then((m) => m.TwinHead3D), {
  ssr: false, loading: () => loader,
})

// Stand-in rigged VRM, used only when a profile has no 3D head yet.
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
 * (real lip-sync of the user's face); `3d` renders the user's own FLAME head
 * with its baked morph targets, falling back to a stand-in rig only when the
 * profile has no head yet. Both modes share one lipsync track + audio clock.
 */
export function AvatarRenderer({
  mode = "2d", profile, speech, className = "", glow = "#CC3A63", interactive = true, onEnded,
}: AvatarRendererProps) {
  if (mode === "3d") {
    // Only drive the real head when the backend actually baked blendshapes in;
    // otherwise it is a static bust and the stand-in rig reads better.
    const caps = profile?.appearance?.capabilities
    const hasAnimatableHead = !!profile?.appearance?.glb_url && !!caps?.arkit_blendshapes
    return hasAnimatableHead
      ? <TwinHead3D className={className} profile={profile} speech={speech} glow={glow} interactive={interactive} onEnded={onEnded} />
      : <VRMAvatar className={className} speech={speech} glow={glow} interactive={interactive} onEnded={onEnded} />
  }
  return (
    <TalkingHeadVideo profile={profile} speech={speech} className={className} glow={glow} onEnded={onEnded} />
  )
}

export default AvatarRenderer
