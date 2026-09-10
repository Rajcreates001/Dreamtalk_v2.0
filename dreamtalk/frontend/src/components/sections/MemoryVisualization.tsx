"use client"

import { motion } from "motion/react"
import { Brain, Zap, Layers, Clock, Network, GitBranch } from "lucide-react"
import { SectionWrapper, SectionHeading, StaggerGrid, staggerItem, GlassCard } from "./SectionWrapper"

const memoryTypes = [
  {
    icon: Zap,
    title: "Working Memory",
    desc: "Short-term context during active conversations with 7-item capacity. Retains what matters right now.",
    color: "#CC3A63",
  },
  {
    icon: Brain,
    title: "Episodic Memory",
    desc: "Past conversations, user preferences, and interaction history. Every session becomes lasting knowledge.",
    color: "#A2AB73",
  },
  {
    icon: Layers,
    title: "Semantic Memory",
    desc: "Knowledge graphs built from uploaded documents, websites, and content. Structured intelligence.",
    color: "#A2AB73",
  },
  {
    icon: GitBranch,
    title: "Procedural Memory",
    desc: "Learned patterns, skills, and response strategies refined through thousands of interactions.",
    color: "#D6A44C",
  },
]

export function MemoryVisualization() {
  return (
    <SectionWrapper id="memory" bg="memory" label="Chapter 06" reveal="scale">
      <SectionHeading
        label="Memory Engine"
        title="Avatars that never forget"
        description="Multi-layered memory architecture for persistent, contextual conversations that grow richer over time."
      />

      {/* Memory visualization */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8 }}
        className="relative flex items-center justify-center py-16 mb-12"
      >
        {/* Neural network visualization */}
        <div className="relative w-full max-w-lg h-64">
          {/* Connection lines */}
          <svg className="absolute inset-0 w-full h-full" viewBox="0 0 400 200">
            {[
              [50, 100, 120, 60],
              [50, 100, 120, 140],
              [50, 100, 200, 100],
              [120, 60, 200, 100],
              [120, 140, 200, 100],
              [200, 100, 280, 60],
              [200, 100, 280, 140],
              [280, 60, 350, 100],
              [280, 140, 350, 100],
            ].map(([x1, y1, x2, y2], i) => (
              <motion.line
                key={i}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke="rgba(204,58,99,0.15)"
                strokeWidth="1"
                initial={{ pathLength: 0 }}
                whileInView={{ pathLength: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 1, delay: 0.3 + i * 0.05 }}
              />
            ))}
          </svg>

          {/* Neural nodes */}
          {[
            { x: 50, y: 100, color: "#CC3A63", label: "Input", size: 28 },
            { x: 120, y: 60, color: "#A2AB73", label: "Process", size: 22 },
            { x: 120, y: 140, color: "#A2AB73", label: "Analyze", size: 22 },
            { x: 200, y: 100, color: "#A2AB73", label: "Memory", size: 32 },
            { x: 280, y: 60, color: "#D6A44C", label: "Store", size: 22 },
            { x: 280, y: 140, color: "#D6A44C", label: "Recall", size: 22 },
            { x: 350, y: 100, color: "#D84C63", label: "Output", size: 28 },
          ].map((node, i) => (
            <motion.div
              key={node.label}
              initial={{ scale: 0, opacity: 0 }}
              whileInView={{ scale: 1, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.5 + i * 0.08, type: "spring" }}
              className="absolute flex flex-col items-center"
              style={{ left: `${(node.x / 400) * 100}%`, top: `${(node.y / 200) * 100}%`, transform: "translate(-50%, -50%)" }}
            >
              <motion.div
                className="rounded-full flex items-center justify-center"
                style={{
                  width: node.size,
                  height: node.size,
                  background: `${node.color}20`,
                  border: `2px solid ${node.color}40`,
                }}
                animate={{
                  boxShadow: [`0 0 0px ${node.color}00`, `0 0 12px ${node.color}30`, `0 0 0px ${node.color}00`],
                }}
                transition={{ duration: 2, delay: i * 0.3, repeat: Infinity }}
              >
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ background: node.color }}
                />
              </motion.div>
              <span className="text-[9px] text-foreground-muted mt-1 font-mono">{node.label}</span>
            </motion.div>
          ))}

          {/* Data flow particles */}
          {[0, 1, 2].map((particle) => (
            <motion.div
              key={particle}
              className="absolute w-1.5 h-1.5 rounded-full bg-[#CC3A63]"
              initial={{ left: "10%", top: "50%", opacity: 0 }}
              animate={{
                left: ["10%", "90%"],
                top: ["50%", "45%", "55%", "50%"],
                opacity: [0, 1, 1, 0],
              }}
              transition={{
                duration: 3,
                delay: particle * 1.2,
                repeat: Infinity,
                ease: "linear",
              }}
            />
          ))}
        </div>
      </motion.div>

      {/* Memory types */}
      <StaggerGrid className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {memoryTypes.map((mem) => (
          <GlassCard key={mem.title}>
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center mb-4 border border-white/[0.06]"
              style={{ background: `${mem.color}15` }}
            >
              <mem.icon className="h-5 w-5" style={{ color: mem.color }} />
            </div>
            <h3 className="text-base font-semibold text-foreground mb-2">{mem.title}</h3>
            <p className="text-sm text-foreground-muted leading-relaxed">{mem.desc}</p>
            <div className="mt-4 flex items-center gap-2">
              <div className="flex-1 h-1 rounded-full bg-white/[0.06]">
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: mem.color }}
                  initial={{ width: "60%" }}
                  animate={{ width: ["70%", "85%", "70%"] }}
                  transition={{ duration: 3, repeat: Infinity, repeatType: "reverse" }}
                />
              </div>
              <span className="text-[10px] text-foreground-muted font-mono">Active</span>
            </div>
          </GlassCard>
        ))}
      </StaggerGrid>
    </SectionWrapper>
  )
}
