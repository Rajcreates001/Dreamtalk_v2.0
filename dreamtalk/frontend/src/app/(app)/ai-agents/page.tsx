"use client"

import { motion } from "motion/react"
import {
  Bot, Network, Brain, Mic, Eye, Cpu,
  Play, Activity, MessageSquare,
} from "lucide-react"

const AGENTS = [
  { name: "Planner Agent", icon: Brain, color: "#CC3A63", status: "active", desc: "Orchestrates tasks and workflows" },
  { name: "Research Agent", icon: Network, color: "#A2AB73", status: "active", desc: "Deep research and analysis" },
  { name: "Voice Agent", icon: Mic, color: "#A2AB73", status: "active", desc: "Speech synthesis and recognition" },
  { name: "Memory Agent", icon: Cpu, color: "#CC3A63", status: "idle", desc: "Long-term memory management" },
  { name: "Knowledge Agent", icon: Brain, color: "#D6A44C", status: "active", desc: "Knowledge retrieval and indexing" },
  { name: "Vision Agent", icon: Eye, color: "#B03A5E", status: "idle", desc: "Image and video analysis" },
]

export default function AIAgentsPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-[#F3F4F4]">AI Agents</h1>
        <p className="text-sm text-[#B0A79C] mt-1">Multi-agent orchestration center</p>
      </div>

      {/* Agent grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {AGENTS.map((agent, i) => {
          const Icon = agent.icon
          return (
            <motion.div
              key={agent.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
              className="p-4 rounded-xl bg-[#2C2929]/80 border border-white/[0.06] hover:bg-[#2C2929] hover:border-white/[0.12] transition-all"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${agent.color}15` }}>
                    <Icon className="h-5 w-5" style={{ color: agent.color }} />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-[#F3F4F4]">{agent.name}</h3>
                    <p className="text-[10px] text-[#B0A79C]">{agent.desc}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 px-2 py-1 rounded-md" style={{ background: agent.status === "active" ? "#A2AB7310" : "#8A817810" }}>
                  <span className="relative flex h-2 w-2">
                    {agent.status === "active" && (
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#A2AB73] opacity-75" />
                    )}
                    <span className="relative inline-flex rounded-full h-2 w-2" style={{ background: agent.status === "active" ? "#A2AB73" : "#8A8178" }} />
                  </span>
                  <span className="text-[10px]" style={{ color: agent.status === "active" ? "#A2AB73" : "#8A8178" }}>
                    {agent.status === "active" ? "Active" : "Idle"}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 mt-4">
                <button className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-white/[0.04] border border-white/[0.06] text-xs text-[#B0A79C] hover:text-[#F3F4F4] transition-all">
                  <Activity className="h-3 w-3" />
                  View Logs
                </button>
                <button className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-white/[0.04] border border-white/[0.06] text-xs text-[#B0A79C] hover:text-[#F3F4F4] transition-all">
                  <Play className="h-3 w-3" />
                  Run
                </button>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Agent collaboration */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="p-5 rounded-xl bg-[#2C2929]/80 border border-white/[0.06]"
      >
        <div className="flex items-center gap-3 mb-4">
          <Network className="h-5 w-5 text-[#CC3A63]" />
          <div>
            <h3 className="text-sm font-semibold text-[#F3F4F4]">Agent Collaboration</h3>
            <p className="text-[10px] text-[#B0A79C]">Real-time multi-agent coordination</p>
          </div>
        </div>

        <div className="flex items-center gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/[0.06]">
          <div className="flex -space-x-2">
            {AGENTS.slice(0, 4).map((agent, i) => (
              <div key={i} className="w-7 h-7 rounded-full flex items-center justify-center text-[8px] font-bold border-2 border-[#2C2929]" style={{ background: `${agent.color}20`, color: agent.color }}>
                {agent.name.charAt(0)}
              </div>
            ))}
          </div>
          <span className="text-xs text-[#B0A79C]">4 agents collaborating on: <span className="text-[#F3F4F4]">Knowledge Sync</span></span>
          <span className="ml-auto text-[10px] text-[#A2AB73]">● Active</span>
        </div>
      </motion.div>
    </div>
  )
}
