"use client"

import { motion } from "motion/react"
import { ArrowRight, Sparkles, Play } from "lucide-react"
import { SectionWrapper } from "./SectionWrapper"
import Link from "next/link"

export function PremiumCTA() {
  return (
    <SectionWrapper id="cta" bg="cta" label="Chapter 16" reveal="scale">
      <div className="max-w-4xl mx-auto text-center relative">
        {/* Background glow */}
        <motion.div
          className="absolute inset-0 bg-gradient-to-b from-[#CC3A63]/10 via-[#A2AB73]/5 to-transparent rounded-3xl blur-3xl"
          animate={{ opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: 4, repeat: Infinity }}
        />

        <div className="relative">
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#CC3A63]/10 border border-[#CC3A63]/20 text-xs font-medium text-[#CC3A63] mb-6"
          >
            <Sparkles className="h-3 w-3" />
            Your Digital Human is waiting
          </motion.div>

          {/* Heading */}
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1, duration: 0.6 }}
            className="text-4xl sm:text-5xl lg:text-6xl font-bold text-foreground mb-6 tracking-tight"
          >
            Create your
            <br />
            <motion.span
              className="bg-gradient-to-r from-[#CC3A63] via-[#A2AB73] to-[#A2AB73] bg-clip-text text-transparent inline-block"
              animate={{ backgroundPosition: ["0% 50%", "100% 50%", "0% 50%"] }}
              transition={{ duration: 6, repeat: Infinity, ease: "linear" }}
              style={{ backgroundSize: "200% 200%" }}
            >
              Digital Human
            </motion.span>
          </motion.h2>

          {/* Description */}
          <motion.p
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="text-lg text-foreground-muted max-w-2xl mx-auto mb-8 leading-relaxed"
          >
            Join thousands of creators, healthcare providers, and enterprises building the future of AI interaction.
          </motion.p>

          {/* Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3, duration: 0.5 }}
            className="flex flex-wrap justify-center gap-4"
          >
            <Link
              href="/signup"
              className="group relative inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-white font-semibold text-sm overflow-hidden transition-all hover:scale-[1.02]"
            >
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent"
                animate={{ x: ["-100%", "200%"] }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
              />
              <span className="relative z-10">Create Your Digital Human</span>
              <ArrowRight className="relative z-10 h-4 w-4 group-hover:translate-x-1 transition-transform" />
            </Link>

            <Link
              href="/login"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl border border-white/[0.08] text-foreground text-sm font-medium hover:bg-white/[0.04] hover:text-foreground transition-all"
            >
              <Play className="h-4 w-4" />
              Watch Demo
            </Link>
          </motion.div>

          {/* Trust indicators */}
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.5 }}
            className="flex flex-wrap justify-center gap-6 mt-10 text-xs text-foreground-muted"
          >
            <span>No credit card required</span>
            <span className="w-px h-4 bg-white/[0.06]" />
            <span>Free plan available</span>
            <span className="w-px h-4 bg-white/[0.06]" />
            <span>Enterprise ready</span>
            <span className="w-px h-4 bg-white/[0.06]" />
            <span>Cancel anytime</span>
          </motion.div>
        </div>
      </div>
    </SectionWrapper>
  )
}
