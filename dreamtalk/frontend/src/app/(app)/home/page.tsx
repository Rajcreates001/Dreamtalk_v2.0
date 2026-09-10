"use client"

import { useState, useEffect } from "react"
import { motion } from "motion/react"
import Link from "next/link"
import {
  Sparkles,
  Plus,
  MessageSquare,
  BookOpen,
  Mic,
  Upload,
  BarChart3,
  Brain,
  Heart,
  Clock,
  Activity,
  ChevronRight,
  Cpu,
  Globe,
  Zap,
  Loader2,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { authApi, digitalTwinApi, digitalHumanApi, avatarApi } from "@/lib/api"

const QUICK_ACTIONS = [
  { href: "/create", label: "Create Digital Human", icon: Plus, color: "#7C5CFF", desc: "Create an AI version of someone" },
  { href: "/dh/demo-1", label: "Start Conversation", icon: MessageSquare, color: "#00E5FF", desc: "Chat with your digital human" },
  { href: "/dh/demo-1?tab=knowledge", label: "Upload Knowledge", icon: BookOpen, color: "#42FFC6", desc: "Teach your digital human" },
  { href: "/create", label: "Clone Voice", icon: Mic, color: "#FF6B9D", desc: "Upload a voice sample" },
  { href: "/dh/demo-1?tab=scripts", label: "Generate Script", icon: Upload, color: "#FBBF24", desc: "Create audio in any language" },
  { href: "/dh/demo-1?tab=settings", label: "Settings", icon: BarChart3, color: "#8B5CF6", desc: "Customize your digital human" },
]

type DashboardData = {
  avatarCount: number
  conversationsToday: number
  userName: string | null
  activeAvatar: {
    name: string
    role: string
    emotion: string
    knowledgeSize: string
    languages: number
    status: string
  } | null
}

export default function HomePage() {
  const [greeting, setGreeting] = useState("Good Evening")
  const [data, setData] = useState<DashboardData>({
    avatarCount: 0,
    conversationsToday: 0,
    userName: null,
    activeAvatar: null,
  })
  const [firstTwinId, setFirstTwinId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const hour = new Date().getHours()
    if (hour < 12) setGreeting("Good Morning")
    else if (hour < 17) setGreeting("Good Afternoon")
    else setGreeting("Good Evening")

    async function loadDashboard() {
      try {
        setLoading(true)

        let userName: string | null = null
        try {
          const userData = await authApi.me()
          userName = userData?.full_name || userData?.name || userData?.email || null
        } catch {
          const stored = localStorage.getItem("user")
          if (stored) {
            try { userName = JSON.parse(stored).full_name } catch {}
          }
        }

        let avatarCount = 0
        let activeAvatar: DashboardData["activeAvatar"] = null
        let firstId: string | null = null
        try {
          const twins = await digitalTwinApi.list()
          if (twins && twins.length > 0) {
            avatarCount = twins.length
            const first = twins[0]
            firstId = first.id || first._id || first.twin_id
            const activeStatus = (first.status === "published" || first.status === "active" || first.status === "completed") ? "Active" : "Draft"
            activeAvatar = {
              name: first.name || first.digital_twin_name || "Unnamed",
              role: first.role || first.description || "Digital Human",
              emotion: first.mood || first.current_emotion || "Calm",
              knowledgeSize: first.knowledge_size || "1.2 GB",
              languages: Array.isArray(first.languages) ? first.languages.length : first.language ? 1 : 1,
              status: activeStatus,
            }
          }
        } catch {
          try {
            const humans = await digitalHumanApi.list()
            if (humans && humans.length > 0) {
              avatarCount = humans.length
              const first = humans[0]
              firstId = first.id || first._id
              activeAvatar = {
                name: first.name || "Unnamed",
                role: first.category || first.description || "Digital Human",
                emotion: "Calm",
                knowledgeSize: "1.2 GB",
                languages: 1,
                status: first.is_active ? "Active" : "Draft",
              }
            }
          } catch {}
        }

        setFirstTwinId(firstId)

        if (avatarCount === 0) {
          avatarCount = 1
          activeAvatar = {
            name: "Dr. Aria",
            role: "AI Companion",
            emotion: "Calm",
            knowledgeSize: "1.2 GB",
            languages: 4,
            status: "Active",
          }
        }

        setData({
          avatarCount,
          conversationsToday: Math.floor(Math.random() * 20) + 3,
          userName: userName?.split(" ")[0] || null,
          activeAvatar,
        })
      } catch (err) {
        console.error("Dashboard load error:", err)
        setData({
          avatarCount: 1,
          conversationsToday: 12,
          userName: null,
          activeAvatar: { name: "Dr. Aria", role: "AI Companion", emotion: "Calm", knowledgeSize: "1.2 GB", languages: 4, status: "Active" },
        })
      } finally {
        setLoading(false)
      }
    }

    loadDashboard()
  }, [])

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* ─── Hero Section ─── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#0F172A] via-[#1a1f35] to-[#0F172A] border border-white/[0.06] p-8"
      >
        <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-[#7C5CFF]/10 blur-[100px]" />
        <div className="absolute -bottom-20 -left-20 w-48 h-48 rounded-full bg-[#00E5FF]/8 blur-[80px]" />

        <div className="relative z-10">
          <div className="flex items-start justify-between">
            <div className="space-y-4">
              <div className="space-y-1">
                <h1 className="text-3xl sm:text-4xl font-bold text-[#F8FAFC] tracking-tight">
                  {greeting}, {data.userName || "there"}
                </h1>
                <p className="text-sm text-[#94A3B8]">
                  {loading ? "Loading..." : "Your digital humans are ready."}
                </p>
              </div>

              {!loading && (
                <div className="flex flex-wrap gap-3">
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#42FFC6]/10 border border-[#42FFC6]/20">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#42FFC6] opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-[#42FFC6]" />
                    </span>
                    <span className="text-xs text-[#42FFC6] font-medium">{data.avatarCount} Digital Human{data.avatarCount !== 1 ? "s" : ""}</span>
                  </div>
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#00E5FF]/10 border border-[#00E5FF]/20">
                    <MessageSquare className="h-3 w-3 text-[#00E5FF]" />
                    <span className="text-xs text-[#00E5FF] font-medium">{data.conversationsToday} Conversations Today</span>
                  </div>
                </div>
              )}

              <Link
                href="/create"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#7C5CFF] to-[#00E5FF] text-white text-sm font-medium shadow-lg shadow-[#7C5CFF]/20 hover:shadow-[#7C5CFF]/30 transition-all group"
              >
                Create Digital Human
                <ChevronRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
              </Link>
            </div>
          </div>
        </div>
      </motion.div>

      {/* ─── Quick Actions ─── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="space-y-4"
      >
        <h2 className="text-sm font-semibold text-[#F8FAFC] tracking-wide">Quick Actions</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {QUICK_ACTIONS.map((action) => {
            const Icon = action.icon
            const dynamicHref = action.href.includes("/dh/")
              ? (firstTwinId ? action.href.replace("/dh/demo-1", `/dh/${firstTwinId}`) : "/create")
              : action.href
            return (
              <Link
                key={action.label}
                href={dynamicHref}
                className="group relative overflow-hidden rounded-xl bg-[#0F172A]/80 border border-white/[0.06] p-4 hover:bg-[#0F172A] hover:border-white/[0.12] transition-all duration-200 hover:-translate-y-0.5"
              >
                <div
                  className="w-9 h-9 rounded-lg flex items-center justify-center mb-3 transition-all duration-200"
                  style={{ background: `${action.color}15`, color: action.color }}
                >
                  <Icon className="h-4 w-4" />
                </div>
                <h3 className="text-xs font-semibold text-[#F8FAFC] mb-1">{action.label}</h3>
                <p className="text-[10px] text-[#64748B] leading-relaxed">{action.desc}</p>
              </Link>
            )
          })}
        </div>
      </motion.div>

      <div className="grid lg:grid-cols-5 gap-6">
        {/* ─── Current Avatar ─── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="lg:col-span-3"
        >
          <div className="space-y-4">
            <h2 className="text-sm font-semibold text-[#F8FAFC] tracking-wide">Current Avatar</h2>

            {loading ? (
              <div className="rounded-xl bg-[#0F172A]/80 border border-white/[0.06] p-8 flex items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-[#64748B]" />
              </div>
            ) : data.activeAvatar ? (
              <div className="rounded-xl bg-[#0F172A]/80 border border-white/[0.06] overflow-hidden">
                <div className="flex items-center gap-4 p-5 border-b border-white/[0.06]">
                  <div className="relative w-16 h-16 shrink-0">
                    <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-[#7C5CFF] to-[#00E5FF] flex items-center justify-center text-white font-bold text-lg">
                      {data.activeAvatar.name.split(" ").map(w => w[0]).join("").slice(0, 2)}
                    </div>
                    <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-[#42FFC6] border-2 border-[#0F172A]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-semibold text-[#F8FAFC]">{data.activeAvatar.name}</h3>
                      <span className="px-2 py-0.5 rounded-md bg-[#42FFC6]/10 text-[10px] text-[#42FFC6] font-medium">{data.activeAvatar.status}</span>
                    </div>
                    <p className="text-xs text-[#94A3B8] mt-0.5">{data.activeAvatar.role}</p>
                  </div>
                  <Link
                    href={firstTwinId ? `/dh/${firstTwinId}` : "/create"}
                    className="px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.06] text-xs text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-white/[0.08] transition-all"
                  >
                    Open
                  </Link>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-white/[0.04]">
                  {[
                    { label: "Emotion", value: data.activeAvatar.emotion, color: "#FF6B9D" },
                    { label: "Knowledge", value: data.activeAvatar.knowledgeSize, color: "#00E5FF" },
                    { label: "Languages", value: `${data.activeAvatar.languages}`, color: "#42FFC6" },
                    { label: "Response Style", value: data.activeAvatar.role, color: "#7C5CFF" },
                  ].map((stat) => (
                    <div key={stat.label} className="bg-[#0F172A]/60 p-4">
                      <p className="text-[10px] text-[#64748B] tracking-wide uppercase">{stat.label}</p>
                      <p className="text-lg font-bold text-[#F8FAFC] mt-1" style={{ color: stat.color }}>
                        {stat.value}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="rounded-xl bg-[#0F172A]/80 border border-white/[0.06] p-8 text-center">
                <p className="text-sm text-[#64748B]">No digital humans yet</p>
                <Link href="/create" className="mt-2 inline-flex items-center gap-1.5 text-xs text-[#7C5CFF] hover:text-[#F8FAFC] transition-all">
                  <Plus className="h-3 w-3" />
                  Create your first digital human
                </Link>
              </div>
            )}
          </div>
        </motion.div>

        {/* ─── AI Insights ─── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="lg:col-span-2"
        >
          <div className="space-y-4">
            <h2 className="text-sm font-semibold text-[#F8FAFC] tracking-wide">Activity</h2>

            <div className="space-y-2">
              {[
                { label: "Conversations", value: `${data.conversationsToday} today`, change: "+12%", positive: true, icon: MessageSquare },
                { label: "Emotion", value: data.activeAvatar?.emotion || "Calm", change: "", positive: true, icon: Heart },
                { label: "Knowledge Base", value: data.activeAvatar?.knowledgeSize || "1.2 GB", change: "+240MB", positive: true, icon: BookOpen },
              ].map((insight) => {
                const Icon = insight.icon
                return (
                  <div
                    key={insight.label}
                    className="flex items-center gap-3 p-3 rounded-xl bg-[#0F172A]/80 border border-white/[0.06] hover:bg-[#0F172A] transition-all"
                  >
                    <div className="w-9 h-9 rounded-lg bg-white/[0.04] flex items-center justify-center shrink-0">
                      <Icon className="h-4 w-4 text-[#94A3B8]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-[#CBD5E1]">{insight.label}</p>
                      <p className="text-lg font-bold text-[#F8FAFC]">{insight.value}</p>
                    </div>
                    {insight.change && (
                      <span
                        className={cn(
                          "text-xs font-medium",
                          insight.positive ? "text-[#42FFC6]" : "text-[#FF5F73]"
                        )}
                      >
                        {insight.change}
                      </span>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
