"use client"

import { motion } from "motion/react"
import { cn } from "@/lib/utils"
import { Link2, Globe, Code2, Bot, Database, MessageSquare, FileText, CheckCircle, Plus, Sparkles } from "lucide-react"

const INTEGRATIONS = [
  { name: "Slack", desc: "Connect your AI workforce to Slack", icon: MessageSquare, color: "#4A154B", status: "connected" as const },
  { name: "GitHub", desc: "Sync knowledge from repositories", icon: Code2, color: "#F3F4F4", status: "connected" as const },
  { name: "Google Drive", desc: "Import documents from Drive", icon: Globe, color: "#4285F4", status: "available" as const },
  { name: "Notion", desc: "Sync workspaces as knowledge", icon: FileText, color: "#FFFFFF", status: "available" as const },
  { name: "WordPress", desc: "Deploy avatars on your site", icon: Globe, color: "#21759B", status: "available" as const },
  { name: "Zapier", desc: "Connect 3000+ apps", icon: Bot, color: "#FF4A00", status: "available" as const },
  { name: "HubSpot", desc: "CRM integration for sales", icon: Database, color: "#FF7A59", status: "available" as const },
  { name: "Shopify", desc: "E-commerce support avatars", icon: Globe, color: "#96BF48", status: "premium" as const },
]

const statusStyles = {
  connected: { label: "Connected", color: "#A2AB73", icon: CheckCircle },
  available: { label: "Available", color: "#8A8178", icon: Plus },
  premium: { label: "Premium", color: "#CC3A63", icon: Sparkles },
}

export default function IntegrationsPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-[#F3F4F4]">Integrations</h1>
        <p className="text-sm text-[#B0A79C] mt-1">Connect your AI workforce to your tools</p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {INTEGRATIONS.map((item, i) => {
          const Icon = item.icon
          const status = statusStyles[item.status]
          return (
            <motion.div
              key={item.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              className="p-4 rounded-xl bg-[#2C2929]/80 border border-white/[0.06] hover:bg-[#2C2929] hover:border-white/[0.12] transition-all group"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${item.color}15` }}>
                  <Icon className="h-5 w-5" style={{ color: item.color }} />
                </div>
                <button className={cn(
                  "flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium transition-all",
                  item.status === "connected"
                    ? "bg-[#A2AB73]/10 text-[#A2AB73]"
                    : "bg-white/[0.04] text-[#8A8178] hover:text-[#F3F4F4]"
                )}>
                  {item.status === "connected" ? <CheckCircle className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
                  {status.label}
                </button>
              </div>
              <h3 className="text-sm font-semibold text-[#F3F4F4]">{item.name}</h3>
              <p className="text-xs text-[#8A8178] mt-1">{item.desc}</p>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
