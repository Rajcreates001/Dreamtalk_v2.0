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
    color: "#7C5CFF",
    gradient: "from-[#7C5CFF]/20 to-[#7C5CFF]/5",
  },
  {
    icon: Mic,
    title: "Voice Synthesis",
    desc: "Clone any voice with 99% accuracy. Support for 50+ languages and regional accents.",
    color: "#22D3EE",
    gradient: "from-[#22D3EE]/20 to-[#22D3EE]/5",
  },
  {
    icon: Heart,
    title: "Emotion AI",
    desc: "Real-time sentiment analysis and emotion-aware responses for natural conversations.",
    color: "#FF5F73",
    gradient: "from-[#FF5F73]/20 to-[#FF5F73]/5",
  },
  {
    icon: BookOpen,
    title: "Knowledge Engine",
    desc: "Process PDFs, websites, videos, and documents. Your avatar learns from everything.",
    color: "#FBBF24",
    gradient: "from-[#FBBF24]/20 to-[#FBBF24]/5",
  },
  {
    icon: Cpu,
    title: "Memory System",
    desc: "Persistent memory that remembers every conversation, preference, and context across sessions.",
    color: "#42FFC6",
    gradient: "from-[#42FFC6]/20 to-[#42FFC6]/5",
  },
  {
    icon: Brain,
    title: "Reasoning Engine",
    desc: "Multi-step reasoning with context, knowledge, and memory for complex decision-making.",
    color: "#7C5CFF",
    gradient: "from-[#7C5CFF]/20 to-[#7C5CFF]/5",
  },
  {
    icon: Globe,
    title: "Multi-Platform",
    desc: "Deploy to web, mobile, WhatsApp, Slack, Discord, Teams, kiosks, and more.",
    color: "#22D3EE",
    gradient: "from-[#22D3EE]/20 to-[#22D3EE]/5",
  },
  {
    icon: Zap,
    title: "Real-time Streaming",
    desc: "Sub-200ms response time with streaming conversations and live avatar animations.",
    color: "#FBBF24",
    gradient: "from-[#FBBF24]/20 to-[#FBBF24]/5",
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
            background: "radial-gradient(circle, rgba(124,92,255,0.08) 0%, transparent 70%)",
          }}
          animate={{ scale: [1, 1.05, 1], rotate: [0, 5, 0] }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute w-56 h-56 rounded-full border border-[#7C5CFF]/10"
          animate={{ rotate: 360 }}
          transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
        />

        {/* Central hub */}
        <motion.div
          className="relative z-10 w-36 h-36 rounded-full bg-gradient-to-br from-[#7C5CFF] via-[#00E5FF] to-[#42FFC6] p-[3px]"
          animate={{ boxShadow: ["0 0 40px rgba(124,92,255,0.3)", "0 0 60px rgba(124,92,255,0.5)", "0 0 40px rgba(124,92,255,0.3)"] }}
          transition={{ duration: 3, repeat: Infinity }}
        >
          <div className="w-full h-full rounded-full bg-[#070B14] flex items-center justify-center flex-col">
            <Bot className="h-8 w-8 text-[#7C5CFF] mb-1" />
            <span className="text-[10px] font-bold text-[#F8FAFC]">DreamTalk</span>
            <span className="text-[8px] text-[#42FFC6]">● Live</span>
          </div>
        </motion.div>
      </motion.div>

      {/* Features Grid */}
      <StaggerGrid className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {features.map((feature) => (
          <GlassCard key={feature.title}>
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center mb-4 border border-white/[0.06] transition-all duration-500 group-hover:scale-110"
              style={{ background: `linear-gradient(135deg, ${feature.color}20, transparent)` }}
            >
              <feature.icon className="h-5 w-5" style={{ color: feature.color }} />
            </div>
            <h3 className="text-base font-semibold text-[#F8FAFC] mb-2">{feature.title}</h3>
            <p className="text-sm text-[#94A3B8] leading-relaxed">{feature.desc}</p>
            <motion.div
              className="mt-4 h-px w-0 bg-gradient-to-r from-transparent via-[#7C5CFF]/30 to-transparent"
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
          className="group inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-[#7C5CFF] to-[#00E5FF] text-white text-sm font-semibold shadow-lg shadow-[#7C5CFF]/20 hover:shadow-[#7C5CFF]/30 transition-all"
        >
          <Layers className="h-4 w-4" />
          Explore the Platform
          <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
        </Link>
      </motion.div>
    </SectionWrapper>
  )
}
