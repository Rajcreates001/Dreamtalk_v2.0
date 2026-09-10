"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { motion } from "motion/react"
import { Play, Pause, Download, Music, Loader2 } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface AudioPlayerProps {
  audioUrl: string | null
  isLoading?: boolean
  className?: string
}

const BAR_COUNT = 48

export function AudioPlayer({ audioUrl, isLoading = false, className }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef = useRef<number>(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)

  const generateBars = useCallback((time: number) => {
    const bars: number[] = []
    for (let i = 0; i < BAR_COUNT; i++) {
      const seed = Math.sin(i * 7.3 + time * 0.1) * 0.5 + 0.5
      const noise = Math.sin(i * 13.7 + time * 3.0) * 0.25 + 0.25
      const peak = Math.sin(i * 3.1 + time * 0.4) * 0.15
      const height = Math.max(0.08, seed * 0.6 + noise * 0.3 + peak)
      bars.push(height)
    }
    return bars
  }, [])

  const drawWaveform = useCallback((time: number, isActive: boolean) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    ctx.scale(dpr, dpr)

    const width = rect.width
    const height = rect.height
    ctx.clearRect(0, 0, width, height)

    const bars = generateBars(isActive ? time : 0)
    const gap = 2
    const barWidth = (width - gap * (BAR_COUNT - 1)) / BAR_COUNT

    bars.forEach((barHeight, i) => {
      const x = i * (barWidth + gap)
      const barH = barHeight * height * 0.8
      const y = (height - barH) / 2

      const gradient = ctx.createLinearGradient(x, y, x, y + barH)
      if (isActive) {
        gradient.addColorStop(0, "rgba(16, 185, 129, 0.9)")
        gradient.addColorStop(1, "rgba(59, 130, 246, 0.7)")
      } else {
        gradient.addColorStop(0, "rgba(156, 163, 175, 0.4)")
        gradient.addColorStop(1, "rgba(156, 163, 175, 0.2)")
      }
      ctx.fillStyle = gradient
      ctx.beginPath()
      ctx.roundRect(x, y, barWidth, barH, barWidth / 2)
      ctx.fill()
    })
  }, [generateBars])

  useEffect(() => {
    let startTime = Date.now()
    const animate = () => {
      const elapsed = Date.now() - startTime
      drawWaveform(elapsed, isPlaying)
      animRef.current = requestAnimationFrame(animate)
    }
    animate()
    return () => cancelAnimationFrame(animRef.current)
  }, [drawWaveform, isPlaying])

  const handlePlayPause = () => {
    const audio = audioRef.current
    if (!audio) return
    if (isPlaying) {
      audio.pause()
    } else {
      audio.play()
    }
  }

  const handleDownload = () => {
    if (!audioUrl) return
    const a = document.createElement("a")
    a.href = audioUrl
    a.download = "generated-audio.wav"
    a.click()
  }

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    return `${m}:${s.toString().padStart(2, "0")}`
  }

  if (isLoading) {
    return (
      <Card className={cn("overflow-hidden", className)}>
        <CardContent className="flex flex-col items-center justify-center gap-3 p-12">
          <Loader2 className="h-10 w-10 animate-spin text-muted-foreground/60" />
          <p className="text-sm text-muted-foreground">Generating audio...</p>
        </CardContent>
      </Card>
    )
  }

  if (!audioUrl) {
    return (
      <Card className={cn("overflow-hidden", className)}>
        <CardContent className="flex flex-col items-center justify-center gap-3 p-12">
          <div className="h-16 w-16 rounded-2xl bg-muted/30 flex items-center justify-center">
            <Music className="h-8 w-8 text-muted-foreground/40" />
          </div>
          <p className="text-sm text-muted-foreground">No audio generated yet</p>
          <p className="text-xs text-muted-foreground/50">Generated voice audio will appear here</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn("overflow-hidden rounded-2xl border border-border bg-card shadow-sm", className)}
    >
      <div className="p-4">
        <div className="flex items-center gap-4">
          <Button
            size="icon"
            variant={isPlaying ? "default" : "outline"}
            onClick={handlePlayPause}
            className="h-10 w-10 shrink-0 rounded-full"
          >
            {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 ml-0.5" />}
          </Button>
          <div className="flex-1 min-w-0">
            <canvas
              ref={canvasRef}
              className="w-full h-12 rounded-lg"
            />
          </div>
        </div>
        <div className="flex items-center justify-between mt-3">
          <span className="text-xs text-muted-foreground tabular-nums">
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>
          <Button
            size="sm"
            variant="ghost"
            onClick={handleDownload}
            className="text-xs gap-1.5"
          >
            <Download className="h-3.5 w-3.5" />
            Download
          </Button>
        </div>
      </div>

      <audio
        ref={audioRef}
        src={audioUrl}
        preload="metadata"
        onLoadedMetadata={() => {
          if (audioRef.current) setDuration(audioRef.current.duration)
        }}
        onTimeUpdate={() => {
          if (audioRef.current) setCurrentTime(audioRef.current.currentTime)
        }}
        onEnded={() => {
          setIsPlaying(false)
          if (audioRef.current) audioRef.current.currentTime = 0
        }}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
      />
    </motion.div>
  )
}
