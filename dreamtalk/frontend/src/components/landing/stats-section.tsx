"use client"

import { motion } from "motion/react"
import { BlurFade } from "@/components/magic/blur-fade"
import { NumberTicker } from "@/components/magic/number-ticker"

const stats = [
  { value: 12, suffix: "+", label: "Integrated AI Systems", desc: "Voice, vision, cognition & memory" },
  { value: 3000, suffix: "+", label: "Python Source Files", desc: "Across face, avatar & brain modules" },
  { value: 24, suffix: "/7", label: "Always Available", desc: "Low-latency cloud inference" },
  { value: 10, suffix: "ms", label: "Voice Latency", desc: "Real-time speech processing" },
]

export function StatsSection() {
  return (
    <section className="relative w-full py-20 px-6 lg:px-16 xl:px-24 bg-background overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-emerald-500/[0.02] to-background pointer-events-none" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[1px] bg-gradient-to-r from-transparent via-emerald-500/30 to-transparent" />

      <div className="relative max-w-7xl mx-auto">
        <BlurFade inView offset={10} blur="4px">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
            {stats.map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1, duration: 0.5 }}
                className="text-center space-y-2"
              >
                <div className="text-3xl sm:text-4xl lg:text-5xl font-bold text-emerald-400">
                  <NumberTicker value={stat.value} />
                  <span>{stat.suffix}</span>
                </div>
                <h3 className="font-semibold text-foreground">{stat.label}</h3>
                <p className="text-sm text-muted-foreground">{stat.desc}</p>
              </motion.div>
            ))}
          </div>
        </BlurFade>
      </div>
    </section>
  )
}
