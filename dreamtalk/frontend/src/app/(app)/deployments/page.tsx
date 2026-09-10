"use client"

import { motion } from "motion/react"
import { Globe, CheckCircle, Clock, AlertTriangle, RefreshCw, Eye, Rocket, Cpu } from "lucide-react"

const DEPLOYMENTS = [
  { name: "Dr. Aria", env: "Production", status: "live" as const, url: "chat.dreamtalk.ai/aria", uptime: "99.97%", requests: "12.4K", color: "#42FFC6" },
  { name: "Prof. Orion", env: "Staging", status: "deploying" as const, url: "staging.dreamtalk.ai/orion", uptime: "98.2%", requests: "3.1K", color: "#7C5CFF" },
  { name: "Luna", env: "Development", status: "pending" as const, url: "dev.dreamtalk.ai/luna", uptime: "—", requests: "—", color: "#FBBF24" },
  { name: "Sage Analytics", env: "Production", status: "live" as const, url: "api.dreamtalk.ai/sage", uptime: "99.99%", requests: "87.2K", color: "#00E5FF" },
]

const STATUS_CFG = {
  live: { label: "Live", color: "#42FFC6", icon: CheckCircle },
  deploying: { label: "Deploying", color: "#FBBF24", icon: RefreshCw },
  pending: { label: "Pending", color: "#64748B", icon: Clock },
  error: { label: "Error", color: "#FF5F73", icon: AlertTriangle },
}

export default function DeploymentsPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[#F8FAFC]">Deployments</h1>
          <p className="text-sm text-[#94A3B8] mt-1">Manage your AI workforce deployment status</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-[#7C5CFF] to-[#00E5FF] text-white text-sm font-medium shadow-lg shadow-[#7C5CFF]/20">
          <Rocket className="h-4 w-4" />
          New Deployment
        </button>
      </div>

      <div className="grid gap-4">
        {DEPLOYMENTS.map((dep, i) => {
          const StatusIcon = STATUS_CFG[dep.status].icon
          return (
            <motion.div
              key={dep.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
              className="p-5 rounded-xl bg-[#0F172A]/80 border border-white/[0.06] hover:bg-[#0F172A] transition-all"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold text-sm" style={{ background: `linear-gradient(135deg, ${dep.color}, ${dep.color}80)` }}>
                    {dep.name.split(" ").map(w => w[0]).join("").slice(0, 2)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-semibold text-[#F8FAFC]">{dep.name}</h3>
                      <span className="px-2 py-0.5 rounded-md text-[10px] font-medium" style={{ background: `${STATUS_CFG[dep.status].color}15`, color: STATUS_CFG[dep.status].color }}>
                        {STATUS_CFG[dep.status].label}
                      </span>
                      <span className="px-2 py-0.5 rounded-md bg-white/[0.04] text-[10px] text-[#64748B]">{dep.env}</span>
                    </div>
                    <p className="text-xs text-[#64748B] mt-0.5">{dep.url}</p>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <p className="text-xs text-[#64748B]">Uptime</p>
                    <p className="text-sm font-semibold text-[#42FFC6]">{dep.uptime}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-[#64748B]">Requests</p>
                    <p className="text-sm font-semibold text-[#F8FAFC]">{dep.requests}</p>
                  </div>
                  <button className="px-3 py-2 rounded-lg bg-white/[0.04] border border-white/[0.06] text-xs text-[#94A3B8] hover:text-[#F8FAFC] transition-all">
                    <Eye className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Active Deployments", value: "2", icon: Globe, color: "#42FFC6" },
          { label: "Total Requests", value: "102.7K", icon: Cpu, color: "#7C5CFF" },
          { label: "Avg Uptime", value: "99.4%", icon: CheckCircle, color: "#00E5FF" },
        ].map((stat) => (
          <div key={stat.label} className="p-4 rounded-xl bg-[#0F172A]/80 border border-white/[0.06]">
            <div className="flex items-center gap-2 mb-2">
              <stat.icon className="h-4 w-4" style={{ color: stat.color }} />
              <span className="text-xs text-[#64748B]">{stat.label}</span>
            </div>
            <p className="text-xl font-bold text-[#F8FAFC]">{stat.value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
