"use client"

import { useCallback, useEffect, useRef, useState } from "react"

export type RecorderState = "idle" | "recording" | "denied" | "unsupported"

/**
 * Microphone recorder with a live amplitude track for the waveform.
 * Robust to permission denial and unsupported browsers (§47).
 */
export function useVoiceRecorder() {
  const [state, setState] = useState<RecorderState>("idle")
  const [elapsed, setElapsed] = useState(0)
  const [levels, setLevels] = useState<number[]>(() => Array(48).fill(0.04))
  const [error, setError] = useState<string | null>(null)

  const mediaRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<BlobPart[]>([])
  const audioCtxRef = useRef<AudioContext | null>(null)
  const rafRef = useRef<number>(0)
  const startedAtRef = useRef<number>(0)
  const resolveRef = useRef<((r: { blob: Blob; duration: number }) => void) | null>(null)

  const cleanup = useCallback(() => {
    cancelAnimationFrame(rafRef.current)
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    audioCtxRef.current?.close().catch(() => {})
    audioCtxRef.current = null
  }, [])

  useEffect(() => () => cleanup(), [cleanup])

  const start = useCallback(async () => {
    setError(null)
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setState("unsupported")
      setError("Recording is not supported in this browser.")
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      chunksRef.current = []

      const rec = new MediaRecorder(stream)
      mediaRef.current = rec
      rec.ondataavailable = (e) => e.data.size > 0 && chunksRef.current.push(e.data)
      rec.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: rec.mimeType || "audio/webm" })
        const duration = (Date.now() - startedAtRef.current) / 1000
        resolveRef.current?.({ blob, duration })
        resolveRef.current = null
      }

      // Live amplitude via analyser.
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      const ctx = new AudioCtx()
      audioCtxRef.current = ctx
      const source = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      const buf = new Uint8Array(analyser.frequencyBinCount)

      const tick = () => {
        analyser.getByteTimeDomainData(buf)
        let sum = 0
        for (let i = 0; i < buf.length; i++) {
          const v = (buf[i] - 128) / 128
          sum += v * v
        }
        const rms = Math.min(1, Math.sqrt(sum / buf.length) * 3.2)
        setLevels((prev) => [...prev.slice(1), Math.max(0.04, rms)])
        setElapsed((Date.now() - startedAtRef.current) / 1000)
        rafRef.current = requestAnimationFrame(tick)
      }

      startedAtRef.current = Date.now()
      rec.start()
      setState("recording")
      setElapsed(0)
      rafRef.current = requestAnimationFrame(tick)
    } catch {
      setState("denied")
      setError("Microphone access denied. You can upload a recording instead.")
    }
  }, [])

  const stop = useCallback(() => {
    return new Promise<{ blob: Blob; duration: number } | null>((resolve) => {
      const rec = mediaRef.current
      if (!rec || rec.state === "inactive") {
        resolve(null)
        return
      }
      resolveRef.current = (r) => resolve(r)
      rec.stop()
      setState("idle")
      cancelAnimationFrame(rafRef.current)
      setLevels(Array(48).fill(0.04))
      cleanup()
    })
  }, [cleanup])

  return { state, elapsed, levels, error, start, stop }
}
