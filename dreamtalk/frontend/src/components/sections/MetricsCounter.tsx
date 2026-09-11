"use client"

import { motion } from "motion/react"
import { SectionWrapper } from "./SectionWrapper"

const metrics = [
  { value: "50K+", label: "Avatars Created", desc: "Digital Humans brought to life", color: "#CC3A63" },
  { value: "10M+", label: "Conversations", desc: "Intelligent interactions served", color: "#A2AB73" },
  { value: "50+", label: "Languages", desc: "Multilingual voice & text", color: "#A2AB73" },
  { value: "<200ms", label: "Response Time", desc: "Real-time intelligence", color: "#D6A44C" },
  { value: "99.9%", label: "Uptime", desc: "Enterprise reliability", color: "#D84C63" },
  { value: "94%", label: "Satisfaction", desc: "User happiness score", color: "#CC3A63" },
]

export function MetricsCounter() {
  return (
    <SectionWrapper id="metrics" bg="aurora" label="Chapter 13" reveal="slide">
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {metrics.map((metric, i) => (
          <motion.div
            key={metric.label}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.06 }}
            className="relative text-center p-6 rounded-2xl bg-card/60 border border-foreground/[0.06] hover:bg-foreground/[0.03] transition-all group"
          >
            {/* Decorative line */}
            <motion.div
              className="absolute top-0 left-8 right-8 h-px"
              style={{ background: `linear-gradient(90deg, transparent, ${metric.color}, transparent)` }}
              initial={{ scaleX: 0, opacity: 0 }}
              whileInView={{ scaleX: 1, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 + i * 0.06 }}
            />
            <motion.div
              className="text-3xl lg:text-4xl font-bold mb-1 font-mono"
              style={{ color: metric.color }}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 + i * 0.06, type: "spring" }}
            >
              <motion.span
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: 0.3 + i * 0.06 }}
              >
                {metric.value}
              </motion.span>
            </motion.div>
            <h4 className="text-sm font-semibold text-foreground mb-0.5">{metric.label}</h4>
            <p className="text-[11px] text-foreground-muted">{metric.desc}</p>
          </motion.div>
        ))}
      </div>
    </SectionWrapper>
  )
}
