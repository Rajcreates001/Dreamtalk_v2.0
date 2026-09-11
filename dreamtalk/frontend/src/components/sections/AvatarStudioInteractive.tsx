"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "motion/react"
import {
  Camera, Mic, Heart, BookOpen, Brain, Globe, User, Sparkles,
  ChevronRight, Check,
} from "lucide-react"
import { SectionWrapper, SectionHeading } from "./SectionWrapper"

const stages = [
  { id: "photo", icon: Camera, label: "Photo", color: "#CC3A63", desc: "Upload a reference photo or generate procedurally" },
  { id: "voice", icon: Mic, label: "Voice", color: "#A2AB73", desc: "Clone or synthesize a voice in 50+ languages" },
  { id: "personality", icon: Heart, label: "Personality", color: "#D84C63", desc: "Define traits, tone, and behavioral patterns" },
  { id: "knowledge", icon: BookOpen, label: "Knowledge", color: "#D6A44C", desc: "Upload documents, websites, and media" },
  { id: "memory", icon: Brain, label: "Memory", color: "#A2AB73", desc: "Configure memory architecture and persistence" },
  { id: "deploy", icon: Globe, label: "Deploy", color: "#CC3A63", desc: "Deploy to web, mobile, API, or platform" },
]

export function AvatarStudioInteractive() {
  const [activeStage, setActiveStage] = useState(0)
  const [completed, setCompleted] = useState<number[]>([])

  const handleNext = () => {
    if (!completed.includes(activeStage)) {
      setCompleted([...completed, activeStage])
    }
    if (activeStage < stages.length - 1) {
      setActiveStage(activeStage + 1)
    }
  }

  const handlePrev = () => {
    if (activeStage > 0) {
      setActiveStage(activeStage - 1)
    }
  }

  return (
    <SectionWrapper id="studio" bg="alt" label="Chapter 04" reveal="blur">
      <SectionHeading
        label="Avatar Studio"
        title="Create your Digital Human"
        description="A complete pipeline for bringing your Digital Human to life — from appearance to deployment."
      />

      <div className="grid lg:grid-cols-2 gap-12 items-center">
        {/* Pipeline visualization */}
        <motion.div
          initial={{ opacity: 0, x: -30 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="relative"
        >
          {/* Pipeline stages */}
          <div className="space-y-3">
            {stages.map((stage, i) => {
              const isActive = i === activeStage
              const isCompleted = completed.includes(i)
              const isNext = !isCompleted && !isActive
              return (
                <motion.button
                  key={stage.id}
                  onClick={() => setActiveStage(i)}
                  className={`w-full flex items-center gap-4 p-4 rounded-xl transition-all duration-500 text-left ${
                    isActive
                      ? "bg-card/90 border border-[#CC3A63]/30 shadow-lg shadow-[#CC3A63]/5"
                      : isCompleted
                        ? "bg-card/60 border border-[#A2AB73]/20"
                        : "bg-card/40 border border-foreground/[0.04] hover:border-foreground/[0.1]"
                  }`}
                  whileHover={{ x: 4 }}
                  transition={{ duration: 0.2 }}
                >
                  {/* Stage number */}
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-all ${
                      isActive
                        ? "bg-gradient-to-br from-[#CC3A63] to-[#A2AB73] shadow-lg shadow-[#CC3A63]/20"
                        : isCompleted
                          ? "bg-[#A2AB73]/20 border border-[#A2AB73]/30"
                          : "bg-foreground/[0.04] border border-foreground/[0.06]"
                    }`}
                  >
                    {isCompleted ? (
                      <Check className="h-4 w-4 text-[#A2AB73]" />
                    ) : (
                      <span className={`text-sm font-bold ${isActive ? "text-white" : "text-foreground-muted"}`}>
                        {String(i + 1).padStart(2, "0")}
                      </span>
                    )}
                  </div>

                  {/* Stage info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <stage.icon className="h-4 w-4" style={{ color: isActive ? stage.color : "#8A8178" }} />
                      <span className={`text-sm font-semibold ${isActive ? "text-foreground" : "text-foreground"}`}>
                        {stage.label}
                      </span>
                    </div>
                    <p className="text-xs text-foreground-muted mt-0.5 line-clamp-1">{stage.desc}</p>
                  </div>

                  {/* Active indicator */}
                  {isActive && (
                    <motion.div
                      layoutId="pipeline-active"
                      className="w-1.5 h-8 rounded-full bg-gradient-to-b from-[#CC3A63] to-[#A2AB73]"
                    />
                  )}
                </motion.button>
              )
            })}
          </div>

          {/* Progress bar */}
          <div className="mt-6 flex items-center gap-3">
            <div className="flex-1 h-1 rounded-full bg-foreground/[0.06] overflow-hidden">
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-[#CC3A63] to-[#A2AB73]"
                initial={{ width: "0%" }}
                animate={{ width: `${(completed.length / stages.length) * 100}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
            <span className="text-xs text-foreground-muted font-mono">{completed.length}/{stages.length}</span>
          </div>
        </motion.div>

        {/* Right side - Active stage detail */}
        <motion.div
          key={activeStage}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="relative"
        >
          <div className="rounded-[24px] bg-gradient-to-b from-card/90 to-card/60 backdrop-blur-2xl border border-foreground/[0.06] p-8">
            <div className="flex items-center gap-3 mb-6">
              <div
                className="w-12 h-12 rounded-2xl flex items-center justify-center"
                style={{ background: `${stages[activeStage].color}20` }}
              >
                {(() => {
                  const StageIcon = stages[activeStage].icon
                  return <StageIcon className="h-6 w-6" style={{ color: stages[activeStage].color }} />
                })()}
              </div>
              <div>
                <h3 className="text-lg font-bold text-foreground">{stages[activeStage].label}</h3>
                <p className="text-sm text-foreground-muted">Step {activeStage + 1} of {stages.length}</p>
              </div>
            </div>

            <p className="text-foreground leading-relaxed mb-8">
              {stages[activeStage].desc}
            </p>

            {/* Stage preview visualization */}
            <div className="rounded-xl bg-foreground/[0.02] border border-foreground/[0.06] p-6 mb-6">
              <div className="flex items-center justify-center h-32">
                <motion.div
                  className="flex flex-col items-center gap-2"
                  animate={{ y: [0, -4, 0] }}
                  transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                >
                  {(() => {
                    const StageIcon = stages[activeStage].icon
                    return (
                      <>
                        <div
                          className="w-16 h-16 rounded-2xl flex items-center justify-center"
                          style={{ background: `${stages[activeStage].color}15` }}
                        >
                          <StageIcon className="h-8 w-8" style={{ color: stages[activeStage].color }} />
                        </div>
                        <span className="text-xs text-foreground-muted">{stages[activeStage].label} configuration</span>
                      </>
                    )
                  })()}
                </motion.div>
              </div>
            </div>

            {/* Navigation */}
            <div className="flex items-center gap-3">
              <motion.button
                onClick={handlePrev}
                disabled={activeStage === 0}
                className="px-4 py-2 rounded-xl text-sm font-medium text-foreground border border-foreground/[0.06] disabled:opacity-30 hover:bg-foreground/[0.04] transition-all"
                whileHover={{ x: activeStage > 0 ? -2 : 0 }}
              >
                Previous
              </motion.button>
              <motion.button
                onClick={handleNext}
                disabled={activeStage === stages.length - 1}
                className="flex-1 px-4 py-2 rounded-xl bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-white text-sm font-semibold disabled:opacity-30 transition-all flex items-center justify-center gap-2"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {activeStage === stages.length - 1 ? "Complete" : "Next Step"}
                <ChevronRight className="h-4 w-4" />
              </motion.button>
            </div>
          </div>

          {/* Floating decoration */}
          <motion.div
            className="absolute -top-4 -right-4 w-24 h-24 rounded-full bg-gradient-to-br from-[#CC3A63]/10 to-transparent blur-2xl"
            animate={{ scale: [1, 1.2, 1], rotate: [0, 10, 0] }}
            transition={{ duration: 6, repeat: Infinity }}
          />
        </motion.div>
      </div>

      {/* Demo CTA */}
      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ delay: 0.8 }}
        className="text-center mt-12"
      >
        <p className="text-sm text-foreground-muted">
          <span className="text-[#CC3A63]">Interactive preview</span> — Click through each stage to explore the creation pipeline
        </p>
      </motion.div>
    </SectionWrapper>
  )
}
