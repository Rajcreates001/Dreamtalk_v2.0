"use client"

import { useEffect, useRef } from "react"
import type { VisemeKeyframe } from "./types"

export interface MouthShape {
  mouth_open: number
  mouth_width: number
  lip_round: number
  jaw_drop: number
}

const CLOSED: MouthShape = { mouth_open: 0, mouth_width: 0, lip_round: 0, jaw_drop: 0 }

const lerp = (a: number, b: number, t: number) => a + (b - a) * t

/**
 * Sample the mouth shape at time `t` (seconds) from an audio-aligned viseme
 * track, interpolating between the surrounding keyframes.
 */
export function sampleLipsync(keyframes: VisemeKeyframe[] | undefined, t: number): MouthShape {
  if (!keyframes || keyframes.length === 0) return CLOSED
  // Binary search for the last keyframe whose timestamp <= t.
  let lo = 0, hi = keyframes.length - 1, idx = 0
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    if (keyframes[mid].timestamp <= t) { idx = mid; lo = mid + 1 } else { hi = mid - 1 }
  }
  const cur = keyframes[idx]
  const next = keyframes[idx + 1]
  if (!next) return { mouth_open: cur.mouth_open, mouth_width: cur.mouth_width, lip_round: cur.lip_round, jaw_drop: cur.jaw_drop }
  const span = Math.max(0.0001, next.timestamp - cur.timestamp)
  const f = Math.min(1, Math.max(0, (t - cur.timestamp) / span))
  return {
    mouth_open: lerp(cur.mouth_open, next.mouth_open, f),
    mouth_width: lerp(cur.mouth_width, next.mouth_width, f),
    lip_round: lerp(cur.lip_round, next.lip_round, f),
    jaw_drop: lerp(cur.jaw_drop, next.jaw_drop, f),
  }
}

/**
 * Drive `onFrame(shape, currentTime)` off an <audio>/<video> element's clock
 * while it plays. This is the single source of truth for lip-sync timing —
 * never setTimeout. Stops the rAF loop when the media pauses/ends.
 */
export function useMediaLipsyncClock(
  mediaRef: React.RefObject<HTMLMediaElement | null>,
  keyframes: VisemeKeyframe[] | undefined,
  onFrame: (shape: MouthShape, currentTime: number, playing: boolean) => void,
) {
  const raf = useRef(0)
  const onFrameRef = useRef(onFrame)
  onFrameRef.current = onFrame

  useEffect(() => {
    const el = mediaRef.current
    if (!el) return
    let running = false

    const tick = () => {
      const media = mediaRef.current
      if (!media) return
      onFrameRef.current(sampleLipsync(keyframes, media.currentTime), media.currentTime, !media.paused)
      if (!media.paused && !media.ended) raf.current = requestAnimationFrame(tick)
      else running = false
    }
    const start = () => { if (!running) { running = true; raf.current = requestAnimationFrame(tick) } }
    const stop = () => { cancelAnimationFrame(raf.current); running = false; onFrameRef.current(CLOSED, el.currentTime, false) }

    el.addEventListener("play", start)
    el.addEventListener("playing", start)
    el.addEventListener("pause", stop)
    el.addEventListener("ended", stop)
    if (!el.paused) start()
    return () => {
      cancelAnimationFrame(raf.current)
      el.removeEventListener("play", start)
      el.removeEventListener("playing", start)
      el.removeEventListener("pause", stop)
      el.removeEventListener("ended", stop)
    }
  }, [mediaRef, keyframes])
}
