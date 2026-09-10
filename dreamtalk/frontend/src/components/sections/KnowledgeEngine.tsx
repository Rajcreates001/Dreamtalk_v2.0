"use client"

import { motion } from "motion/react"
import { BookOpen, FileText, Globe, Video, Mic, Image, Code, Download, ArrowRight } from "lucide-react"
import { SectionWrapper, SectionHeading, GlassCard } from "./SectionWrapper"

const sources = [
  { icon: FileText, label: "PDF", color: "#FF5F73" },
  { icon: FileText, label: "Word", color: "#3B82F6" },
  { icon: Globe, label: "Websites", color: "#22D3EE" },
  { icon: Video, label: "YouTube", color: "#FF5F73" },
  { icon: Mic, label: "Audio", color: "#FBBF24" },
  { icon: Image, label: "Images", color: "#42FFC6" },
  { icon: Code, label: "Code", color: "#7C5CFF" },
  { icon: Download, label: "Any Format", color: "#22D3EE" },
]

export function KnowledgeEngine() {
  return (
    <SectionWrapper id="knowledge" bg="knowledge" label="Chapter 07" reveal="blur">
      <SectionHeading
        label="Knowledge Engine"
        title="How your avatar learns"
        description="Upload any content — DreamTalk transforms it into structured intelligence your Digital Human can reason with."
      />

      {/* Knowledge pipeline */}
      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        className="relative max-w-5xl mx-auto mb-12"
      >
        {/* Pipeline stages */}
        <div className="grid grid-cols-4 gap-3 mb-8">
          {[
            { label: "Upload", icon: Download, color: "#7C5CFF", desc: "Documents, media, links" },
            { label: "Process", icon: Code, color: "#22D3EE", desc: "Parse, embed, index" },
            { label: "Graph", icon: Globe, color: "#42FFC6", desc: "Knowledge graph" },
            { label: "Reason", icon: BookOpen, color: "#FBBF24", desc: "Query & learn" },
          ].map((stage, i) => (
            <motion.div
              key={stage.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 + i * 0.15 }}
              className="relative flex flex-col items-center"
            >
              <div
                className="w-full rounded-xl p-4 text-center border border-white/[0.06]"
                style={{ background: `${stage.color}08` }}
              >
                <stage.icon className="h-6 w-6 mx-auto mb-2" style={{ color: stage.color }} />
                <h4 className="text-sm font-semibold text-[#F8FAFC]">{stage.label}</h4>
                <p className="text-[10px] text-[#64748B] mt-1">{stage.desc}</p>
              </div>
              {i < 3 && (
                <div className="hidden lg:block absolute -right-2.5 top-1/2 -translate-y-1/2">
                  <ArrowRight className="h-4 w-4 text-[#7C5CFF]/30" />
                </div>
              )}
            </motion.div>
          ))}
        </div>

        {/* Source types grid */}
        <div className="grid grid-cols-4 sm:grid-cols-8 gap-2">
          {sources.map((source, i) => (
            <motion.div
              key={source.label}
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 + i * 0.03 }}
              className="flex flex-col items-center gap-1.5 p-3 rounded-xl bg-[#0F172A]/40 border border-white/[0.04] hover:border-white/[0.1] transition-all group"
              whileHover={{ y: -2 }}
            >
              <source.icon className="h-4 w-4" style={{ color: source.color }} />
              <span className="text-[9px] text-[#64748B] font-medium">{source.label}</span>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* How it works */}
      <div className="grid lg:grid-cols-3 gap-4 max-w-5xl mx-auto">
        {[
          {
            title: "Document Intelligence",
            desc: "Upload PDFs, Word docs, research papers. We extract text, tables, images, and structure into a queryable knowledge graph.",
            color: "#7C5CFF",
          },
          {
            title: "Web & Media Learning",
            desc: "Crawl websites, transcribe YouTube videos, process audio recordings. Your avatar learns from any digital source.",
            color: "#22D3EE",
          },
          {
            title: "Continuous Updates",
            desc: "Add new knowledge anytime. The graph grows, connections strengthen, and your Digital Human becomes more knowledgeable.",
            color: "#42FFC6",
          },
        ].map((item, i) => (
          <motion.div
            key={item.title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 + i * 0.1 }}
            className="rounded-2xl bg-[#0F172A]/60 border border-white/[0.06] p-6 hover:bg-white/[0.03] transition-all"
          >
            <div className="w-3 h-3 rounded-full mb-4" style={{ background: item.color }} />
            <h3 className="text-base font-semibold text-[#F8FAFC] mb-2">{item.title}</h3>
            <p className="text-sm text-[#94A3B8] leading-relaxed">{item.desc}</p>
          </motion.div>
        ))}
      </div>
    </SectionWrapper>
  )
}
