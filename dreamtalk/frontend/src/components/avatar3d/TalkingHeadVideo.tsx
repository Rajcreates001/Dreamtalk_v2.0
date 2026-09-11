"use client"

import { useEffect, useRef, useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import { assetUrl } from "@/services/avatar/client"
import { useMediaLipsyncClock } from "@/services/avatar/lipsync"
import type { AvatarProfile, RespondResult } from "@/services/avatar/types"

export interface TalkingHeadVideoProps {
  profile?: AvatarProfile | null
  /** the current utterance to speak; null = idle (poster) */
  speech?: RespondResult | null
  className?: string
  glow?: string
  onEnded?: () => void
}

/**
 * 2D digital human. Plays the backend's rendered talking-head video when
 * present (real MuseTalk lip-sync of the user's face); otherwise shows the
 * profile photo and plays the cloned-voice audio with a live speaking meter.
 * All timing is driven off the media clock — never setTimeout.
 */
export function TalkingHeadVideo({ profile, speech, className = "", glow = "#CC3A63", onEnded }: TalkingHeadVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const audioRef = useRef<HTMLAudioElement>(null)
  const [openLevel, setOpenLevel] = useState(0)

  const poster = assetUrl(profile?.appearance?.primary_image_url)
  const videoUrl = assetUrl(speech?.video?.video_url)
  const audioUrl = assetUrl(speech?.audio_url ?? speech?.audio?.audio_url)
  const speaking = !!(videoUrl || audioUrl)

  // Drive a mouth-open meter from whichever media is playing.
  const mediaRef = (videoUrl ? videoRef : audioRef) as React.RefObject<HTMLMediaElement | null>
  useMediaLipsyncClock(mediaRef, speech?.lipsync, (shape, _t, playing) => {
    setOpenLevel(playing ? Math.min(1, shape.mouth_open + shape.jaw_drop * 0.4) : 0)
  })

  // Autoplay the new utterance.
  useEffect(() => {
    if (videoUrl && videoRef.current) videoRef.current.play().catch(() => {})
    else if (audioUrl && audioRef.current) audioRef.current.play().catch(() => {})
  }, [videoUrl, audioUrl])

  return (
    <div className={className} style={{ position: "relative" }}>
      <div className="pointer-events-none absolute inset-0 -z-10"
        style={{ background: `radial-gradient(52% 52% at 50% 46%, ${glow}22, transparent 72%)` }} />

      <div className="relative h-full w-full overflow-hidden rounded-3xl">
        {/* Idle / poster */}
        {poster && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={poster} alt={profile?.name ?? "Digital human"}
            className="absolute inset-0 h-full w-full object-cover" />
        )}
        {!poster && (
          <div className="absolute inset-0 grid place-items-center bg-surface/50 text-foreground-muted text-sm">
            No avatar yet
          </div>
        )}

        {/* Rendered talking-head video (crossfades over the poster) */}
        <AnimatePresence>
          {videoUrl && (
            <motion.video
              key={videoUrl}
              ref={videoRef}
              src={videoUrl}
              playsInline
              onEnded={onEnded}
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.35 }}
              className="absolute inset-0 h-full w-full object-cover"
            />
          )}
        </AnimatePresence>

        {/* Audio-only playback (no rendered video) */}
        {audioUrl && !videoUrl && <audio ref={audioRef} src={audioUrl} onEnded={onEnded} hidden />}

        {/* Live speaking meter (for the audio-only case) */}
        {speaking && !videoUrl && (
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-end gap-[3px] h-8">
            {Array.from({ length: 11 }).map((_, i) => {
              const center = 1 - Math.abs(i - 5) / 6
              const h = 4 + openLevel * 28 * (0.4 + center)
              return <span key={i} className="w-[3px] rounded-full" style={{ height: h, background: glow, opacity: 0.85 }} />
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default TalkingHeadVideo
