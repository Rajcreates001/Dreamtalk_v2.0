"use client"

import { useState, useRef, useEffect } from "react"
import { motion, AnimatePresence } from "motion/react"
import {
  MessageSquare, Search, Plus, Bot,
  Brain, Heart, BookOpen, Cpu,
  ChevronRight, PanelRightOpen, PanelRightClose,
  ArrowLeft, Loader2,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useChat } from "@/hooks/use-chat"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ChatMessage } from "@/components/chat/chat-message"
import { ChatInput } from "@/components/chat/chat-input"
import { WelcomeScreen } from "@/components/chat/welcome-screen"
import { AvatarResult } from "@/components/chat/avatar-result"
import { Particles } from "@/components/magic/particles"
import { SpatialScene } from "@/components/3d/spatial-scene"
import { useTheme } from "@/components/layout/theme-provider"
import { digitalTwinApi, pipelineApi, avatarApi, API_BASE_URL } from "@/lib/api"

const THINKING_DATA = {
  emotion: "Calm & Engaged",
  emotionScore: 87,
  knowledgeRetrieved: "Memory Systems, Neural Networks",
  memoryUsed: "Last 5 interactions, User preferences",
  reasoning: "User is asking about long-term memory architecture. Retrieving relevant knowledge...",
  confidence: 94,
  latency: "124ms",
  sources: ["Memory Systems White Paper", "DreamTalk Architecture Docs", "User Conversation History"],
}

type ConversationItem = {
  id: string
  title: string
  preview: string
  time: string
}

function timeAgo(timestamp: string | number): string {
  const diff = Date.now() - new Date(timestamp).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return `${Math.floor(days / 7)}w ago`
}

export default function ConversationsPage() {
  const {
    messages, isLoading, isSpeaking, emotion,
    pipelineStatus, pipelineResult, sendMessage, stopGeneration,
  } = useChat()

  const [showPanel, setShowPanel] = useState(true)
  const [avatarExpanded, setAvatarExpanded] = useState(true)
  const [activeConv, setActiveConv] = useState<string | null>(null)
  const [conversations, setConversations] = useState<ConversationItem[]>([])
  const [convLoading, setConvLoading] = useState(true)
  const [meshUrl, setMeshUrl] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  const { theme } = useTheme()
  const isDark = theme === "dark"

  // Fetch avatar mesh from backend session
  useEffect(() => {
    async function fetchMesh() {
      try {
        const session = await avatarApi.getSession()
        if (session?.mesh_url) {
          // mesh_url is relative like /api/static/current_mesh.obj — prepend API base
          const fullUrl = session.mesh_url.startsWith("http")
            ? session.mesh_url
            : `${API_BASE_URL}${session.mesh_url}`
          setMeshUrl(fullUrl)
        }
      } catch {
        // No mesh available yet — will show fallback
      }
    }
    fetchMesh()
    // Re-fetch every 30s in case a pipeline run completes
    const interval = setInterval(fetchMesh, 30000)
    return () => clearInterval(interval)
  }, [])

  // Load real conversation history
  useEffect(() => {
    async function loadHistory() {
      try {
        setConvLoading(true)
        const items: ConversationItem[] = []

        // Try to find conversation history from twins or pipelines
        let twinList: any[] = []
        try {
          twinList = (await digitalTwinApi.list()) || []
          if (twinList && twinList.length > 0) {
            for (const twin of twinList.slice(0, 5)) {
              items.push({
                id: twin.id,
                title: twin.name || "Conversation",
                preview: twin.description || twin.greeting || "Continue your conversation...",
                time: timeAgo(twin.updated_at || twin.created_at || Date.now()),
              })
            }
          }
        } catch {}

        // If no conversations from API, try pipeline history
        if (items.length === 0 && twinList?.[0]?.id) {
          try {
            const history = await pipelineApi.history(twinList[0].id)
            if (history && history.length > 0) {
              for (const entry of history.slice(0, 5)) {
                items.push({
                  id: entry.id || entry.pipeline_id,
                  title: `Pipeline Run`,
                  preview: entry.text?.slice(0, 60) || entry.status || "Processing complete",
                  time: timeAgo(entry.created_at || Date.now()),
                })
              }
            }
          } catch {}
        }

        // Fall back to sample data
        if (items.length === 0) {
          items.push(
            { id: "demo-1", title: "Memory Systems Discussion", preview: "How do you store long-term memories?", time: "2 min ago" },
            { id: "demo-2", title: "Knowledge Base Update", preview: "I've processed the new PDF documents...", time: "1 hr ago" },
            { id: "demo-3", title: "Emotional State Analysis", preview: "Your current emotional state appears calm", time: "3 hrs ago" },
            { id: "demo-4", title: "Voice Training Session", preview: "Voice clone completed successfully", time: "Yesterday" },
            { id: "demo-5", title: "Deployment Planning", preview: "Ready to deploy to production environment", time: "2 days ago" },
          )
        }

        setConversations(items)
        if (items.length > 0) setActiveConv(items[0].id)
      } catch {
        setConversations([
          { id: "demo-1", title: "Memory Systems Discussion", preview: "How do you store long-term memories?", time: "2 min ago" },
        ])
        setActiveConv("demo-1")
      } finally {
        setConvLoading(false)
      }
    }
    loadHistory()
  }, [])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  return (
    <div className="flex h-full -m-6 lg:-m-8 bg-background overflow-hidden">
      <SpatialScene intensity={0.3} isDark={isDark} interactive reduced />

      {/* ─── Left: Conversation History ─── */}
      <div className="w-56 lg:w-64 shrink-0 border-r border-white/[0.06] flex flex-col bg-[#2C2929]/30 relative z-10">
        <div className="p-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.06] text-[#8A8178] text-sm">
            <Search className="h-3.5 w-3.5 shrink-0" />
            <input
              type="text"
              placeholder="Search conversations..."
              className="bg-transparent text-xs text-[#F3F4F4] placeholder:text-[#8A8178] focus:outline-none w-full"
            />
          </div>
          <button
            type="button"
            className="w-full mt-2 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-gradient-to-r from-[#CC3A63]/20 to-[#A2AB73]/10 border border-[#CC3A63]/20 text-xs text-[#CC3A63] font-medium hover:from-[#CC3A63]/30 transition-all"
          >
            <Plus className="h-3 w-3" />
            New Conversation
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {convLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-[#8A8178]" />
            </div>
          ) : conversations.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-xs text-[#8A8178]">No conversations yet</p>
            </div>
          ) : (
            conversations.map((conv) => (
            <button
              key={conv.id}
              type="button"
              onClick={() => setActiveConv(conv.id)}
              className={cn(
                "w-full text-left p-2.5 rounded-xl transition-all",
                activeConv === conv.id
                  ? "bg-[#CC3A63]/10 border border-[#CC3A63]/20"
                  : "hover:bg-white/[0.04] border border-transparent"
              )}
            >
              <p className="text-xs font-semibold text-[#D8D2C8] truncate">{conv.title}</p>
              <p className="text-[10px] text-[#8A8178] mt-0.5 truncate">{conv.preview}</p>
              <p className="text-[9px] text-[#8A8178] mt-1">{conv.time}</p>
            </button>
          )))}
        </div>
      </div>

      {/* ─── Center-Left: Avatar Panel ─── */}
      <motion.div
        layout
        transition={{ duration: 0.4, ease: "easeInOut" }}
        className={cn(
          "relative flex flex-col border-r border-white/[0.06] bg-[#2C2929]/20 shrink-0 relative z-10",
          avatarExpanded ? "w-[300px] xl:w-[340px]" : "w-[0px] overflow-hidden",
          "hidden lg:flex"
        )}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06] shrink-0">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-emerald-400/20 to-blue-400/20 flex items-center justify-center">
              <MessageSquare className="h-3.5 w-3.5 text-emerald-500" />
            </div>
            <div>
              <h2 className="text-xs font-semibold text-[#D8D2C8]">Dr. Aria</h2>
              <p className="text-[9px] text-[#8A8178]">AI Companion</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setAvatarExpanded(false)}
            className="h-6 w-6 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] transition-colors flex items-center justify-center"
          >
            <ArrowLeft className="h-3 w-3 text-[#8A8178]" />
          </button>
        </div>

        <div className="flex-1 relative overflow-hidden">
          <AvatarResult
            vrmModelUrl={meshUrl || process.env.NEXT_PUBLIC_VRM_MODEL_URL || null}
            generatedVideoUrl={pipelineResult?.videoUrl ?? null}
            generatedAudioUrl={pipelineResult?.audioUrl ?? null}
            emotion={emotion}
            isSpeaking={isSpeaking}
            className="w-full h-full"
          />
        </div>
      </motion.div>

      {/* Avatar collapse toggle */}
      {!avatarExpanded && (
        <button
          type="button"
          onClick={() => setAvatarExpanded(true)}
          className="hidden lg:flex items-center justify-center w-6 h-12 self-center bg-[#2C2929]/40 border border-white/[0.06] rounded-r-lg text-[#8A8178] hover:text-[#B0A79C] relative z-10 cursor-pointer"
        >
          <ChevronRight className="h-3 w-3" />
        </button>
      )}

      {/* ─── Center: Chat ─── */}
      <div className="flex-1 flex flex-col min-w-0 relative z-10">
        <Particles
          quantity={40}
          color="#8F9A5E"
          className="absolute inset-0 opacity-20 pointer-events-none"
          staticity={100}
          ease={120}
        />

        {/* Chat header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06] bg-[#2C2929]/30">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-emerald-400/20 to-blue-400/20 flex items-center justify-center">
              <Bot className="h-3.5 w-3.5 text-emerald-500" />
            </div>
            <div>
              <p className="text-xs font-semibold text-[#D8D2C8]">Dr. Aria</p>
              <p className="text-[9px] text-emerald-500">
                {isSpeaking ? "Speaking..." : "● Online"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {emotion && (
              <span className="text-[10px] text-[#8A8178] flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                {emotion}
              </span>
            )}
            <span className="text-[10px] text-[#8A8178] flex items-center gap-1.5">
              <span className={cn("h-1.5 w-1.5 rounded-full", isLoading ? "bg-amber-500 animate-pulse" : "bg-emerald-500")} />
              {pipelineStatus === "processing" ? "Processing" : isLoading ? "Thinking" : "Ready"}
            </span>
            <button
              type="button"
              onClick={() => setShowPanel(!showPanel)}
              className="p-1.5 rounded-lg hover:bg-white/[0.06] text-[#8A8178] hover:text-[#B0A79C] transition-all"
            >
              {showPanel ? <PanelRightClose className="h-3.5 w-3.5" /> : <PanelRightOpen className="h-3.5 w-3.5" />}
            </button>
          </div>
        </div>

        {/* Messages */}
        <ScrollArea ref={scrollRef} className="flex-1 px-4 py-4">
          {messages.length === 0 ? (
            <WelcomeScreen />
          ) : (
            <div className="flex flex-col gap-4 max-w-3xl mx-auto w-full">
              {messages.map((msg, i) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10, filter: "blur(4px)" }}
                  animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                  transition={{ duration: 0.3 }}
                >
                  <ChatMessage message={msg} />
                </motion.div>
              ))}
              {isLoading && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-3"
                >
                  <div className="h-8 w-8 rounded-full bg-emerald-500/10 flex items-center justify-center shrink-0">
                    <span className="text-xs font-bold text-emerald-600">D</span>
                  </div>
                  <div className="flex items-center gap-1.5 px-4 py-3 rounded-2xl bg-white/[0.04] border border-white/[0.06] rounded-tl-md">
                    <span className="h-2 w-2 rounded-full bg-[#8A8178] animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="h-2 w-2 rounded-full bg-[#8A8178] animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="h-2 w-2 rounded-full bg-[#8A8178] animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </motion.div>
              )}
            </div>
          )}
        </ScrollArea>

        {/* Input */}
        <div className="border-t border-white/[0.06] bg-[#2C2929]/20">
          <ChatInput onSend={sendMessage} onStop={stopGeneration} isLoading={isLoading} />
        </div>
      </div>

      {/* ─── Right: Avatar Thinking Panel ─── */}
      <AnimatePresence>
        {showPanel && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 260, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            className="border-l border-white/[0.06] bg-[#2C2929]/30 overflow-hidden shrink-0 relative z-10"
          >
            <div className="w-[260px] p-4 space-y-4">
              <h3 className="text-xs font-semibold text-[#F3F4F4] flex items-center gap-2">
                <Brain className="h-3.5 w-3.5 text-[#CC3A63]" />
                Avatar Thoughts
              </h3>

              {/* Emotion */}
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-[#8A8178] flex items-center gap-1.5">
                    <Heart className="h-3 w-3 text-[#CC3A63]" />
                    Emotion
                  </span>
                  <span className="text-[10px] text-[#CC3A63] font-medium">{THINKING_DATA.emotionScore}%</span>
                </div>
                <p className="text-xs text-[#D8D2C8]">{emotion || THINKING_DATA.emotion}</p>
                <div className="h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${THINKING_DATA.emotionScore}%` }}
                    className="h-full rounded-full bg-gradient-to-r from-[#CC3A63] to-[#CC3A63]"
                  />
                </div>
              </div>

              {/* Knowledge Retrieved */}
              <div className="space-y-1.5">
                <span className="text-[10px] text-[#8A8178] flex items-center gap-1.5">
                  <BookOpen className="h-3 w-3 text-[#A2AB73]" />
                  Knowledge Retrieved
                </span>
                <p className="text-[11px] text-[#D8D2C8]">{THINKING_DATA.knowledgeRetrieved}</p>
              </div>

              {/* Memory */}
              <div className="space-y-1.5">
                <span className="text-[10px] text-[#8A8178] flex items-center gap-1.5">
                  <Brain className="h-3 w-3 text-[#CC3A63]" />
                  Memory Used
                </span>
                <p className="text-[11px] text-[#D8D2C8]">{THINKING_DATA.memoryUsed}</p>
              </div>

              {/* Reasoning */}
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-[10px] text-[#8A8178] flex items-center gap-1.5 mb-1.5">
                  <Cpu className="h-3 w-3 text-[#D6A44C]" />
                  Reasoning
                </span>
                <p className="text-[11px] text-[#B0A79C] leading-relaxed">{THINKING_DATA.reasoning}</p>
              </div>

              {/* Sources */}
              <div className="space-y-1.5">
                <span className="text-[10px] text-[#8A8178]">Sources</span>
                {THINKING_DATA.sources.map((src, i) => (
                  <div key={i} className="flex items-center gap-2 text-[10px] text-[#8A8178]">
                    <div className="w-1 h-1 rounded-full bg-[#CC3A63]" />
                    {src}
                  </div>
                ))}
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-white/[0.06]">
                <div>
                  <p className="text-[9px] text-[#8A8178]">Confidence</p>
                  <p className="text-xs font-semibold text-[#A2AB73]">{THINKING_DATA.confidence}%</p>
                </div>
                <div>
                  <p className="text-[9px] text-[#8A8178]">Latency</p>
                  <p className="text-xs font-semibold text-[#F3F4F4]">{THINKING_DATA.latency}</p>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
