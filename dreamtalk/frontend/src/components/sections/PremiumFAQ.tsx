"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "motion/react"
import { ChevronRight, Search, Sparkles } from "lucide-react"
import { SectionWrapper, SectionHeading } from "./SectionWrapper"

const faqs = [
  { q: "What is DreamTalk?", a: "DreamTalk is an AI Avatar Platform — The Operating System for Digital Humans. Create, train, deploy, and manage intelligent digital humans with voice, emotion, memory, and knowledge capabilities." },
  { q: "How much does DreamTalk cost?", a: "We offer Free, Pro (₹2,499/mo), and Business (₹8,499/mo) plans. Enterprise pricing available on request. All plans include core features with scaling limits." },
  { q: "Can I create avatars for healthcare?", a: "Yes! DreamTalk supports HIPAA-compliant avatars for healthcare with medical knowledge upload, patient context, and secure data handling." },
  { q: "What platforms can I deploy to?", a: "DreamTalk avatars can be deployed to websites, mobile apps, WhatsApp, Discord, Slack, Microsoft Teams, kiosks, and via our API/SDK." },
  { q: "Does DreamTalk support multiple languages?", a: "Yes, our avatars support 50+ languages with natural accents, emotion detection, and real-time translation capabilities." },
  { q: "How does the knowledge base work?", a: "Upload PDFs, documents, websites, YouTube links, audio files, or images. DreamTalk processes them into a knowledge graph that your avatar can query in real-time." },
  { q: "Can I customize my avatar's appearance?", a: "Absolutely. Choose gender, age, face shape, hair, skin tone, clothing, voice, accent, personality traits, and more in our Avatar Studio." },
  { q: "Do avatars have memory?", a: "Yes, every avatar has persistent memory — working, episodic, semantic, and procedural. They remember past conversations and learned information." },
  { q: "Is my data secure?", a: "All data is encrypted at rest and in transit. We offer role-based access control, private knowledge isolation, audit logging, and SOC-ready architecture." },
  { q: "Can I try before buying?", a: "Yes! The Free plan includes 5 avatars, basic voice, and 10 min/interaction. No credit card required to get started." },
]

export function PremiumFAQ() {
  const [open, setOpen] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")

  const filtered = faqs.filter(
    (faq) =>
      faq.q.toLowerCase().includes(searchQuery.toLowerCase()) ||
      faq.a.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <SectionWrapper id="faq" bg="alt" label="Chapter 15" reveal="slide">
      <SectionHeading
        label="FAQ"
        title="Frequently asked questions"
        description="Everything you need to know about DreamTalk."
      />

      <div className="max-w-3xl mx-auto">
        {/* Search */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="relative mb-8"
        >
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-foreground-muted" />
          <input
            name="faq-search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search questions..."
            className="w-full bg-card/60 border border-foreground/[0.06] rounded-xl pl-11 pr-4 py-3 text-sm text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-[#CC3A63]/30 focus:border-[#CC3A63]/50 transition-all"
          />
        </motion.div>

        {/* FAQ items */}
        <div className="space-y-2">
          <AnimatePresence>
            {filtered.map((faq) => (
              <motion.div
                key={faq.q}
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10, height: 0 }}
                transition={{ duration: 0.2 }}
                className="rounded-xl bg-card/60 border border-foreground/[0.05] overflow-hidden"
              >
                <button
                  onClick={() => setOpen(open === faq.q ? null : faq.q)}
                  className="w-full flex items-center justify-between p-4 text-left text-sm font-medium text-foreground hover:text-foreground transition-colors"
                >
                  <span>{faq.q}</span>
                  <motion.div
                    animate={{ rotate: open === faq.q ? 90 : 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <ChevronRight className="h-4 w-4 text-foreground-muted" />
                  </motion.div>
                </button>
                <AnimatePresence>
                  {open === faq.q && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3, ease: "easeInOut" }}
                      className="overflow-hidden"
                    >
                      <p className="px-4 pb-4 text-sm text-foreground-muted leading-relaxed">{faq.a}</p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        {filtered.length === 0 && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center text-sm text-foreground-muted py-8"
          >
            No questions found for &ldquo;{searchQuery}&rdquo;
          </motion.p>
        )}
      </div>
    </SectionWrapper>
  )
}
