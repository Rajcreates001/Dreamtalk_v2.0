"use client"

import { Brain, MessageCircle, Mic, Eye, Sparkles, Globe } from "lucide-react"
import { BlurFade } from "@/components/magic/blur-fade"
import { BentoGrid, BentoCard } from "@/components/magic/bento-grid"
import { Particles } from "@/components/magic/particles"
import { cn } from "@/lib/utils"

const features = [
  {
    name: "Natural Conversations",
    description: "Multi-turn dialogue with context awareness and emotional intelligence.",
    Icon: MessageCircle,
    href: "/conversations",
    cta: "Try it",
    background: (
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/15 via-transparent to-blue-500/10" />
    ),
    className: "lg:col-span-1 lg:row-span-2",
  },
  {
    name: "Real-Time Voice",
    description: "Low-latency speech recognition and lifelike text-to-speech synthesis.",
    Icon: Mic,
    href: "/conversations",
    cta: "Try it",
    background: (
      <div className="absolute inset-0 bg-gradient-to-tr from-blue-500/15 via-transparent to-emerald-500/10" />
    ),
    className: "lg:col-span-1",
  },
  {
    name: "Vision Aware",
    description: "Understands visual context through camera and image analysis.",
    Icon: Eye,
    href: "/conversations",
    cta: "Try it",
    background: (
      <div className="absolute inset-0 bg-gradient-to-bl from-purple-500/15 via-transparent to-emerald-500/10" />
    ),
    className: "lg:col-span-1",
  },
  {
    name: "3D Digital Human Presence",
    description: "Expressive VRM digital human with real-time lip-sync, emotions, and gestures.",
    Icon: Sparkles,
    href: "/conversations",
    cta: "Try it",
    background: (
      <Particles quantity={40} color="#10b981" className="absolute inset-0 opacity-60" staticity={80} ease={120} />
    ),
    className: "lg:col-span-2 lg:row-span-1",
  },
  {
    name: "Cognitive Memory",
    description: "Persistent memory across sessions using advanced memory systems.",
    Icon: Brain,
    href: "/conversations",
    cta: "Try it",
    background: (
      <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/10 via-transparent to-blue-500/10" />
    ),
    className: "lg:col-span-1",
  },
  {
    name: "Multi-Form Digital Beings",
    description: "Switch between VRM, Live2D, and photorealistic digital humans seamlessly.",
    Icon: Globe,
    href: "/conversations",
    cta: "Try it",
    background: (
      <div className="absolute inset-0 bg-gradient-to-tl from-blue-500/15 via-transparent to-emerald-500/10" />
    ),
    className: "lg:col-span-1",
  },
]

export function FeaturesSection() {
  return (
    <section id="features" className="relative w-full py-24 px-6 lg:px-16 xl:px-24 bg-background">
      <div className="absolute inset-0 bg-gradient-to-b from-background via-emerald-500/3 to-background pointer-events-none" />

      <div className="relative max-w-7xl mx-auto">
        <BlurFade inView offset={10} blur="4px">
          <div className="text-center space-y-4 mb-16">
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
              Everything You Need
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              Powered by 12 integrated AI systems working together in real-time
            </p>
          </div>
        </BlurFade>

        <BlurFade inView offset={20} blur="6px" delay={0.2}>
          <BentoGrid className="grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 auto-rows-[16rem] gap-4">
            {features.map((feature, i) => (
              <BentoCard key={feature.name} {...feature} />
            ))}
          </BentoGrid>
        </BlurFade>
      </div>
    </section>
  )
}
