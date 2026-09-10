"use client"

import { useState, useRef } from "react"
import { motion } from "motion/react"
import { Film, Download, Maximize2, Minimize2, Loader2 } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface VideoResultProps {
  videoUrl: string | null
  isLoading?: boolean
  className?: string
}

export function VideoResult({ videoUrl, isLoading = false, className }: VideoResultProps) {
  const [isFullscreen, setIsFullscreen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const toggleFullscreen = () => {
    if (!containerRef.current) return
    if (document.fullscreenElement) {
      document.exitFullscreen()
      setIsFullscreen(false)
    } else {
      containerRef.current.requestFullscreen()
      setIsFullscreen(true)
    }
  }

  const handleDownload = () => {
    if (!videoUrl) return
    const a = document.createElement("a")
    a.href = videoUrl
    a.download = "generated-video.mp4"
    a.click()
  }

  if (isLoading) {
    return (
      <Card className={cn("overflow-hidden", className)}>
        <CardContent className="flex flex-col items-center justify-center gap-3 p-12">
          <Loader2 className="h-10 w-10 animate-spin text-muted-foreground/60" />
          <p className="text-sm text-muted-foreground">Generating video...</p>
        </CardContent>
      </Card>
    )
  }

  if (!videoUrl) {
    return (
      <Card className={cn("overflow-hidden", className)}>
        <CardContent className="flex flex-col items-center justify-center gap-3 p-12">
          <div className="h-16 w-16 rounded-2xl bg-muted/30 flex items-center justify-center">
            <Film className="h-8 w-8 text-muted-foreground/40" />
          </div>
          <p className="text-sm text-muted-foreground">No video generated yet</p>
          <p className="text-xs text-muted-foreground/50">Generated videos will appear here</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn("relative overflow-hidden rounded-2xl border border-border bg-card shadow-sm", className)}
      ref={containerRef}
    >
      <div className="relative">
        <video
          src={videoUrl}
          controls
          className="w-full aspect-video bg-black"
          autoPlay={false}
          playsInline
        />
        {isFullscreen && (
          <div className="absolute top-3 right-3 z-10 flex gap-2">
            <Button
              size="icon-sm"
              variant="secondary"
              onClick={toggleFullscreen}
              className="bg-background/80 backdrop-blur-sm"
            >
              <Minimize2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}
      </div>
      <div className="flex items-center justify-between px-4 py-3">
        <span className="text-xs text-muted-foreground">Generated Video</span>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={toggleFullscreen}
            className="text-xs gap-1.5"
          >
            <Maximize2 className="h-3.5 w-3.5" />
            Fullscreen
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleDownload}
            className="text-xs gap-1.5"
          >
            <Download className="h-3.5 w-3.5" />
            Download
          </Button>
        </div>
      </div>
    </motion.div>
  )
}
