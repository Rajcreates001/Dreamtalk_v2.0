"use client"

import { motion } from "motion/react"
import { Globe, Smartphone, Monitor, Cloud, Radio, Bot, Shield, ArrowRight } from "lucide-react"
import { SectionWrapper, SectionHeading } from "./SectionWrapper"
import Link from "next/link"

const platforms = [
  { icon: Monitor, label: "Web", desc: "Embed in any website", color: "#CC3A63" },
  { icon: Smartphone, label: "Mobile", desc: "iOS & Android apps", color: "#A2AB73" },
  { icon: Bot, label: "API", desc: "REST, WebSocket, gRPC", color: "#A2AB73" },
  { icon: Cloud, label: "Cloud", desc: "Scalable infrastructure", color: "#D6A44C" },
  { icon: Radio, label: "Kiosk", desc: "Physical deployments", color: "#D84C63" },
  { icon: Shield, label: "On-premise", desc: "Private deployment", color: "#CC3A63" },
]

export function DeploymentNetwork() {
  return (
    <SectionWrapper id="deployment" bg="deploy" label="Chapter 10" reveal="slide">
      <SectionHeading
        label="Deployment"
        title="Deploy anywhere, scale infinitely"
        description="DreamTalk Digital Humans work everywhere — web, mobile, cloud, kiosks, and enterprise infrastructure."
      />

      {/* Globe visualization */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true }}
        className="relative flex items-center justify-center py-16 mb-12"
      >
        {/* Network rings */}
        {[0, 1, 2, 3].map((i) => (
          <motion.div
            key={i}
            className="absolute rounded-full border border-[#CC3A63]/10"
            style={{
              width: 120 + i * 80,
              height: 120 + i * 80,
            }}
            animate={{ rotate: 360 }}
            transition={{
              duration: 20 + i * 10,
              repeat: Infinity,
              ease: "linear",
            }}
          />
        ))}

        {/* Central node */}
        <motion.div
          className="relative z-10 w-20 h-20 rounded-full bg-gradient-to-br from-[#CC3A63] to-[#A2AB73] p-[2px]"
          animate={{ boxShadow: ["0 0 30px rgba(204,58,99,0.3)", "0 0 50px rgba(204,58,99,0.5)", "0 0 30px rgba(204,58,99,0.3)"] }}
          transition={{ duration: 3, repeat: Infinity }}
        >
          <div className="w-full h-full rounded-full bg-background flex items-center justify-center">
            <Globe className="h-8 w-8 text-[#CC3A63]" />
          </div>
        </motion.div>

        {/* Connection dots */}
        {[
          { x: "25%", y: "30%", color: "#A2AB73" },
          { x: "75%", y: "25%", color: "#A2AB73" },
          { x: "80%", y: "70%", color: "#D6A44C" },
          { x: "20%", y: "75%", color: "#D84C63" },
          { x: "50%", y: "15%", color: "#CC3A63" },
          { x: "50%", y: "85%", color: "#A2AB73" },
        ].map((dot, i) => (
          <motion.div
            key={i}
            className="absolute w-3 h-3 rounded-full"
            style={{
              left: dot.x,
              top: dot.y,
              background: dot.color,
              boxShadow: `0 0 12px ${dot.color}50`,
            }}
            animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 2, delay: i * 0.3, repeat: Infinity }}
          />
        ))}

        {/* Data flow lines */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ opacity: 0.1 }}>
          {[
            [200, 150, 100, 80],
            [200, 150, 300, 70],
            [200, 150, 320, 180],
            [200, 150, 80, 190],
            [200, 150, 200, 40],
            [200, 150, 200, 260],
          ].map(([x1, y1, x2, y2], i) => (
            <motion.line
              key={i}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke={["#CC3A63", "#A2AB73", "#A2AB73", "#D6A44C", "#D84C63", "#A2AB73"][i]}
              strokeWidth="1"
              strokeDasharray="4 4"
              initial={{ pathLength: 0 }}
              whileInView={{ pathLength: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 2, delay: i * 0.2 }}
            />
          ))}
        </svg>
      </motion.div>

      {/* Platform cards */}
      <div className="grid sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {platforms.map((platform, i) => (
          <motion.div
            key={platform.label}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 + i * 0.06 }}
            className="rounded-xl bg-card/60 border border-foreground/[0.06] p-4 text-center hover:bg-foreground/[0.03] transition-all group"
            whileHover={{ y: -4 }}
          >
            <div
              className="w-10 h-10 rounded-xl mx-auto mb-3 flex items-center justify-center transition-transform group-hover:scale-110"
              style={{ background: `${platform.color}15` }}
            >
              <platform.icon className="h-5 w-5" style={{ color: platform.color }} />
            </div>
            <h4 className="text-sm font-semibold text-foreground mb-0.5">{platform.label}</h4>
            <p className="text-[10px] text-foreground-muted">{platform.desc}</p>
          </motion.div>
        ))}
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ delay: 0.6 }}
        className="text-center mt-8"
      >
        <Link
          href="/signup"
          className="inline-flex items-center gap-2 text-sm text-[#CC3A63] hover:text-[#A2AB73] transition-colors"
        >
          Explore deployment options <ArrowRight className="h-4 w-4" />
        </Link>
      </motion.div>
    </SectionWrapper>
  )
}
