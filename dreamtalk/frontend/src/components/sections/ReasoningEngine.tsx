"use client"

import { motion } from "motion/react"
import { Brain, ArrowRight, CircuitBoard, Cpu, Network, Zap } from "lucide-react"
import { SectionWrapper, SectionHeading } from "./SectionWrapper"

const steps = [
  { icon: CircuitBoard, label: "Input", desc: "User query or command", color: "#CC3A63" },
  { icon: Brain, label: "Context", desc: "Session history & persona", color: "#A2AB73" },
  { icon: Network, label: "Memory", desc: "Relevant past interactions", color: "#A2AB73" },
  { icon: Cpu, label: "Knowledge", desc: "Structured knowledge graph", color: "#D6A44C" },
  { icon: Zap, label: "Reasoning", desc: "Multi-step analysis", color: "#D84C63" },
]

export function ReasoningEngine() {
  return (
    <SectionWrapper id="reasoning" bg="alt" label="Chapter 08" reveal="slide">
      <SectionHeading
        label="Reasoning Engine"
        title="How your Digital Twin thinks"
        description="DreamTalk's Reasoning Engine combines context, memory, knowledge, and emotion to produce intelligent, nuanced responses."
      />

      {/* Reasoning pipeline */}
      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        className="max-w-4xl mx-auto"
      >
        {/* Pipeline steps */}
        <div className="flex flex-wrap justify-center gap-3 mb-8">
          {steps.map((step, i) => (
            <motion.div
              key={step.label}
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 + i * 0.1 }}
              className="flex items-center gap-2"
            >
              <div
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-white/[0.06]"
                style={{ background: `${step.color}08` }}
              >
                <step.icon className="h-4 w-4" style={{ color: step.color }} />
                <span className="text-xs font-medium text-foreground">{step.label}</span>
              </div>
              {i < steps.length - 1 && (
                <ArrowRight className="h-3.5 w-3.5 text-foreground-muted/40 hidden sm:block" />
              )}
            </motion.div>
          ))}
        </div>

        {/* Flow visualization */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.6 }}
          className="rounded-2xl bg-card/60 border border-white/[0.06] p-6 lg:p-8"
        >
          <div className="grid lg:grid-cols-2 gap-8">
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-foreground">Transparent reasoning</h3>
              <p className="text-sm text-foreground-muted leading-relaxed">
                Every response your Digital Twin generates is the result of a sophisticated reasoning process.
                DreamTalk combines short-term context, long-term memory, structured knowledge, and emotional
                awareness to produce responses that feel genuinely intelligent.
              </p>
              <div className="flex gap-2">
                {["Context-aware", "Memory-backed", "Knowledge-grounded", "Emotion-aware"].map((tag) => (
                  <span
                    key={tag}
                    className="px-2.5 py-1 rounded-lg text-[10px] font-medium text-[#CC3A63] bg-[#CC3A63]/10 border border-[#CC3A63]/20"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>

            {/* Reasoning animation */}
            <div className="relative h-40 rounded-xl bg-white/[0.02] border border-white/[0.06] overflow-hidden">
              <div className="absolute inset-0 flex items-center justify-center">
                <motion.div
                  className="flex items-center gap-4"
                  animate={{ x: [0, 20, 0, -20, 0] }}
                  transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                >
                  {[
                    { label: "?", color: "#CC3A63" },
                    { label: "...", color: "#A2AB73" },
                    { label: "!", color: "#A2AB73" },
                  ].map((item, i) => (
                    <motion.div
                      key={item.label}
                      className="w-12 h-12 rounded-xl flex items-center justify-center"
                      style={{ background: `${item.color}15`, border: `1px solid ${item.color}30` }}
                      animate={{ y: [0, -8, 0] }}
                      transition={{ duration: 2, delay: i * 0.3, repeat: Infinity }}
                    >
                      <span className="text-lg font-bold" style={{ color: item.color }}>{item.label}</span>
                    </motion.div>
                  ))}
                </motion.div>
              </div>

              {/* Animated particles */}
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="absolute w-1 h-1 rounded-full bg-[#CC3A63]"
                  animate={{
                    x: [0, 200, 0],
                    y: [30 + i * 40, 20 + i * 30, 30 + i * 40],
                    opacity: [0, 1, 0],
                  }}
                  transition={{ duration: 3, delay: i * 0.5, repeat: Infinity, ease: "linear" }}
                />
              ))}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </SectionWrapper>
  )
}
