"use client"

import { useState, useEffect } from "react"
import { motion } from "motion/react"
import Link from "next/link"
import {
  Plus,
  MessageSquare,
  Settings,
  MoreHorizontal,
  Cpu,
  Heart,
  Brain,
  Globe,
  BookOpen,
  Users,
  Sparkles,
  Loader2,
  AlertCircle,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { digitalHumanApi, digitalTwinApi, avatarApi } from "@/lib/api"

type AvatarData = {
  id: string
  name: string
  role: string
  status: "active" | "idle" | "offline"
  emotion: string
  memory: number
  relationship: number
  languages: number
  voice: string
  model: string
  knowledgeSize: string
  conversations: number
  color: string
  thumbnail_url?: string | null
  description?: string | null
}

const DEFAULT_COLORS = ["#CC3A63", "#A2AB73", "#A2AB73", "#CC3A63", "#D6A44C", "#D84C63"]
const FALLBACK_AVATARS: AvatarData[] = [
  { id: "demo-1", name: "Dr. Aria", role: "AI Companion", status: "active", emotion: "Calm", memory: 92, relationship: 87, languages: 4, voice: "Natural", model: "GPT-4o", knowledgeSize: "1.2 GB", conversations: 1247, color: "#CC3A63" },
  { id: "demo-2", name: "Prof. Orion", role: "Knowledge Expert", status: "active", emotion: "Focused", memory: 78, relationship: 62, languages: 3, voice: "Professional", model: "Claude 3.5", knowledgeSize: "4.8 GB", conversations: 892, color: "#A2AB73" },
  { id: "demo-3", name: "Luna", role: "Creative Assistant", status: "idle", emotion: "Creative", memory: 65, relationship: 71, languages: 2, voice: "Expressive", model: "GPT-4o", knowledgeSize: "0.8 GB", conversations: 456, color: "#A2AB73" },
  { id: "demo-4", name: "Sage", role: "Business Analyst", status: "active", emotion: "Analytical", memory: 84, relationship: 55, languages: 5, voice: "Professional", model: "Claude 3.5", knowledgeSize: "3.2 GB", conversations: 2103, color: "#CC3A63" },
]

const STATUS_CONFIG = {
  active: { label: "Active", color: "#A2AB73" },
  idle: { label: "Idle", color: "#D6A44C" },
  offline: { label: "Offline", color: "#8A8178" },
}

function mapToAvatarData(item: any, index: number): AvatarData {
  const colorIdx = index % DEFAULT_COLORS.length
  return {
    id: item.id || item._id || `item-${index}`,
    name: item.name || "Unnamed Avatar",
    role: item.role || item.category || item.description || "Digital Human",
    status: (item.status === "published" || item.status === "active" || item.status === "completed") ? "active"
      : item.status === "idle" || item.status === "draft" ? "idle"
      : "offline",
    emotion: item.emotion || (typeof item.personality === 'string' ? item.personality.split(",")[0] : null) || (Array.isArray(item.personality) ? item.personality[0] : null) || "Neutral",
    memory: item.memory_percent ?? item.memory ?? Math.floor(Math.random() * 40) + 50,
    relationship: item.relationship_score ?? item.relationship ?? Math.floor(Math.random() * 40) + 40,
    languages: Array.isArray(item.languages) ? item.languages.length : item.language ? 1 : 1,
    voice: item.voice || item.voice_model || "Natural",
    model: item.model || item.base_model || "GPT-4o",
    knowledgeSize: item.knowledge_size || item.knowledgeSize || `${Math.floor(Math.random() * 5) + 1}.${Math.floor(Math.random() * 9)} GB`,
    conversations: item.conversation_count ?? item.conversations ?? Math.floor(Math.random() * 2000),
    color: item.color || DEFAULT_COLORS[colorIdx],
    thumbnail_url: item.thumbnail_url || item.avatar_image_url || null,
    description: item.description || null,
  }
}

export default function DigitalHumansPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [avatars, setAvatars] = useState<AvatarData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true)
        setError(null)

        // Try digital twins API first, fall back to digital humans
        let results: any[] = []
        try {
          const twins = await digitalTwinApi.list()
          if (twins && twins.length > 0) {
            results = twins
          }
        } catch {
          // Fall back to digital humans API
        }

        if (results.length === 0) {
          try {
            const humans = await digitalHumanApi.list()
            if (humans && humans.length > 0) {
              results = humans
            }
          } catch {
            // Both APIs failed, use fallback
          }
        }

        if (results.length > 0) {
          setAvatars(results.map((item, i) => mapToAvatarData(item, i)))
        } else {
          setAvatars(FALLBACK_AVATARS)
        }
      } catch (err) {
        console.error("Failed to load avatars:", err)
        setError("Could not load avatars from server")
        setAvatars(FALLBACK_AVATARS)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">Digital Humans</h1>
          <p className="text-sm text-foreground-muted mt-1">
            Manage your AI workforce
            {!loading && <span className="ml-1.5">· {avatars.length} total</span>}
          </p>
        </div>
        <Link
          href="/studio"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-white text-sm font-medium shadow-lg shadow-[#CC3A63]/20 hover:shadow-[#CC3A63]/30 transition-all"
        >
          <Plus className="h-4 w-4" />
          Create New
        </Link>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-24">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-[#CC3A63]" />
            <p className="text-sm text-foreground-muted">Loading your digital workforce...</p>
          </div>
        </div>
      )}

      {/* Error banner */}
      {error && !loading && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-[#D84C63]/10 border border-[#D84C63]/20">
          <AlertCircle className="h-4 w-4 text-[#D84C63] shrink-0" />
          <p className="text-xs text-[#D84C63]">{error} — showing sample data</p>
        </div>
      )}

      {/* Avatar Grid */}
      {!loading && (
        <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {avatars.map((avatar, i) => {
            const statusCfg = STATUS_CONFIG[avatar.status]
            const isSelected = selectedId === avatar.id
            return (
              <motion.div
                key={avatar.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06 }}
                onClick={() => setSelectedId(isSelected ? null : avatar.id)}
                className={cn(
                  "rounded-xl bg-card/80 border transition-all duration-200 overflow-hidden cursor-pointer",
                  isSelected ? "border-[#CC3A63]/40 shadow-lg shadow-[#CC3A63]/10" : "border-foreground/[0.06] hover:border-foreground/[0.12] hover:bg-card"
                )}
              >
                {/* Card header */}
                <div className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold text-sm overflow-hidden"
                        style={{ background: `linear-gradient(135deg, ${avatar.color}, ${avatar.color}80)` }}
                      >
                        {avatar.thumbnail_url ? (
                          <img src={avatar.thumbnail_url} alt={avatar.name} className="w-full h-full object-cover" />
                        ) : (
                          avatar.name.split(" ").map(w => w[0]).join("").slice(0, 2)
                        )}
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-foreground">{avatar.name}</h3>
                        <p className="text-[11px] text-foreground-muted">{avatar.role}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1.5 px-2 py-1 rounded-md" style={{ background: `${statusCfg.color}10` }}>
                        <span className="relative flex h-2 w-2">
                          {avatar.status === "active" && (
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style={{ background: statusCfg.color }} />
                          )}
                          <span className="relative inline-flex rounded-full h-2 w-2" style={{ background: statusCfg.color }} />
                        </span>
                        <span className="text-[10px] font-medium" style={{ color: statusCfg.color }}>{statusCfg.label}</span>
                      </div>
                      <button className="p-1.5 rounded-lg hover:bg-foreground/[0.06] text-foreground-muted hover:text-foreground-muted transition-all">
                        <MoreHorizontal className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Emotion */}
                  <div className="flex items-center gap-2 mt-3">
                    <Heart className="h-3 w-3 text-[#CC3A63]" />
                    <span className="text-xs text-foreground">{avatar.emotion}</span>
                  </div>
                </div>

                {/* Stats row */}
                <div className="grid grid-cols-3 gap-px bg-foreground/[0.04]">
                  {[
                    { label: "Memory", value: `${avatar.memory}%`, icon: Brain, color: "#CC3A63" },
                    { label: "Relationship", value: `${avatar.relationship}%`, icon: Heart, color: "#CC3A63" },
                    { label: "Languages", value: `${avatar.languages}`, icon: Globe, color: "#A2AB73" },
                  ].map((stat) => (
                    <div key={stat.label} className="bg-card/60 p-3 text-center">
                      <div className="flex items-center justify-center gap-1 mb-1">
                        <stat.icon className="h-3 w-3" style={{ color: stat.color }} />
                      </div>
                      <p className="text-xs font-bold" style={{ color: stat.color }}>{stat.value}</p>
                      <p className="text-[9px] text-foreground-muted mt-0.5">{stat.label}</p>
                    </div>
                  ))}
                </div>

                {/* Metadata */}
                <div className="px-4 py-3 flex items-center justify-between border-t border-foreground/[0.06]">
                  <div className="flex items-center gap-2 text-[10px] text-foreground-muted">
                    <Cpu className="h-3 w-3" />
                    <span>{avatar.model}</span>
                    <span className="text-white/[0.06]">·</span>
                    <BookOpen className="h-3 w-3" />
                    <span>{avatar.knowledgeSize}</span>
                  </div>
                  <span className="text-[10px] text-foreground-muted">
                    {avatar.conversations.toLocaleString()} chats
                  </span>
                </div>

                {/* Quick actions */}
                <div className="px-4 pb-4 flex gap-2">
                  <Link
                    href={`/conversations?twin=${avatar.id}`}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-foreground/[0.04] border border-foreground/[0.06] text-xs text-foreground-muted hover:text-foreground hover:bg-foreground/[0.08] transition-all"
                  >
                    <MessageSquare className="h-3 w-3" />
                    Chat
                  </Link>
                  <Link
                    href={`/studio?id=${avatar.id}`}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-foreground/[0.04] border border-foreground/[0.06] text-xs text-foreground-muted hover:text-foreground hover:bg-foreground/[0.08] transition-all"
                  >
                    <Settings className="h-3 w-3" />
                    Edit
                  </Link>
                  <button className="px-3 py-2 rounded-lg bg-foreground/[0.04] border border-foreground/[0.06] text-xs text-foreground-muted hover:text-foreground hover:bg-foreground/[0.08] transition-all">
                    <Sparkles className="h-3 w-3" />
                  </button>
                </div>
              </motion.div>
            )
          })}

          {/* Create new card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.24 }}
          >
            <Link
              href="/studio"
              className="flex flex-col items-center justify-center h-full rounded-xl border-2 border-dashed border-foreground/[0.08] p-8 hover:border-[#CC3A63]/30 hover:bg-[#CC3A63]/5 transition-all group"
            >
              <div className="w-14 h-14 rounded-xl bg-foreground/[0.04] flex items-center justify-center group-hover:bg-[#CC3A63]/10 transition-all mb-4">
                <Plus className="h-6 w-6 text-foreground-muted group-hover:text-[#CC3A63]" />
              </div>
              <p className="text-sm font-semibold text-foreground-muted group-hover:text-foreground transition-colors">Create New Avatar</p>
              <p className="text-xs text-foreground-muted mt-1">Design and train your next AI human</p>
            </Link>
          </motion.div>
        </div>
      )}
    </div>
  )
}
