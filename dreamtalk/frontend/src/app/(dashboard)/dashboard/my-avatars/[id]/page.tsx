"use client"

import { useState, useEffect } from "react"
import { useRouter, useParams } from "next/navigation"
import { motion } from "motion/react"
import { cn } from "@/lib/utils"
import {
  Bot,
  ArrowLeft,
  MessageSquare,
  Sparkles,
  Settings,
  Trash2,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Globe,
  Image as ImageIcon,
  Mic,
  Heart,
  Clock,
  User,
  Zap,
  BookOpen,
  Activity,
} from "lucide-react"
import { digitalTwinApi, authApi, getAccessToken, API_BASE_URL } from "@/lib/api"
import { AvatarViewer3D } from "@/components/avatar/avatar-viewer-3d"
import Link from "next/link"

type UserData = {
  id: string
  email: string
  full_name: string
  role: string
  avatar_url?: string | null
  created_at?: string
}

type DigitalTwin = {
  id: string
  name: string
  description?: string
  status: string
  role: string
  category?: string
  language?: string
  languages?: string[]
  greeting?: string
  nickname?: string
  avatar_image_url?: string | null
  voice_sample_url?: string | null
  cloned_voice_id?: string | null
  relationship_type?: string
  personality_data?: Record<string, number>
  appearance_data?: {
    face_detected?: boolean
    landmarks_count?: number
    quality_score?: number
    head_pose?: Record<string, number>
    mesh_url?: string | null
    reconstructed_3d_mesh_url?: string | null
  }
  voice_data?: {
    accent?: string
    speaking_style?: string
    speech_rate?: number
    clone_status?: string
  }
  created_at?: string
  updated_at?: string
}

const STATUS_STYLES: Record<string, { bg: string; text: string; dot: string; label: string }> = {
  completed: { bg: "bg-[#42FFC6]/10", text: "text-[#42FFC6]", dot: "bg-[#42FFC6]", label: "Live" },
  processing: { bg: "bg-[#FFB84D]/10", text: "text-[#FFB84D]", dot: "bg-[#FFB84D]", label: "Processing" },
  draft: { bg: "bg-[#94A3B8]/10", text: "text-[#94A3B8]", dot: "bg-[#94A3B8]", label: "Draft" },
  published: { bg: "bg-[#42FFC6]/10", text: "text-[#42FFC6]", dot: "bg-[#42FFC6]", label: "Published" },
  failed: { bg: "bg-[#FF5F73]/10", text: "text-[#FF5F73]", dot: "bg-[#FF5F73]", label: "Failed" },
  default: { bg: "bg-[#94A3B8]/10", text: "text-[#94A3B8]", dot: "bg-[#94A3B8]", label: "Unknown" },
}

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_STYLES[status?.toLowerCase()] || STATUS_STYLES.default
  return (
    <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium", s.bg, s.text)}>
      <span className={cn("w-1.5 h-1.5 rounded-full", s.dot)} />
      {s.label}
    </span>
  )
}

function TraitBar({ label, value, color = "#7C5CFF" }: { label: string; value: number; color?: string }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-[#94A3B8] capitalize">{label.replace(/_/g, " ")}</span>
        <span className="text-[10px] text-[#64748B]">{Math.round(value * 100)}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value * 100}%` }}
          transition={{ duration: 1, delay: 0.2 }}
          className="h-full rounded-full"
          style={{ background: `linear-gradient(90deg, ${color}, ${color}88)` }}
        />
      </div>
    </div>
  )
}

function StepIndicator({ label, completed }: { label: string; completed: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className={cn(
          "w-7 h-7 rounded-full flex items-center justify-center shrink-0 transition-all",
          completed
            ? "bg-[#42FFC6]/20 text-[#42FFC6]"
            : "bg-white/[0.04] text-[#64748B]"
        )}
      >
        {completed ? (
          <CheckCircle2 className="h-3.5 w-3.5" />
        ) : (
          <div className="h-2 w-2 rounded-full bg-[#64748B]/50" />
        )}
      </div>
      <span className={cn("text-xs", completed ? "text-[#CBD5E1] font-medium" : "text-[#64748B]")}>
        {label}
      </span>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      <div className="h-8 w-32 bg-white/[0.04] rounded-lg animate-pulse" />
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="h-[400px] rounded-2xl bg-white/[0.04] animate-pulse" />
        <div className="space-y-4">
          <div className="h-8 w-48 bg-white/[0.04] rounded-lg animate-pulse" />
          <div className="h-4 w-64 bg-white/[0.04] rounded-lg animate-pulse" />
          <div className="h-32 rounded-2xl bg-white/[0.04] animate-pulse" />
        </div>
      </div>
    </div>
  )
}

export default function DigitalTwinDetailPage() {
  const router = useRouter()
  const params = useParams()
  const twinId = params?.id as string

  const [twin, setTwin] = useState<DigitalTwin | null>(null)
  const [user, setUser] = useState<UserData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [publishing, setPublishing] = useState(false)

  useEffect(() => {
    if (!getAccessToken()) {
      router.push("/login")
      return
    }
    if (!twinId) return

    async function loadData() {
      try {
        setLoading(true)
        setError(null)

        const [userData, twinData] = await Promise.all([
          authApi.me().catch(() => {
            const stored = localStorage.getItem("user")
            return stored ? JSON.parse(stored) : null
          }),
          digitalTwinApi.get(twinId),
        ])

        if (userData) setUser(userData)
        setTwin(twinData)
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to load avatar"
        setError(message)
        console.error("Detail page load error:", err)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [twinId, router])

  const handlePublish = async () => {
    if (!twin) return
    try {
      setPublishing(true)
      const updated = await digitalTwinApi.publish(twin.id)
      setTwin({ ...twin, status: "published", ...updated })
    } catch (err) {
      console.error("Publish error:", err)
      setError("Failed to publish avatar. Please ensure all steps are complete.")
    } finally {
      setPublishing(false)
    }
  }

  const handleChat = () => {
    router.push(`/conversations?twin=${twinId}`)
  }

  if (loading) return <LoadingSkeleton />

  if (error || !twin) {
    return (
      <div className="max-w-6xl mx-auto py-24 flex flex-col items-center gap-4">
        <AlertCircle className="h-12 w-12 text-red-400" />
        <h2 className="text-lg font-semibold text-[#F8FAFC]">Avatar Not Found</h2>
        <p className="text-sm text-[#64748B]">{error || "This avatar does not exist or has been removed."}</p>
        <button
          onClick={() => router.push("/dashboard/my-avatars")}
          className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#7C5CFF] to-[#00E5FF] text-white text-sm font-medium mt-2"
        >
          Back to My Avatars
        </button>
      </div>
    )
  }

  const langs = twin.languages || (twin.language ? [twin.language] : ["en"])
  const personality = twin.personality_data
  const appearance = twin.appearance_data
  const voice = twin.voice_data
  const createdDate = twin.created_at
    ? new Date(twin.created_at).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })
    : "—"
  const isDraft = twin.status === "draft"
  const isPublished = twin.status === "published" || twin.status === "completed"
  // Use 3D mesh URL from the appearance data (static files served under /api/static/)
  const meshUrl = appearance?.reconstructed_3d_mesh_url 
    ? `${API_BASE_URL}${appearance.reconstructed_3d_mesh_url}`
    : null

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      {/* Back navigation */}
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
      >
        <Link
          href="/dashboard/my-avatars"
          className="inline-flex items-center gap-1.5 text-xs text-[#94A3B8] hover:text-[#F8FAFC] transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to My Avatars
        </Link>
      </motion.div>

      <div className="grid lg:grid-cols-5 gap-6">
        {/* Left column - 3D Viewer */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="lg:col-span-3 space-y-4"
        >
          {/* 3D Avatar Viewer */}
          <AvatarViewer3D
            modelUrl={meshUrl}
            height={500}
            autoRotate={!isDraft}
            autoRotateSpeed={2.0}
            showControls={true}
            fallbackType="head"
            className="w-full"
          />

          {/* Quick stats row */}
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-xl bg-[#0F172A]/80 backdrop-blur-2xl border border-white/[0.06] p-3 text-center">
              <p className="text-[10px] text-[#64748B] mb-1">Face Quality</p>
              <p className="text-sm font-bold text-[#F8FAFC]">
                {appearance?.quality_score ? `${(appearance.quality_score * 100).toFixed(0)}%` : "—"}
              </p>
            </div>
            <div className="rounded-xl bg-[#0F172A]/80 backdrop-blur-2xl border border-white/[0.06] p-3 text-center">
              <p className="text-[10px] text-[#64748B] mb-1">Landmarks</p>
              <p className="text-sm font-bold text-[#F8FAFC]">
                {appearance?.landmarks_count || "—"}
              </p>
            </div>
            <div className="rounded-xl bg-[#0F172A]/80 backdrop-blur-2xl border border-white/[0.06] p-3 text-center">
              <p className="text-[10px] text-[#64748B] mb-1">Status</p>
              <p className="text-sm font-bold text-[#F8FAFC] capitalize">
                {twin.status}
              </p>
            </div>
          </div>
        </motion.div>

        {/* Right column - Details */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="lg:col-span-2 space-y-4"
        >
          {/* Header card */}
          <div className="bg-[#0F172A]/80 backdrop-blur-2xl border border-white/[0.06] rounded-[20px] p-5 space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className={cn(
                  "w-12 h-12 rounded-xl flex items-center justify-center",
                  isPublished
                    ? "bg-gradient-to-br from-[#42FFC6]/20 to-[#00E5FF]/10"
                    : "bg-gradient-to-br from-[#7C5CFF]/20 to-[#00E5FF]/10"
                )}>
                  <Bot className={cn("h-6 w-6", isPublished ? "text-[#42FFC6]" : "text-[#7C5CFF]")} />
                </div>
                <div>
                  <h1 className="text-lg font-bold text-[#F8FAFC]">{twin.name}</h1>
                  {twin.nickname && (
                    <p className="text-[11px] text-[#64748B]">aka &ldquo;{twin.nickname}&rdquo;</p>
                  )}
                </div>
              </div>
              <StatusBadge status={twin.status} />
            </div>

            {twin.description && (
              <p className="text-sm text-[#94A3B8] leading-relaxed">{twin.description}</p>
            )}

            {twin.greeting && (
              <div className="rounded-xl bg-white/[0.04] border border-white/[0.06] p-3">
                <p className="text-[10px] text-[#64748B] mb-1">Greeting</p>
                <p className="text-sm text-[#CBD5E1] italic">&ldquo;{twin.greeting}&rdquo;</p>
              </div>
            )}
          </div>

          {/* Meta card */}
          <div className="bg-[#0F172A]/80 backdrop-blur-2xl border border-white/[0.06] rounded-[20px] p-5 space-y-3">
            <h2 className="text-xs font-semibold text-[#94A3B8] uppercase tracking-wider">Details</h2>

            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <User className="h-3.5 w-3.5 text-[#64748B]" />
                  <span className="text-xs text-[#94A3B8]">Role</span>
                </div>
                <span className="text-xs text-[#CBD5E1] capitalize">{twin.role}</span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Globe className="h-3.5 w-3.5 text-[#64748B]" />
                  <span className="text-xs text-[#94A3B8]">Languages</span>
                </div>
                <div className="flex gap-1">
                  {langs.map((lang) => (
                    <span key={lang} className="px-1.5 py-0.5 rounded-md bg-white/[0.04] text-[10px] text-[#94A3B8] uppercase">
                      {lang === "en" ? "EN" : lang === "ta" ? "TA" : lang === "hi" ? "HI" : lang.slice(0, 2).toUpperCase()}
                    </span>
                  ))}
                </div>
              </div>

              {twin.relationship_type && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Heart className="h-3.5 w-3.5 text-[#64748B]" />
                    <span className="text-xs text-[#94A3B8]">Relationship</span>
                  </div>
                  <span className="text-xs text-[#CBD5E1] capitalize">{twin.relationship_type.replace(/_/g, " ")}</span>
                </div>
              )}

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock className="h-3.5 w-3.5 text-[#64748B]" />
                  <span className="text-xs text-[#94A3B8]">Created</span>
                </div>
                <span className="text-xs text-[#CBD5E1]">{createdDate}</span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ImageIcon className="h-3.5 w-3.5 text-[#64748B]" />
                  <span className="text-xs text-[#94A3B8]">Photo</span>
                </div>
                <span className={cn("text-xs", twin.avatar_image_url ? "text-[#42FFC6]" : "text-[#64748B]")}>
                  {twin.avatar_image_url ? "Uploaded" : "Not uploaded"}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Mic className="h-3.5 w-3.5 text-[#64748B]" />
                  <span className="text-xs text-[#94A3B8]">Voice</span>
                </div>
                <span className={cn("text-xs", twin.cloned_voice_id ? "text-[#42FFC6]" : "text-[#64748B]")}>
                  {twin.cloned_voice_id ? "Cloned" : "Not cloned"}
                </span>
              </div>
            </div>
          </div>

          {/* Pipeline steps card */}
          <div className="bg-[#0F172A]/80 backdrop-blur-2xl border border-white/[0.06] rounded-[20px] p-5 space-y-3">
            <h2 className="text-xs font-semibold text-[#94A3B8] uppercase tracking-wider">Creation Pipeline</h2>
            <div className="space-y-3">
              <StepIndicator label="Appearance" completed={!!appearance?.face_detected} />
              <StepIndicator label="Voice" completed={!!twin.cloned_voice_id} />
              <StepIndicator label="Personality" completed={!!personality} />
              <StepIndicator label="Intelligence" completed={isPublished} />
              <StepIndicator label="Published" completed={isPublished} />
            </div>
          </div>

          {/* Personality card */}
          {personality && Object.keys(personality).length > 0 && (
            <div className="bg-[#0F172A]/80 backdrop-blur-2xl border border-white/[0.06] rounded-[20px] p-5 space-y-3">
              <h2 className="text-xs font-semibold text-[#94A3B8] uppercase tracking-wider">Personality Traits</h2>
              <div className="space-y-2.5">
                {Object.entries(personality).slice(0, 6).map(([trait, value]) => (
                  <TraitBar
                    key={trait}
                    label={trait}
                    value={value as number}
                    color={
                      trait.includes("open") || trait.includes("friend")
                        ? "#7C5CFF"
                        : trait.includes("consci") || trait.includes("prof")
                          ? "#00E5FF"
                          : trait.includes("extra") || trait.includes("humor")
                            ? "#42FFC6"
                            : "#7C5CFF"
                    }
                  />
                ))}
              </div>
            </div>
          )}

          {/* Voice details card */}
          {voice && (
            <div className="bg-[#0F172A]/80 backdrop-blur-2xl border border-white/[0.06] rounded-[20px] p-5 space-y-3">
              <h2 className="text-xs font-semibold text-[#94A3B8] uppercase tracking-wider">Voice Profile</h2>
              <div className="space-y-2.5">
                {voice.accent && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-[#94A3B8]">Accent</span>
                    <span className="text-xs text-[#CBD5E1] capitalize">{voice.accent}</span>
                  </div>
                )}
                {voice.speaking_style && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-[#94A3B8]">Style</span>
                    <span className="text-xs text-[#CBD5E1] capitalize">{voice.speaking_style.replace(/_/g, " ")}</span>
                  </div>
                )}
                {voice.speech_rate && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-[#94A3B8]">Speed</span>
                    <span className="text-xs text-[#CBD5E1]">{voice.speech_rate} WPM</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex items-center gap-2 pt-2">
            <button
              onClick={handleChat}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-[#7C5CFF] to-[#00E5FF] text-white text-sm font-medium hover:shadow-lg hover:shadow-[#7C5CFF]/20 transition-all"
            >
              <MessageSquare className="h-4 w-4" />
              Chat
            </button>

            {isDraft && (
              <button
                onClick={handlePublish}
                disabled={publishing}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-[#42FFC6]/10 border border-[#42FFC6]/30 text-[#42FFC6] text-sm font-medium hover:bg-[#42FFC6]/20 transition-all"
              >
                {publishing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Zap className="h-4 w-4" />
                )}
                Publish
              </button>
            )}

            <button
              className="p-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-white/[0.08] transition-all"
              title="Settings"
            >
              <Settings className="h-4 w-4" />
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
