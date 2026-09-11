"use client"

import { useMemo } from "react"
import { motion } from "motion/react"
import { Mic, Languages, Music, Volume2 } from "lucide-react"
import { SectionWrapper, SectionHeading } from "./SectionWrapper"

/** A single CSS-animated waveform bar — zero JS per frame */
function WaveBar({ height, index }: { height: number; index: number }) {
  return (
    <div
      className="w-1.5 rounded-full"
      style={{
        height: `${height}px`,
        background: "linear-gradient(to top, #CC3A63, #A2AB73)",
        animation: `waveform-pulse 1.5s ease-in-out infinite`,
        animationDelay: `${index * 0.03}s`,
        willChange: "transform, opacity",
      }}
    />
  )
}

export function VoiceIntelligence() {
  // Pre-compute heights deterministically (no Math.random at render time)
  const bars = useMemo(
    () =>
      Array.from({ length: 30 }).map((_, i) => ({
        height: 10 + Math.sin(i * 0.3) * 20 + 15,
        index: i,
      })),
    []
  )

  return (
    <SectionWrapper id="voice" bg="voice" label="Chapter 09" reveal="scale">
      <SectionHeading
        label="Voice Intelligence"
        title="Natural, emotional, multilingual speech"
        description="DreamTalk's Voice AI delivers human-quality speech synthesis with emotion, accent control, and real-time adaptation."
      />

      <div className="grid lg:grid-cols-2 gap-8 items-center max-w-5xl mx-auto">
        {/* Voice visualization */}
        <div className="relative h-64 rounded-2xl bg-card/60 border border-foreground/[0.06] overflow-hidden">
          {/* Waveform — CSS animated, no JS per frame */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex items-end gap-1 h-32">
              {bars.map((bar) => (
                <WaveBar key={bar.index} height={bar.height} index={bar.index} />
              ))}
            </div>
          </div>

          {/* Floating frequency rings — CSS animated */}
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="absolute rounded-full border border-[#CC3A63]/20"
              style={{
                width: 80 + i * 60,
                height: 80 + i * 60,
                top: "50%",
                left: "50%",
                transform: "translate(-50%, -50%)",
                animation: `frequency-pulse 3s ease-in-out ${i * 0.5}s infinite`,
              }}
            />
          ))}

          {/* Status */}
          <div className="absolute bottom-4 left-4 flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#A2AB73] opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#A2AB73]" />
            </span>
            <span className="text-[10px] text-foreground-muted font-mono">Voice Active</span>
          </div>
        </div>

        {/* Features */}
        <div className="space-y-3">
          {[
            { icon: Mic, label: "Voice Cloning", desc: "99% accuracy from 30 seconds of audio", color: "#CC3A63" },
            { icon: Languages, label: "50+ Languages", desc: "Regional accents and dialects supported", color: "#A2AB73" },
            { icon: Music, label: "Emotion Control", desc: "Happy, calm, urgent, empathetic tones", color: "#A2AB73" },
            { icon: Volume2, label: "Real-time Streaming", desc: "Sub-200ms latency for natural conversations", color: "#D6A44C" },
          ].map((feat, i) => (
            <motion.div
              key={feat.label}
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 + i * 0.08 }}
              className="flex items-center gap-3 p-3 rounded-xl bg-card/40 border border-foreground/[0.04] hover:bg-foreground/[0.03] transition-all"
            >
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: `${feat.color}15` }}
              >
                <feat.icon className="h-4 w-4" style={{ color: feat.color }} />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-foreground">{feat.label}</h4>
                <p className="text-xs text-foreground-muted">{feat.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </SectionWrapper>
  )
}
