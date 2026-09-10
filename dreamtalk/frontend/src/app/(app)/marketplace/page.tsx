"use client"

import { useState } from "react"
import { motion } from "motion/react"
import { cn } from "@/lib/utils"
import { Bot, Mic, BookOpen, Globe, Download, Star, Store } from "lucide-react"

const ITEMS = [
  { name: "Customer Support Agent", type: "Template", downloads: "2.4K", rating: 4.8, color: "#CC3A63", desc: "Full-featured customer support AI avatar" },
  { name: "Premium Voice Pack", type: "Voice", downloads: "1.8K", rating: 4.9, color: "#A2AB73", desc: "12 high-quality natural voices" },
  { name: "Medical Knowledge Base", type: "Knowledge", downloads: "3.2K", rating: 4.7, color: "#A2AB73", desc: "HIPAA-compliant medical training data" },
  { name: "Japanese Language Pack", type: "Language", downloads: "892", rating: 4.6, color: "#CC3A63", desc: "Fluency pack for Japanese" },
  { name: "Enterprise Analytics", type: "Integration", downloads: "1.1K", rating: 4.5, color: "#D6A44C", desc: "Connect with your BI tools" },
  { name: "Emotion Engine Pro", type: "Module", downloads: "567", rating: 4.9, color: "#B03A5E", desc: "Advanced emotional intelligence module" },
]

const CATEGORIES = ["All", "Templates", "Voices", "Knowledge", "Languages", "Integrations", "Modules"]

const TYPE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  Template: Bot,
  Voice: Mic,
  Knowledge: BookOpen,
  Language: Globe,
  Integration: Globe,
  Module: Bot,
}

export default function MarketplacePage() {
  const [activeCat, setActiveCat] = useState("All")

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-foreground">Marketplace</h1>
        <p className="text-sm text-foreground-muted mt-1">Discover templates, voices, and integrations</p>
      </div>

      {/* Categories */}
      <div className="flex gap-2 flex-wrap">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCat(cat)}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              activeCat === cat
                ? "bg-[#CC3A63]/20 text-[#CC3A63] border border-[#CC3A63]/30"
                : "bg-white/[0.04] text-foreground-muted hover:text-foreground border border-transparent"
            )}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {ITEMS.map((item, i) => {
          const Icon = TYPE_ICONS[item.type] || Bot
          return (
            <motion.div
              key={item.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="p-4 rounded-xl bg-card/80 border border-white/[0.06] hover:bg-card hover:border-white/[0.12] transition-all group"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${item.color}15`, color: item.color }}>
                  <Icon className="h-5 w-5" />
                </div>
                <div className="flex items-center gap-1">
                  <Star className="h-3 w-3 text-[#D6A44C]" />
                  <span className="text-xs text-foreground">{item.rating}</span>
                </div>
              </div>
              <h3 className="text-sm font-semibold text-foreground">{item.name}</h3>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[10px] text-foreground-muted px-2 py-0.5 rounded-md bg-white/[0.04]">{item.type}</span>
                <span className="text-[10px] text-foreground-muted">{item.downloads} downloads</span>
              </div>
              <p className="text-xs text-foreground-muted mt-2">{item.desc}</p>
              <button className="w-full mt-3 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-white/[0.04] border border-white/[0.06] text-xs text-foreground-muted hover:text-foreground hover:bg-white/[0.08] transition-all group">
                <Download className="h-3 w-3" />
                Install
              </button>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
