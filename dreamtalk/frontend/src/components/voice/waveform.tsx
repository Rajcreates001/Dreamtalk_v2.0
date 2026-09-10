"use client"

import React, { useRef, useEffect, useState } from "react"

interface WaveformProps {
  analyserNode?: AnalyserNode | null
  color?: string
  height?: number
  barWidth?: number
  gap?: number
}

export function Waveform({
  analyserNode,
  color = "hsl(var(--primary))",
  height = 80,
  barWidth = 3,
  gap = 2,
}: WaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const draw = () => {
      const width = canvas.width
      const heightPx = canvas.height
      ctx.clearRect(0, 0, width, heightPx)

      if (!analyserNode) {
        // Draw idle waveform
        const barCount = Math.floor(width / (barWidth + gap))
        for (let i = 0; i < barCount; i++) {
          const x = i * (barWidth + gap)
          const h = 4 + Math.sin(Date.now() / 500 + i * 0.3) * 2
          ctx.fillStyle = color
          ctx.globalAlpha = 0.3
          ctx.fillRect(x, (heightPx - h) / 2, barWidth, h)
        }
        ctx.globalAlpha = 1
        animationRef.current = requestAnimationFrame(draw)
        return
      }

      const bufferLength = analyserNode.frequencyBinCount
      const dataArray = new Uint8Array(bufferLength)
      analyserNode.getByteFrequencyData(dataArray)

      const barCount = Math.floor(width / (barWidth + gap))
      const step = Math.floor(bufferLength / barCount)

      for (let i = 0; i < barCount; i++) {
        const value = dataArray[i * step] || 0
        const barHeight = (value / 255) * heightPx
        const x = i * (barWidth + gap)
        const y = (heightPx - barHeight) / 2

        ctx.fillStyle = color
        ctx.globalAlpha = 0.6 + (value / 255) * 0.4
        ctx.fillRect(x, y, barWidth, Math.max(barHeight, 2))
      }
      ctx.globalAlpha = 1
      animationRef.current = requestAnimationFrame(draw)
    }

    draw()
    return () => cancelAnimationFrame(animationRef.current)
  }, [analyserNode, color, height, barWidth, gap])

  return (
    <canvas
      ref={canvasRef}
      width={300}
      height={height}
      className="w-full rounded-lg"
      style={{ height: `${height}px` }}
    />
  )
}

// ── Helper: create analyser from MediaStream ──
export function useAnalyser(stream: MediaStream | null): AnalyserNode | null {
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null)
  const ctxRef = useRef<AudioContext | null>(null)

  useEffect(() => {
    if (!stream) {
      setAnalyser(null)
      return
    }
    const ctx = new AudioContext()
    ctxRef.current = ctx
    const source = ctx.createMediaStreamSource(stream)
    const node = ctx.createAnalyser()
    node.fftSize = 128
    source.connect(node)
    setAnalyser(node)

    return () => {
      ctx.close()
      setAnalyser(null)
    }
  }, [stream])

  return analyser
}
