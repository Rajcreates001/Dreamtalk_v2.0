"use client"

import { motion } from "motion/react"
import {
  Brain, Database, Mic, Heart, Cpu, Globe, BookOpen, Zap,
  Sparkles, ArrowRight, Bot, Layers,
} from "lucide-react"
import { SectionWrapper, SectionHeading, StaggerGrid, staggerItem, GlassCard } from "./SectionWrapper"
import Link from "next/link"

const features = [
  {
    icon: Bot,
    title: "Avatar Intelligence",
    desc: "Create custom digital humans with full control over appearance, voice, and personality.",
    color: "#CC3A63",
    gradient: "from-[#CC3A63]/20 to-[#CC3A63]/5",
  },
  {
    icon: Mic,
    title: "Voice Synthesis",
    desc: "Clone any voice with 99% accuracy. Support for 50+ languages and regional accents.",
    color: "#A2AB73",
    gradient: "from-[#A2AB73]/20 to-[#A2AB73]/5",
  },
  {
    icon: Heart,
    title: "Emotion AI",
    desc: "Real-time sentiment analysis and emotion-aware responses for natural conversations.",
    color: "#D84C63",
    gradient: "from-[#D84C63]/20 to-[#D84C63]/5",
  },
  {
    icon: BookOpen,
    title: "Knowledge Engine",
    desc: "Process PDFs, websites, videos, and documents. Your avatar learns from everything.",
    color: "#D6A44C",
    gradient: "from-[#D6A44C]/20 to-[#D6A44C]/5",
  },
  {
    icon: Cpu,
    title: "Memory System",
    desc: "Persistent memory that remembers every conversation, preference, and context across sessions.",
    color: "#A2AB73",
    gradient: "from-[#A2AB73]/20 to-[#A2AB73]/5",
  },
  {
    icon: Brain,
    title: "Reasoning Engine",
    desc: "Multi-step reasoning with context, knowledge, and memory for complex decision-making.",
    color: "#CC3A63",
    gradient: "from-[#CC3A63]/20 to-[#CC3A63]/5",
  },
  {
    icon: Globe,
    title: "Multi-Platform",
    desc: "Deploy to web, mobile, WhatsApp, Slack, Discord, Teams, kiosks, and more.",
    color: "#A2AB73",
    gradient: "from-[#A2AB73]/20 to-[#A2AB73]/5",
  },
  {
    icon: Zap,
    title: "Real-time Streaming",
    desc: "Sub-200ms response time with streaming conversations and live avatar animations.",
    color: "#D6A44C",
    gradient: "from-[#D6A44C]/20 to-[#D6A44C]/5",
  },
]

export function DreamTalkSolution() {
  return (
    <SectionWrapper id="solution" bg="solution" label="Chapter 03" reveal="slide">
      <SectionHeading
        label="The Platform"
        title="The Operating System for Digital Humans"
        description="DreamTalk replaces fragmented AI tools with a unified platform where Digital Humans are created, trained, deployed, and continuously evolve."
      />

      {/* Central OS Visualization */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 1, delay: 0.2 }}
        className="relative flex items-center justify-center py-12 mb-12"
      >
        {/* Outer glow rings */}
        <motion.div
          className="absolute w-72 h-72 rounded-full"
          style={{
            background: "radial-gradient(circle, rgba(204,58,99,0.08) 0%, transparent 70%)",
          }}
          animate={{ scale: [1, 1.05, 1], rotate: [0, 5, 0] }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute w-56 h-56 rounded-full border border-[#CC3A63]/10"
          animate={{ rotate: 360 }}
          transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
        />

        {/* Central hub */}
        <motion.div
          className="relative z-10 w-36 h-36 rounded-full bg-gradient-to-br from-[#CC3A63] via-[#A2AB73] to-[#A2AB73] p-[3px]"
          animate={{ boxShadow: ["0 0 40px rgba(204,58,99,0.3)", "0 0 60px rgba(204,58,99,0.5)", "0 0 40px rgba(204,58,99,0.3)"] }}
          transition={{ duration: 3, repeat: Infinity }}
        >
          <div className="w-full h-full rounded-full bg-background flex items-center justify-center flex-col">
            <Bot className="h-8 w-8 text-[#CC3A63] mb-1" />
            <span className="text-[10px] font-bold text-foreground">DreamTalk</span>
            <span className="text-[8px] text-[#A2AB73]">● Live</span>
          </div>
        </motion.div>
      </motion.div>

      {/* Features Grid */}
      <StaggerGrid className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {features.map((feature) => (
          <GlassCard key={feature.title}>
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center mb-4 border border-foreground/[0.06] transition-all duration-500 group-hover:scale-110"
              style={{ background: `linear-gradient(135deg, ${feature.color}20, transparent)` }}
            >
              <feature.icon className="h-5 w-5" style={{ color: feature.color }} />
            </div>
            <h3 className="text-base font-semibold text-foreground mb-2">{feature.title}</h3>
            <p className="text-sm text-foreground-muted leading-relaxed">{feature.desc}</p>
            <motion.div
              className="mt-4 h-px w-0 bg-gradient-to-r from-transparent via-[#CC3A63]/30 to-transparent"
              whileInView={{ width: "100%" }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, delay: 0.3 }}
            />
          </GlassCard>
        ))}
      </StaggerGrid>

      {/* Bottom CTA */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.6 }}
        className="flex justify-center mt-12"
      >
        <Link
          href="/signup"
          className="group inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-white text-sm font-semibold shadow-lg shadow-[#CC3A63]/20 hover:shadow-[#CC3A63]/30 transition-all"
        >
          <Layers className="h-4 w-4" />
          Explore the Platform
          <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
        </Link>
      </motion.div>
    </SectionWrapper>
  )
}
