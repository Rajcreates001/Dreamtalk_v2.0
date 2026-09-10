"use client"

import { motion } from "motion/react"
import {
  Shield, Lock, Key, Fingerprint, Server, Cloud, Database,
  ArrowRight, CheckCircle,
} from "lucide-react"
import { SectionWrapper, SectionHeading, GlassCard } from "./SectionWrapper"
import Link from "next/link"

const features = [
  { icon: Lock, label: "End-to-End Encryption", desc: "All data encrypted at rest and in transit with AES-256", color: "#CC3A63" },
  { icon: Key, label: "Role-Based Access", desc: "Granular permissions for teams and organizations", color: "#A2AB73" },
  { icon: Fingerprint, label: "Authentication", desc: "SSO, OAuth, SAML, and MFA support", color: "#A2AB73" },
  { icon: Server, label: "Private Deployment", desc: "On-premise or VPC deployment options", color: "#D6A44C" },
  { icon: Database, label: "Data Isolation", desc: "Each Digital Twin's knowledge is isolated", color: "#D84C63" },
  { icon: Cloud, label: "SOC 2 Compliant", desc: "Enterprise-grade security controls and auditing", color: "#CC3A63" },
]

export function SecurityIntegrations() {
  return (
    <SectionWrapper id="security" bg="alt" label="Chapter 12" reveal="scale">
      <SectionHeading
        label="Security & Trust"
        title="Enterprise-grade by design"
        description="DreamTalk is built with security, privacy, and compliance at its core."
      />

      <div className="grid lg:grid-cols-2 gap-8 max-w-5xl mx-auto">
        {/* Security features */}
        <div className="space-y-3">
          {features.map((feat, i) => (
            <motion.div
              key={feat.label}
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.06 }}
              className="flex items-center gap-3 p-3 rounded-xl bg-[#2C2929]/40 border border-white/[0.04] hover:bg-white/[0.03] transition-all"
            >
              <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: `${feat.color}15` }}>
                <feat.icon className="h-4 w-4" style={{ color: feat.color }} />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-[#F3F4F4]">{feat.label}</h4>
                <p className="text-xs text-[#8A8178]">{feat.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Shield visualization */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          className="relative flex items-center justify-center"
        >
          <div className="relative w-48 h-48">
            {/* Shield rings */}
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="absolute inset-0 rounded-full border"
                style={{
                  borderColor: `${["#CC3A63", "#A2AB73", "#A2AB73"][i]}20`,
                  margin: i * 12,
                }}
                animate={{ rotate: [0, 360] }}
                transition={{ duration: 15 - i * 3, repeat: Infinity, ease: "linear" }}
              />
            ))}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[#CC3A63]/20 to-[#A2AB73]/20 border border-[#CC3A63]/30 flex items-center justify-center">
                <Shield className="h-10 w-10 text-[#CC3A63]" />
              </div>
            </div>
          </div>

          {/* Compliance badges */}
          <div className="absolute -bottom-4 flex gap-2">
            {["SOC 2", "HIPAA", "GDPR"].map((badge) => (
              <span
                key={badge}
                className="px-2 py-0.5 rounded text-[9px] font-mono bg-[#CC3A63]/10 border border-[#CC3A63]/20 text-[#CC3A63]"
              >
                {badge}
              </span>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Compliance bar */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.5 }}
        className="flex flex-wrap justify-center gap-4 mt-8"
      >
        {[
          "AES-256 Encryption",
          "SOC 2 Type II",
          "HIPAA Eligible",
          "GDPR Compliant",
          "ISO 27001",
          "Data Residency",
        ].map((item) => (
          <span
            key={item}
            className="flex items-center gap-1.5 text-xs text-[#8A8178]"
          >
            <CheckCircle className="h-3 w-3 text-[#A2AB73]" />
            {item}
          </span>
        ))}
      </motion.div>

      {/* API Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.3 }}
        className="mt-16 rounded-2xl bg-[#2C2929]/60 border border-white/[0.06] p-6 lg:p-8"
      >
        <h3 className="text-lg font-semibold text-[#F3F4F4] mb-4 text-center">APIs & Integrations</h3>
        <div className="flex flex-wrap justify-center gap-2">
          {[
            "REST API", "WebSocket", "Streaming", "Python SDK", "Node.js SDK",
            "OpenAI Compatible", "Azure", "AWS", "Google Cloud",
            "Slack", "Teams", "WhatsApp", "Discord", "FHIR",
          ].map((item) => (
            <span
              key={item}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white/[0.04] border border-white/[0.06] text-[#D8D2C8] hover:text-[#F3F4F4] hover:bg-white/[0.06] transition-all"
            >
              {item}
            </span>
          ))}
        </div>
      </motion.div>
    </SectionWrapper>
  )
}
