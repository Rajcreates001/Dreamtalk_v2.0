"use client"

import { useRef } from "react"
import { useInView } from "motion/react"
import { AvatarStage, type AvatarStageProps } from "./AvatarStage"

/**
 * Mounts the (heavy) 3D avatar only once it scrolls near the viewport, so
 * off-screen avatars don't load the model or run a render loop at page start.
 */
export function InViewAvatar({ className = "", ...props }: AvatarStageProps) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { margin: "300px", once: true })
  return (
    <div ref={ref} className={className}>
      {inView ? <AvatarStage {...props} className="h-full w-full" /> : null}
    </div>
  )
}

export default InViewAvatar
