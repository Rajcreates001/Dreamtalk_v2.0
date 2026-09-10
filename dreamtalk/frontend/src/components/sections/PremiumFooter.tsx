"use client"

import { useState } from "react"
import { motion } from "motion/react"
import { Sparkles, ArrowUp, Heart, Mail } from "lucide-react"
import Link from "next/link"

const footerColumns = [
  {
    title: "Platform",
    items: ["Avatar Studio", "Voice Engine", "Knowledge Base", "Memory System", "Emotion AI", "API & SDK"],
  },
  {
    title: "Solutions",
    items: ["Personal", "Healthcare", "Enterprise", "Education", "Government", "Research"],
  },
  {
    title: "Company",
    items: ["About", "Blog", "Careers", "Partners", "Press Kit", "Contact"],
  },
  {
    title: "Resources",
    items: ["Documentation", "API Reference", "Tutorials", "Community", "Status", "Security"],
  },
]

export function PremiumFooter() {
  const [email, setEmail] = useState("")

  return (
    <footer className="relative z-10 border-t border-white/[0.04] bg-background">
      {/* Top divider glow */}
      <div className="h-px bg-gradient-to-r from-transparent via-[#CC3A63]/30 to-transparent" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Main footer grid */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-6 gap-8 mb-12">
          {/* Brand */}
          <div className="lg:col-span-2">
            <Link href="/" className="flex items-center gap-2.5 mb-4 group">
              <div className="relative w-8 h-8">
                <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-[#CC3A63] to-[#A2AB73] animate-breathe" />
                <Sparkles className="relative h-4 w-4 text-white absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
              </div>
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] bg-clip-text text-transparent">
                DreamTalk
              </span>
            </Link>
            <p className="text-sm text-foreground-muted max-w-xs leading-relaxed mb-6">
              The operating system for digital humans. Create, train, and deploy intelligent AI avatars
              with voice, emotion, memory, and knowledge.
            </p>
            {/* Newsletter */}
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-foreground-muted" />
                <input
                  name="newsletter-email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Get product updates"
                  className="w-full bg-card/60 border border-white/[0.06] rounded-lg pl-9 pr-3 py-2 text-xs text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-1 focus:ring-[#CC3A63]/30 transition-all"
                />
              </div>
              <motion.button
                className="px-3 py-2 rounded-lg bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-white text-xs font-medium"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                Subscribe
              </motion.button>
            </div>
          </div>

          {/* Link columns */}
          {footerColumns.map((col) => (
            <div key={col.title}>
              <h4 className="text-sm font-semibold text-foreground mb-4">{col.title}</h4>
              <ul className="space-y-2.5">
                {col.items.map((item) => (
                  <li key={item}>
                    <button className="text-sm text-foreground-muted hover:text-foreground-muted transition-colors">{item}</button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4 pt-8 border-t border-white/[0.04]">
          <p className="text-xs text-foreground-muted flex items-center gap-1.5">
            © 2026 DreamTalk. Built with <Heart className="h-3 w-3 text-[#D84C63]" /> for Digital Humans
          </p>
          <div className="flex items-center gap-4">
            {["Privacy", "Terms", "Cookies", "Licenses"].map((item) => (
              <button key={item} className="text-xs text-foreground-muted hover:text-foreground-muted transition-colors">
                {item}
              </button>
            ))}
            <motion.button
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
              className="w-8 h-8 rounded-lg bg-card/80 border border-white/[0.06] flex items-center justify-center text-foreground-muted hover:text-foreground transition-all"
              whileHover={{ y: -2 }}
            >
              <ArrowUp className="h-4 w-4" />
            </motion.button>
          </div>
        </div>
      </div>
    </footer>
  )
}
