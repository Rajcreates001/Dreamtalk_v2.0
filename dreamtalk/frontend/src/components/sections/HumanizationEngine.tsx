"use client"

import { motion } from "motion/react"
import {
  MessageSquare, Heart, Brain, BookOpen, Zap, User, ArrowRight,
  Sparkles,
} from "lucide-react"
import { SectionWrapper, SectionHeading } from "./SectionWrapper"

const stages = [
  {
    icon: MessageSquare,
    label: "Conversation",
    desc: "Every interaction begins",
    color: "#7C5CFF",
  },
  {
    icon: Heart,
    label: "Emotion",
    desc: "Feels the context",
    color: "#FF5F73",
  },
  {
    icon: Brain,
    label: "Memory",
    desc: "Remembers everything",
    color: "#42FFC6",
  },
  {
    icon: BookOpen,
    label: "Knowledge",
    desc: "Learns continuously",
    color: "#FBBF24",
  },
  {
    icon: Zap,
    label: "Wisdom",
    desc: "Understands deeply",
    color: "#22D3EE",
  },
  {
    icon: User,
    label: "Humanized",
    desc: "A trusted Digital Twin",
    color: "#7C5CFF",
  },
]

export function HumanizationEngine() {
  return (
    <SectionWrapper id="humanization" bg="aurora" label="Chapter 05" reveal="slide">
      <SectionHeading
        label="Humanization Engine"
        title="From AI to trusted Digital Twin"
        description="DreamTalk's Humanization Engine transforms every conversation into deeper understanding, memory, and personality — making Digital Twins feel genuinely human."
      />

      {/* Evolution pipeline */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8 }}
        className="relative max-w-5xl mx-auto"
      >
        {/* Pipeline */}
        <div className="grid grid-cols-6 gap-3 lg:gap-4">
          {stages.map((stage, i) => (
            <motion.div
              key={stage.label}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 + i * 0.12 }}
              className="relative flex flex-col items-center text-center group"
            >
              {/* Stage icon */}
              <div className="relative mb-3">
                <motion.div
                  className="w-14 h-14 lg:w-16 lg:h-16 rounded-2xl flex items-center justify-center border border-white/[0.06] transition-all duration-500 group-hover:border-[#7C5CFF]/30"
                  style={{ background: `${stage.color}10` }}
                  whileHover={{ scale: 1.1, y: -4 }}
                  transition={{ type: "spring", stiffness: 300 }}
                >
                  <stage.icon className="h-6 w-6 lg:h-7 lg:w-7" style={{ color: stage.color }} />
                </motion.div>

                {/* Glow dot */}
                <motion.div
                  className="absolute -top-1 -right-1 w-3 h-3 rounded-full"
                  style={{ background: stage.color }}
                  animate={{
                    scale: [1, 1.5, 1],
                    opacity: [0.5, 1, 0.5],
                  }}
                  transition={{ duration: 2, delay: i * 0.3, repeat: Infinity }}
                />
              </div>

              {/* Label */}
              <h4 className="text-xs lg:text-sm font-semibold text-[#F8FAFC] mb-1">{stage.label}</h4>
              <p className="text-[10px] lg:text-xs text-[#64748B] leading-tight">{stage.desc}</p>

              {/* Arrow (except last) */}
              {i < stages.length - 1 && (
                <div className="hidden lg:block absolute -right-2.5 top-8">
                  <ArrowRight className="h-4 w-4 text-[#7C5CFF]/30" />
                </div>
              )}
            </motion.div>
          ))}
        </div>

        {/* Growth visualization */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 1 }}
          className="mt-16 rounded-2xl bg-[#0F172A]/60 border border-white/[0.06] p-8"
        >
          <div className="grid lg:grid-cols-2 gap-8 items-center">
            <div>
              <h3 className="text-lg font-semibold text-[#F8FAFC] mb-3">
                Continuous evolution
              </h3>
              <p className="text-sm text-[#94A3B8] leading-relaxed">
                DreamTalk Digital Humans don&apos;t stay static. Every conversation, every piece of knowledge,
                every emotional interaction makes them more human. The Humanization Engine continuously
                learns, adapts, and evolves — so your Digital Twin becomes more valuable over time.
              </p>
              <div className="flex flex-wrap gap-2 mt-4">
                {[
                  { label: "+127% Retention", color: "#42FFC6" },
                  { label: "94% Satisfaction", color: "#7C5CFF" },
                  { label: "6.2x Engagement", color: "#22D3EE" },
                ].map((stat) => (
                  <span
                    key={stat.label}
                    className="px-3 py-1 rounded-lg text-xs font-mono"
                    style={{ background: `${stat.color}10`, color: stat.color, border: `1px solid ${stat.color}20` }}
                  >
                    {stat.label}
                  </span>
                ))}
              </div>
            </div>

            {/* Evolution graph */}
            <div className="relative h-32 rounded-xl bg-white/[0.02] border border-white/[0.06] p-4 overflow-hidden">
              <svg className="w-full h-full" viewBox="0 0 200 60">
                <motion.path
                  d="M0,50 Q25,45 50,35 Q75,40 100,20 Q125,25 150,10 Q175,15 200,5"
                  fill="none"
                  stroke="url(#evolutionGrad)"
                  strokeWidth="2"
                  initial={{ pathLength: 0 }}
                  whileInView={{ pathLength: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 2, delay: 1.5 }}
                />
                <defs>
                  <linearGradient id="evolutionGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#7C5CFF" />
                    <stop offset="50%" stopColor="#22D3EE" />
                    <stop offset="100%" stopColor="#42FFC6" />
                  </linearGradient>
                </defs>
              </svg>
              <div className="flex justify-between mt-2">
                <span className="text-[10px] text-[#64748B] font-mono">Day 1</span>
                <span className="text-[10px] text-[#64748B] font-mono">Week 12</span>
                <span className="text-[10px] text-[#64748B] font-mono">Month 6</span>
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </SectionWrapper>
  )
}
