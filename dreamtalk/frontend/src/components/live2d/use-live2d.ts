// Dreamtalk - Live2D Animation
// Based on PersonaEngine (MIT License)
// Source: handcrafted-persona-engine

import { useRef, useEffect, useCallback, useState } from "react"
import { EmotionAnimationService } from "./emotion-service"
import { IdleBlinkingService } from "./idle-blinking-service"
import { VBridgerLipSyncService } from "./lipsync-service"

export interface UseLive2DOptions {
  modelUrl: string | null
  autoStart?: boolean
}

export function useLive2D({ modelUrl, autoStart = true }: UseLive2DOptions) {
  const modelRef = useRef<any>(null)
  const emotionServiceRef = useRef(new EmotionAnimationService())
  const blinkingServiceRef = useRef(new IdleBlinkingService())
  const lipsyncServiceRef = useRef(new VBridgerLipSyncService())
  const animFrameRef = useRef<number>(0)
  const lastTimeRef = useRef(0)
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const setParameter = useCallback((name: string, value: number) => {
    modelRef.current?.setParameter(name, value)
  }, [])

  const setExpression = useCallback((id: string) => {
    modelRef.current?.setExpression(id)
  }, [])

  const startMotion = useCallback((group: string) => {
    modelRef.current?.startRandomMotion(group)
  }, [])

  const playPhonemes = useCallback((phonemes: Array<{ phoneme: string; start: number; end: number }>) => {
    lipsyncServiceRef.current.startPhonemes(phonemes)
  }, [])

  const playEmotions = useCallback((emotions: Array<{ emoji: string; timestamp: number }>) => {
    emotionServiceRef.current.startPlayback(emotions)
  }, [])

  const updateTime = useCallback((time: number) => {
    lipsyncServiceRef.current.updateTime(time)
    emotionServiceRef.current.updateEmotionAtTime(time)
  }, [])

  useEffect(() => {
    if (!modelUrl) return
    const url = modelUrl

    let mounted = true

    async function loadModel() {
      try {
        const { CubismLive2DModel } = await import("./live2d-model")
        const m = new CubismLive2DModel("doctor-avatar")
        await m.load(url)

        if (!mounted) {
          m.dispose()
          return
        }

        modelRef.current = m
        emotionServiceRef.current.setModel(m)
        blinkingServiceRef.current.setModel(m)
        lipsyncServiceRef.current.setModel(m)
        setLoaded(true)

        lastTimeRef.current = performance.now()

        const loop = (now: number) => {
          const dt = Math.min((now - lastTimeRef.current) / 1000, 0.05)
          lastTimeRef.current = now

          emotionServiceRef.current.update(dt)
          blinkingServiceRef.current.update(dt)
          lipsyncServiceRef.current.updateNeutral(dt)
          m.update(dt)

          animFrameRef.current = requestAnimationFrame(loop)
        }

        animFrameRef.current = requestAnimationFrame(loop)
      } catch (err) {
        if (mounted) setError(err instanceof Error ? err.message : "Failed to load model")
      }
    }

    loadModel()

    return () => {
      mounted = false
      cancelAnimationFrame(animFrameRef.current)
      modelRef.current?.dispose()
      modelRef.current = null
    }
  }, [modelUrl])

  return {
    loaded,
    error,
    setParameter,
    setExpression,
    startMotion,
    playPhonemes,
    playEmotions,
    updateTime,
  }
}
