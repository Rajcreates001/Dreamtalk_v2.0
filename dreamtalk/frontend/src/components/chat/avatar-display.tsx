"use client"

import { useState } from "react"
import { Maximize2, Minimize2 } from "lucide-react"
import { motion } from "motion/react"
import { cn } from "@/lib/utils"
import { BorderBeam } from "@/components/magic/border-beam"
import { Badge } from "@/components/ui/badge"

interface AvatarDisplayProps {
  isSpeaking: boolean
  emotion?: string
  className?: string
}

export function AvatarDisplay({ isSpeaking, emotion, className }: AvatarDisplayProps) {
  const [expanded, setExpanded] = useState(true)

  return (
    <motion.div
      layout
      transition={{ duration: 0.4, ease: "easeInOut" }}
      className={cn(
        "relative overflow-hidden rounded-2xl bg-gradient-to-b from-muted/30 to-muted/10 border border-border",
        expanded ? "h-full" : "h-48",
        className
      )}
    >
      <BorderBeam size={100} duration={8} colorFrom="#8F9A5E" colorTo="#853953" borderWidth={1} />

      <div className="relative z-10 flex flex-col items-center justify-center h-full p-6">
        <div className={cn(
          "relative rounded-full bg-gradient-to-br from-emerald-400/20 to-blue-400/20",
          expanded ? "w-48 h-48 mb-4" : "w-20 h-20 mb-2"
        )}>
          <div className={cn(
            "absolute inset-2 rounded-full bg-gradient-to-br from-emerald-500/10 to-blue-500/10 flex items-center justify-center",
            isSpeaking && "animate-pulse ring-2 ring-emerald-400/50 ring-offset-2 ring-offset-background"
          )}>
            <span className={cn("font-bold text-muted-foreground/40", expanded ? "text-4xl" : "text-lg")}>
              3D
            </span>
          </div>
        </div>

        {expanded && (
          <div className="text-center space-y-1">
            <h3 className="font-semibold text-lg">Dr. Aria</h3>
            <p className="text-sm text-muted-foreground">AI Health Companion</p>
            <div className="flex items-center justify-center gap-2 mt-2">
              <Badge variant={isSpeaking ? "success" : "secondary"}>
                {isSpeaking ? "Speaking" : "Listening"}
              </Badge>
              {emotion && <Badge variant="outline">{emotion}</Badge>}
            </div>
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="absolute top-3 right-3 z-20 h-8 w-8 rounded-full bg-background/50 backdrop-blur-sm flex items-center justify-center hover:bg-background/80 transition-colors"
      >
        {expanded ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
      </button>
    </motion.div>
  )
}
