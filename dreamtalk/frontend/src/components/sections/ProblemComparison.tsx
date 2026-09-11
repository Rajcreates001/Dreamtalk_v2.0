"use client"

import { useState } from "react"
import { motion } from "motion/react"
import {
  MessageSquare, Mic, Bot, Search, FileText, Cpu, BarChart3, Database,
  X, Brain, Heart, Sparkles, Users,
} from "lucide-react"
import { SectionWrapper, SectionHeading } from "./SectionWrapper"

/* ── DATA ── */

const FRAGMENTED_TOOLS = [
  { icon: MessageSquare, label: "Chatbot", desc: "Scripted conversations", limit: "No long-term memory", color: "#D84C63", solution: "Persistent memory across sessions" },
  { icon: Mic, label: "Voice AI", desc: "Speech synthesis", limit: "No emotion or tone", color: "#C77B54", solution: "Emotional voice synthesis" },
  { icon: Bot, label: "Avatar Gen", desc: "Static 3D models", limit: "No intelligence", color: "#D6A44C", solution: "Living Digital Human brain" },
  { icon: Search, label: "Search", desc: "Keyword matching", limit: "No understanding", color: "#FFD54F", solution: "Semantic understanding" },
  { icon: FileText, label: "OCR / Vision", desc: "Text extraction", limit: "No context", color: "#D84C63", solution: "Context-aware processing" },
  { icon: Cpu, label: "Automation", desc: "Rule-based flows", limit: "No adaptation", color: "#C77B54", solution: "Self-adapting AI" },
  { icon: BarChart3, label: "Analytics", desc: "Dashboard reports", limit: "No action", color: "#D6A44C", solution: "Autonomous decision-making" },
  { icon: Database, label: "Knowledge Base", desc: "Static documents", limit: "No reasoning", color: "#FFD54F", solution: "Dynamic reasoning engine" },
]

const PIPELINE_STAGES = [
  "Knowledge Ingestion",
  "Memory Formation",
  "Reasoning",
  "Voice Synthesis",
  "Identity Creation",
  "Digital Twin",
]

const SOLVED_LIMITS = [
  "Persistent Memory",
  "Emotional Voice",
  "Living Intelligence",
  "Semantic Search",
  "Context Awareness",
  "Self Adaptation",
  "Autonomous Action",
  "Dynamic Reasoning",
]

const RING_CONFIGS = [
  { label: "Knowledge", color: "#CC3A63", radius: 150 },
  { label: "Memory", color: "#A2AB73", radius: 128 },
  { label: "Voice", color: "#A2AB73", radius: 106 },
  { label: "Reasoning", color: "#D6A44C", radius: 84 },
  { label: "Personality", color: "#D84C63", radius: 62 },
  { label: "Relationship", color: "#CC3A63", radius: 40 },
  { label: "Deployment", color: "#0EA5E9", radius: 20 },
]

/* ── SUB-COMPONENTS ── */

function FragmentedCard({
  tool,
  index,
  hoveredTool,
  setHoveredTool,
}: {
  tool: (typeof FRAGMENTED_TOOLS)[number]
  index: number
  hoveredTool: number | null
  setHoveredTool: (i: number | null) => void
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4, delay: 0.15 + index * 0.06 }}
      onMouseEnter={() => setHoveredTool(index)}
      onMouseLeave={() => setHoveredTool(null)}
      className={`relative rounded-2xl p-4 transition-all duration-300 cursor-default group
        ${hoveredTool === index ? "border-red-500/40 shadow-[0_0_30px_rgba(216,76,99,0.08)]" : "border-white/[0.06]"}
        ${hoveredTool !== null && hoveredTool !== index ? "opacity-50" : "opacity-100"}
      `}
      style={{
        background: `linear-gradient(145deg, var(--card), var(--surface))`,
        border: "1px solid",
        borderColor: hoveredTool === index ? "rgba(216,76,99,0.4)" : "var(--border)",
      }}
    >
      <div
        className="absolute inset-0 rounded-2xl"
        style={{
          animation: `fragment-drift ${4 + index * 0.5}s ease-in-out infinite`,
          animationDelay: `${index * 0.6}s`,
        }}
      />
      <div className="relative z-10 flex items-start gap-3">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style={{ background: `${tool.color}18` }}>
          <tool.icon className="h-4 w-4" style={{ color: tool.color }} />
        </div>
        <div className="min-w-0 flex-1">
          <h4 className="text-sm font-semibold text-foreground mb-0.5">{tool.label}</h4>
          <p className="text-[11px] text-foreground-muted">{tool.desc}</p>
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: hoveredTool === index ? "auto" : 0, opacity: hoveredTool === index ? 1 : 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="flex items-center gap-1 mt-2 text-[10px] text-[#D84C63] font-mono">
              <X className="h-2.5 w-2.5 shrink-0" />
              <span>{tool.limit}</span>
            </div>
          </motion.div>
        </div>
      </div>
      <div className="absolute -top-1 -right-1 flex gap-0.5">
        {[0, 1, 2].map((d) => (
          <div
            key={d}
            className="w-1 h-1 rounded-full"
            style={{
              background: tool.color,
              opacity: 0.15,
              animation: `disconnect-pulse 2s ease-in-out infinite`,
              animationDelay: `${d * 0.3}s`,
            }}
          />
        ))}
      </div>
    </motion.div>
  )
}

function PipelineStage({ stage, index }: { stage: string; index: number }) {
  const isLast = index === PIPELINE_STAGES.length - 1
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4, delay: 0.2 + index * 0.1 }}
      className="flex items-center gap-3 group"
    >
      <div className="relative flex items-center justify-center shrink-0">
        <div
          className={`w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold transition-all duration-500
            ${isLast ? "bg-gradient-to-br from-[#CC3A63] to-[#A2AB73] text-white shadow-[0_0_12px_rgba(204,58,99,0.3)]" : "bg-white/[0.06] text-foreground-muted"}`}
          style={{
            animation: isLast ? `chamber-pulse 2s ease-in-out infinite` : `pipeline-pulse 3s ease-in-out infinite`,
            animationDelay: `${index * 0.4}s`,
          }}
        >
          {index + 1}
        </div>
        {!isLast && (
          <div className="absolute top-7 left-1/2 -translate-x-1/2 w-px h-10 bg-gradient-to-b from-white/[0.06] to-white/[0.02]" />
        )}
      </div>
      <span
        className={`text-[11px] font-mono tracking-wider leading-tight transition-all duration-500
          ${isLast ? "text-foreground font-semibold" : "text-foreground-muted group-hover:text-foreground-muted"}`}
      >
        {stage}
      </span>
    </motion.div>
  )
}

function DigitalTwinChamber({ hoveredTool }: { hoveredTool: number | null }) {
  const solutionText = hoveredTool !== null ? SOLVED_LIMITS[hoveredTool] : null

  return (
    <div className="relative w-full aspect-square max-w-[480px] mx-auto group">
      {/* Outer glow layers */}
      <div className="absolute inset-[5%] rounded-full blur-[100px] animate-chamber-glow" style={{ background: "radial-gradient(circle, rgba(204,58,99,0.12), transparent 70%)" }} />
      <div className="absolute inset-[20%] rounded-full blur-[70px]" style={{ background: "radial-gradient(circle, rgba(162,171,115,0.06), transparent 70%)", animation: "chamber-glow 5s ease-in-out infinite 1.5s" }} />
      <div className="absolute inset-[35%] rounded-full blur-[50px]" style={{ background: "radial-gradient(circle, rgba(162,171,115,0.04), transparent 70%)", animation: "chamber-glow 7s ease-in-out infinite 3s" }} />

      {/* 7 Orbiting Rings */}
      {RING_CONFIGS.map((ring) => (
        <div
          key={ring.label}
          className="absolute inset-0 flex items-center justify-center pointer-events-none"
          style={{
            animation: `orbit-ring ${14 + ring.radius * 0.02}s linear infinite`,
            animationDirection: ring.radius % 2 === 0 ? "normal" : "reverse",
            zIndex: 10 - ring.radius,
          }}
        >
          <div className="absolute rounded-full border" style={{ width: ring.radius * 2, height: ring.radius * 2, borderColor: `${ring.color}10`, borderWidth: "1px" }} />
          <div
            className="absolute w-2 h-2 rounded-full"
            style={{
              background: ring.color,
              left: `calc(50% + ${ring.radius - 1}px)`,
              top: "50%",
              marginTop: -4,
              boxShadow: `0 0 8px ${ring.color}50`,
              animation: `node-glow 2.5s ease-in-out infinite`,
              animationDelay: `${ring.radius * 0.012}s`,
            }}
          />
          <div
            className="absolute text-[7px] font-mono tracking-widest uppercase pointer-events-none select-none opacity-0 transition-opacity duration-300 group-hover:opacity-100"
            style={{ color: ring.color, left: `calc(50% + ${ring.radius * 0.6}px)`, top: `calc(50% - ${ring.radius * 0.88}px)`, transform: "translate(-50%, -50%)" }}
          >
            {ring.label}
          </div>
        </div>
      ))}

      {/* Particle flow — inward from rings to avatar */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {[0, 1, 2, 3, 4, 5, 6].map((i) => {
          const color = RING_CONFIGS[i % RING_CONFIGS.length].color
          return (
            <div
              key={`in-${i}`}
              className="absolute w-0.5 h-0.5 rounded-full"
              style={{
                background: color,
                left: `${30 + Math.sin(i * 1.2) * 25 + 50}%`,
                top: `${30 + Math.cos(i * 1.5) * 25 + 50}%`,
                transform: "translate(-50%, -50%)",
                animation: `flow-inward ${3 + i * 0.3}s ease-in-out infinite`,
                animationDelay: `${i * 0.4}s`,
                opacity: 0.6,
              }}
            />
          )
        })}
      </div>

      {/* Digital Human */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="relative w-28 h-28">
          <div className="absolute inset-[10%] rounded-full blur-[25px] animate-body-glow" style={{ background: "radial-gradient(circle, rgba(204,58,99,0.25), transparent 70%)" }} />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-16 h-16">
            <div className="w-full h-full rounded-[40%_40%_45%_45%] bg-gradient-to-b from-[#CC3A63] to-[#A2AB73] p-[1.5px]" style={{ animation: "breathe 4s ease-in-out infinite" }}>
              <div className="w-full h-full rounded-[40%_40%_45%_45%] bg-background flex items-center justify-center flex-col gap-1">
                <div className="flex gap-3.5">
                  <div className="w-[3px] h-[3px] rounded-full bg-[#A2AB73] shadow-[0_0_4px_#A2AB73]" style={{ animation: "blink 4s ease-in-out infinite" }} />
                  <div className="w-[3px] h-[3px] rounded-full bg-[#A2AB73] shadow-[0_0_4px_#A2AB73]" style={{ animation: "blink 4s ease-in-out infinite 0.1s" }} />
                </div>
                <div className="w-3 h-[1.5px] rounded-full bg-[#CC3A63]/40" style={{ animation: "breathe 4s ease-in-out infinite 0.5s" }} />
              </div>
            </div>
            <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 flex gap-0.5">
              {[0, 1, 2].map((d) => (
                <div key={d} className="w-0.5 h-0.5 rounded-full" style={{ background: "#CC3A63", animation: `thinking-pulse 1.5s ease-in-out infinite`, animationDelay: `${d * 0.3}s`, opacity: 0.6 }} />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Solution overlay */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: hoveredTool !== null ? 1 : 0, y: hoveredTool !== null ? 0 : 10 }}
        transition={{ duration: 0.25 }}
        className="absolute bottom-[2%] left-1/2 -translate-x-1/2 z-30"
      >
        {solutionText && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-card/90 border border-[#A2AB73]/20 backdrop-blur-xl whitespace-nowrap">
            <Sparkles className="h-3 w-3 text-[#A2AB73]" />
            <span className="text-[10px] font-mono text-[#A2AB73] tracking-wider">{solutionText}</span>
          </div>
        )}
      </motion.div>

      {/* Status badges */}
      <div className="absolute top-[1%] left-[3%] z-20">
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-white/[0.03] border border-white/[0.06]">
          <span className="relative flex h-1.5 w-1.5"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#A2AB73] opacity-75" /><span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-[#A2AB73]" /></span>
          <span className="text-[7px] font-mono text-foreground/40 tracking-wider">ACTIVE</span>
        </div>
      </div>
      <div className="absolute top-[12%] right-[0%] z-20">
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-white/[0.03] border border-white/[0.06]">
          <Brain className="h-2 w-2 text-[#A2AB73]" />
          <span className="text-[7px] font-mono text-foreground/30 tracking-wider">LEARNING</span>
        </div>
      </div>
      <div className="absolute bottom-[12%] right-[4%] z-20">
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-white/[0.03] border border-white/[0.06]">
          <Heart className="h-2 w-2 text-[#D84C63]" />
          <span className="text-[7px] font-mono text-foreground/30 tracking-wider">EMPATHETIC</span>
        </div>
      </div>
      <div className="absolute top-[30%] left-[0%] z-20">
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-white/[0.03] border border-white/[0.06]">
          <Users className="h-2 w-2 text-[#CC3A63]" />
          <span className="text-[7px] font-mono text-foreground/30 tracking-wider">RELATIONSHIP</span>
        </div>
      </div>
    </div>
  )
}

/* ── MAIN COMPONENT ── */

export function ProblemComparison() {
  const [hoveredTool, setHoveredTool] = useState<number | null>(null)

  return (
    <SectionWrapper id="problem" bg="problem" label="Chapter 02" reveal="none" spacing="compact">
      <SectionHeading
        label="The Challenge"
        title="Why traditional AI falls short"
        description="Businesses, healthcare, and individuals face critical gaps in how they interact with AI today."
      />

      {/* THREE-COLUMN STORYTELLING — 4+2+6 asymmetric layout */}
      <div className="grid md:grid-cols-6 lg:grid-cols-12 gap-6 lg:gap-8 max-w-7xl mx-auto">
        {/* COL 1: TODAY — Fragmented AI (4 cols) */}
        <motion.div
          initial={{ opacity: 0, x: -40 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="md:col-span-3 lg:col-span-4 relative"
        >
          <div className="mb-4">
            <span className="text-[10px] uppercase tracking-[0.25em] text-[#D84C63]/50 font-mono">TODAY</span>
            <h3 className="text-lg font-bold text-foreground mt-1">Fragmented AI Ecosystem</h3>
            <p className="text-xs text-foreground-muted mt-1 max-w-md">
              Disconnected tools with no shared memory, intelligence, or personality.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {FRAGMENTED_TOOLS.map((tool, i) => (
              <FragmentedCard key={tool.label} tool={tool} index={i} hoveredTool={hoveredTool} setHoveredTool={setHoveredTool} />
            ))}
          </div>

          {/* Broken connection SVG */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ opacity: 0.06, zIndex: 0 }}>
            <defs>
              <linearGradient id="broken-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#D84C63" />
                <stop offset="100%" stopColor="transparent" />
              </linearGradient>
            </defs>
            {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
              <line
                key={i}
                x1={`${10 + (i % 4) * 25}%`}
                y1={`${15 + Math.floor(i / 4) * 35}%`}
                x2={`${35 + (i % 4) * 25}%`}
                y2={`${15 + Math.floor(i / 4) * 35 + 10}%`}
                stroke="url(#broken-grad)" strokeWidth="0.5" strokeDasharray="3 4"
                style={{ animation: `dash-line 1.5s linear infinite`, animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </svg>

          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 1.2 }}
            className="mt-3 p-2.5 rounded-xl bg-[#D84C63]/[0.04] border border-[#D84C63]/[0.1]"
          >
            <div className="flex items-center gap-2 text-xs text-[#D84C63]/70">
              <X className="h-3 w-3 shrink-0" />
              <span className="font-mono text-[10px] tracking-wider">8 tools • No context • No integration • No memory</span>
            </div>
          </motion.div>
        </motion.div>

        {/* COL 2: TRANSFORMATION (2 cols) — hidden on mobile/tablet */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="hidden lg:flex lg:col-span-2 flex-col items-center justify-center relative"
        >
          <div className="mb-6 text-center">
            <span className="text-[10px] uppercase tracking-[0.25em] text-foreground/20 font-mono">TRANSFORMATION</span>
          </div>

          <div className="space-y-3">
            {PIPELINE_STAGES.map((stage, i) => (
              <PipelineStage key={stage} stage={stage} index={i} />
            ))}
          </div>

          <div className="absolute top-0 bottom-0 left-1/2 -translate-x-1/2 w-px overflow-hidden opacity-[0.1]">
            <div className="w-full h-full" style={{ background: "linear-gradient(to bottom, #D84C63, #CC3A63, #A2AB73, #A2AB73)", animation: "energy-flow 3s ease-in-out infinite" }} />
          </div>

          <div className="absolute inset-0 pointer-events-none overflow-hidden">
            {[0, 1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="absolute w-1 h-1 rounded-full"
                style={{
                  background: i < 2 ? "#D84C63" : i < 4 ? "#CC3A63" : "#A2AB73",
                  left: `${45 + (i % 3) * 5}%`,
                  top: "-5%",
                  opacity: 0.6,
                  animation: `particle-fall ${2 + i * 0.3}s ease-in-out infinite`,
                  animationDelay: `${i * 0.5}s`,
                }}
              />
            ))}
          </div>
        </motion.div>

        {/* Mobile pipeline separator — visible only on small screens */}
        <div className="md:col-span-3 lg:hidden flex items-center justify-center py-4">
          <div className="flex items-center gap-2">
            <div className="h-px w-12 bg-gradient-to-r from-[#D84C63] to-[#CC3A63]" />
            <span className="text-[8px] uppercase tracking-[0.3em] text-foreground/20 font-mono">UNIFIED</span>
            <div className="h-px w-12 bg-gradient-to-l from-[#CC3A63] to-[#A2AB73]" />
          </div>
        </div>

        {/* COL 3: DREAMTALK — Digital Twin OS (6 cols) */}
        <motion.div
          initial={{ opacity: 0, x: 40 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="md:col-span-3 lg:col-span-6 relative"
        >
          <div className="mb-4 text-right">
            <span className="text-[10px] uppercase tracking-[0.25em] text-[#A2AB73]/50 font-mono">DREAMTALK</span>
            <h3 className="text-lg font-bold text-foreground mt-1">
              One <span className="bg-gradient-to-r from-[#CC3A63] via-[#A2AB73] to-[#A2AB73] bg-clip-text text-transparent">Digital Twin OS</span>
            </h3>
            <p className="text-xs text-foreground-muted mt-1 max-w-md ml-auto">
              Unified intelligence with persistent memory, emotional awareness, and continuous learning.
            </p>
          </div>

          <DigitalTwinChamber hoveredTool={hoveredTool} />

          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 1.5 }}
            className="mt-3 p-2.5 rounded-xl bg-[#CC3A63]/[0.05] border border-[#CC3A63]/[0.12]"
          >
            <div className="flex items-center gap-2 text-xs text-[#CC3A63]/70">
              <Sparkles className="h-3 w-3 shrink-0" />
              <span className="font-mono text-[10px] tracking-wider">ONE unified OS • Shared memory • Emotional AI • Live reasoning</span>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </SectionWrapper>
  )
}
