"use client"

import { useState } from "react"
import { motion } from "motion/react"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { VrmViewer } from "@/components/vrm/vrm-viewer"
import { VideoResult } from "@/components/chat/video-result"
import { AudioPlayer } from "@/components/chat/audio-player"
import { BorderBeam } from "@/components/magic/border-beam"

interface AvatarResultProps {
  vrmModelUrl: string | null
  generatedVideoUrl: string | null
  generatedAudioUrl: string | null
  emotion?: string
  isSpeaking: boolean
  className?: string
}

export function AvatarResult({
  vrmModelUrl,
  generatedVideoUrl,
  generatedAudioUrl,
  emotion,
  isSpeaking,
  className,
}: AvatarResultProps) {
  const [modelLoaded, setModelLoaded] = useState(false)
  const [modelError, setModelError] = useState(false)
  const [tab, setTab] = useState("avatar")

  return (
    <div className={cn("relative flex flex-col", className)}>
      <Tabs value={tab} onValueChange={setTab} className="flex-1 flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border/50 shrink-0">
          <TabsList variant="line">
            <TabsTrigger value="avatar">3D Avatar</TabsTrigger>
            <TabsTrigger value="video">Generated Video</TabsTrigger>
            <TabsTrigger value="voice">Voice</TabsTrigger>
          </TabsList>
          <div className="flex items-center gap-2">
            {emotion && (
              <Badge variant="outline" className="text-[10px] gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                {emotion}
              </Badge>
            )}
            {isSpeaking && (
              <Badge variant="success" className="text-[10px] gap-1">
                <span className="flex gap-0.5">
                  <span className="h-2 w-[2px] rounded-full bg-emerald-400 animate-pulse" style={{ animationDelay: "0ms" }} />
                  <span className="h-3 w-[2px] rounded-full bg-emerald-400 animate-pulse" style={{ animationDelay: "150ms" }} />
                  <span className="h-2 w-[2px] rounded-full bg-emerald-400 animate-pulse" style={{ animationDelay: "300ms" }} />
                </span>
                Speaking
              </Badge>
            )}
          </div>
        </div>

        <TabsContent value="avatar" className="flex-1 relative overflow-hidden">
          {!modelLoaded && !modelError && (
            <div className="absolute inset-0 flex items-center justify-center z-10">
              <div className="flex flex-col items-center gap-2">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500/30 border-t-emerald-500" />
                <span className="text-xs text-muted-foreground">Loading avatar...</span>
              </div>
            </div>
          )}
          {modelError && (
            <div className="absolute inset-0 flex items-center justify-center z-10">
              <div className="w-40 h-40 rounded-full bg-gradient-to-br from-emerald-400/20 to-blue-400/20 flex items-center justify-center animate-pulse">
                <span className="text-3xl font-bold text-emerald-500/30">AI</span>
              </div>
            </div>
          )}
          <VrmViewer
            modelUrl={vrmModelUrl}
            onLoad={() => setModelLoaded(true)}
            onError={() => { setModelError(true); setModelLoaded(true) }}
            cameraDistance={3.2}
            className="w-full h-full"
          />
          <BorderBeam size={80} duration={10} colorFrom="#10b981" colorTo="#3b82f6" borderWidth={1} />
          {emotion && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="absolute bottom-4 left-4 z-10"
            >
              <Badge variant="outline" className="text-[11px] gap-1.5 bg-background/60 backdrop-blur-sm">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                {emotion}
              </Badge>
            </motion.div>
          )}
          {isSpeaking && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="absolute bottom-4 right-4 z-10"
            >
              <Badge variant="success" className="text-[11px] gap-1.5 bg-background/60 backdrop-blur-sm">
                <span className="flex gap-0.5">
                  <span className="h-2 w-[2px] rounded-full bg-emerald-400 animate-pulse" style={{ animationDelay: "0ms" }} />
                  <span className="h-3 w-[2px] rounded-full bg-emerald-400 animate-pulse" style={{ animationDelay: "150ms" }} />
                  <span className="h-2 w-[2px] rounded-full bg-emerald-400 animate-pulse" style={{ animationDelay: "300ms" }} />
                </span>
                Speaking
              </Badge>
            </motion.div>
          )}
        </TabsContent>

        <TabsContent value="video" className="flex-1 p-4">
          <VideoResult
            videoUrl={generatedVideoUrl}
            className="h-full"
          />
        </TabsContent>

        <TabsContent value="voice" className="flex-1 p-4">
          <AudioPlayer
            audioUrl={generatedAudioUrl}
            className="h-full"
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}
