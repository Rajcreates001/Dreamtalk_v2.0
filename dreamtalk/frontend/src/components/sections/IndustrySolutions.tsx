"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "motion/react"
import {
  Users, Heart, Building2, GraduationCap, Building, Microscope,
  ArrowRight, CheckCircle,
} from "lucide-react"
import { SectionWrapper, SectionHeading } from "./SectionWrapper"
import Link from "next/link"

const industries = [
  {
    id: "personal",
    icon: Users,
    label: "Personal",
    color: "#7C5CFF",
    solutions: [
      { title: "AI Companion", desc: "A personal Digital Twin that learns your preferences, remembers your stories, and grows with you." },
      { title: "Language Tutor", desc: "Practice any language with a patient, adaptive AI tutor who corrects and encourages." },
      { title: "Life Assistant", desc: "Manage schedules, set reminders, answer questions — your personal AI concierge." },
    ],
    metrics: ["5M+ Active Users", "94% Satisfaction", "4.8★ Rating"],
  },
  {
    id: "healthcare",
    icon: Heart,
    label: "Healthcare",
    color: "#22D3EE",
    solutions: [
      { title: "Patient Triage", desc: "24/7 intelligent triage that understands symptoms, assesses urgency, and guides patients." },
      { title: "Mental Health", desc: "Empathetic AI companions for mental wellness support, available anytime." },
      { title: "Medical Scribe", desc: "Automated clinical documentation that integrates with EHR systems." },
    ],
    metrics: ["HIPAA Compliant", "40% Less Wait", "500+ Hospitals"],
  },
  {
    id: "enterprise",
    icon: Building2,
    label: "Enterprise",
    color: "#42FFC6",
    solutions: [
      { title: "Sales Agent", desc: "Qualify leads, schedule meetings, and nurture prospects 24/7 across channels." },
      { title: "Support Agent", desc: "Resolve tickets instantly with knowledge-backed AI that escalates intelligently." },
      { title: "HR Assistant", desc: "Handle onboarding, benefits questions, and policy inquiries autonomously." },
    ],
    metrics: ["3x Productivity", "80% Cost Saving", "99.9% Uptime"],
  },
  {
    id: "education",
    icon: GraduationCap,
    label: "Education",
    color: "#FBBF24",
    solutions: [
      { title: "Virtual Tutor", desc: "One-on-one tutoring adapted to each student's learning style and pace." },
      { title: "Course Assistant", desc: "Answer questions about course material, assignments, and deadlines." },
    ],
    metrics: ["2x Learning Speed", "92% Retention", "10K+ Institutions"],
  },
  {
    id: "government",
    icon: Building,
    label: "Government",
    color: "#FF5F73",
    solutions: [
      { title: "Citizen Services", desc: "Handle permits, forms, and inquiries with multilingual AI assistants." },
      { title: "Policy Advisor", desc: "Answer policy questions and guide citizens through government services." },
    ],
    metrics: ["SOC 2 Certified", "Multi-language", "24/7 Service"],
  },
  {
    id: "research",
    icon: Microscope,
    label: "Research",
    color: "#7C5CFF",
    solutions: [
      { title: "Research Assistant", desc: "Analyze papers, summarize findings, and answer research questions." },
      { title: "Lab Assistant", desc: "Track experiments, manage protocols, and document results." },
    ],
    metrics: ["1M+ Papers", "Real-time Analysis", "Multi-modal"],
  },
]

export function IndustrySolutions() {
  const [active, setActive] = useState("personal")

  const current = industries.find((i) => i.id === active)!

  return (
    <SectionWrapper id="industries" bg="aurora" label="Chapter 11" reveal="blur">
      <SectionHeading
        label="Solutions"
        title="Built for every industry"
        description="DreamTalk powers Digital Humans across personal, healthcare, enterprise, education, government, and research."
      />

      {/* Industry tabs */}
      <div className="flex flex-wrap justify-center gap-2 mb-10">
        {industries.map((ind) => (
          <motion.button
            key={ind.id}
            onClick={() => setActive(ind.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              active === ind.id
                ? "bg-gradient-to-r from-[#7C5CFF]/20 to-[#00E5FF]/10 border border-[#7C5CFF]/30 text-[#F8FAFC] shadow-lg shadow-[#7C5CFF]/5"
                : "bg-white/[0.04] border border-white/[0.06] text-[#94A3B8] hover:text-[#CBD5E1]"
            }`}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <ind.icon className="h-4 w-4" style={{ color: ind.color }} />
            {ind.label}
            <span className="text-[10px] text-[#64748B] font-mono">{ind.solutions.length}</span>
          </motion.button>
        ))}
      </div>

      {/* Current industry detail */}
      <AnimatePresence mode="wait">
        <motion.div
          key={active}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -15 }}
          transition={{ duration: 0.3 }}
        >
          <div className="grid lg:grid-cols-3 gap-4 mb-8">
            {current.solutions.map((sol, i) => (
              <motion.div
                key={sol.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className="rounded-2xl bg-[#0F172A]/80 backdrop-blur-2xl border border-white/[0.06] p-6 hover:border-[#7C5CFF]/20 transition-all group"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ background: current.color }}
                  />
                  <h3 className="text-base font-semibold text-[#F8FAFC]">{sol.title}</h3>
                </div>
                <p className="text-sm text-[#94A3B8] leading-relaxed">{sol.desc}</p>
                <motion.div
                  className="mt-4 flex items-center gap-2 text-xs text-[#7C5CFF]"
                  whileHover={{ x: 4 }}
                >
                  <span>Learn more</span>
                  <ArrowRight className="h-3 w-3" />
                </motion.div>
              </motion.div>
            ))}
          </div>

          {/* Metrics bar */}
          <div className="flex flex-wrap justify-center gap-3">
            {current.metrics.map((metric) => (
              <motion.span
                key={metric}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium"
                style={{
                  background: `${current.color}10`,
                  color: current.color,
                  border: `1px solid ${current.color}20`,
                }}
              >
                <CheckCircle className="h-3 w-3" />
                {metric}
              </motion.span>
            ))}
          </div>
        </motion.div>
      </AnimatePresence>
    </SectionWrapper>
  )
}
