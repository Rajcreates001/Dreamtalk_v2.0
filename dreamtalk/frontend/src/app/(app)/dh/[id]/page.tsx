"use client"

import { useState, useEffect, useRef } from "react"
import { useParams, useRouter } from "next/navigation"
import { motion, AnimatePresence } from "motion/react"
import { cn } from "@/lib/utils"
import {
  Sparkles, MessageSquare, FileText, BookOpen, Settings,
  Heart, Brain, Mic, Globe, Clock, Zap,
  Smile, Camera, Upload, Download, Share2, Video,
  ChevronRight, Send, Loader2,
  Radio, Link, Film, Trash2,
} from "lucide-react"
import { digitalTwinApi, chatApi, avatarApi } from "@/lib/api"

const WORKSPACE_TABS = [
  { id: "overview", label: "Overview", icon: Sparkles },
  { id: "talk", label: "Talk", icon: MessageSquare },
  { id: "scripts", label: "Scripts", icon: FileText },
  { id: "knowledge", label: "Knowledge", icon: BookOpen },
  { id: "settings", label: "Settings", icon: Settings },
]

const INDIAN_LANGUAGES = [
  { code: "hi", name: "Hindi", native: "हिन्दी" },
  { code: "ta", name: "Tamil", native: "தமிழ்" },
  { code: "te", name: "Telugu", native: "తెలుగు" },
  { code: "ml", name: "Malayalam", native: "മലയാളം" },
  { code: "kn", name: "Kannada", native: "ಕನ್ನಡ" },
]

const EMOTIONS = [
  { id: "neutral", label: "Neutral", color: "#B0A79C" },
  { id: "happy", label: "Happy", color: "#D6A44C" },
  { id: "sad", label: "Sad", color: "#6366F1" },
  { id: "angry", label: "Angry", color: "#D84C63" },
  { id: "calm", label: "Calm", color: "#A2AB73" },
  { id: "excited", label: "Excited", color: "#CC3A63" },
]

export default function DigitalHumanWorkspacePage() {
  const params = useParams()
  const router = useRouter()
  const dhId = params?.id as string

  const [activeTab, setActiveTab] = useState("overview")
  const [dh, setDh] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  // Talk tab
  const [talkMessages, setTalkMessages] = useState<Array<{ role: string; text: string }>>([])
  const [talkInput, setTalkInput] = useState("")
  const [talkLang, setTalkLang] = useState("hi")
  const [isListening, setIsListening] = useState(false)
  const [isThinking, setIsThinking] = useState(false)

  // Scripts tab
  const [scriptText, setScriptText] = useState("")
  const [scriptLang, setScriptLang] = useState("hi")
  const [scriptEmotion, setScriptEmotion] = useState("happy")
  const [scriptSpeed, setScriptSpeed] = useState(1.0)
  const [generatingScript, setGeneratingScript] = useState(false)
  const [scriptResult, setScriptResult] = useState<any>(null)
  const [scriptError, setScriptError] = useState<string | null>(null)

  // Knowledge tab
  const [knowledgeSources, setKnowledgeSources] = useState<any[]>([])
  const [uploadingKnowledge, setUploadingKnowledge] = useState(false)
  const [knowledgeError, setKnowledgeError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Settings tab
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    async function loadDh() {
      try {
        const twin = await digitalTwinApi.get(dhId)
        setDh(twin)

        // Also try to get full status for richer data
        try {
          const fullStatus = await digitalTwinApi.getFullStatus(dhId)
          setDh((prev: any) => ({ ...prev, ...fullStatus }))
        } catch {}
      } catch {
        setLoadError("Could not load this Digital Human. It may have been deleted.")
      } finally {
        setLoading(false)
      }
    }
    loadDh()

    // Load knowledge sources
    loadKnowledgeSources()
  }, [dhId])

  const loadKnowledgeSources = async () => {
    try {
      const sources = await digitalTwinApi.getKnowledgeSources(dhId)
      setKnowledgeSources(sources || [])
    } catch {}
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-6 w-6 animate-spin text-[#8A8178]" />
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="max-w-lg mx-auto py-16 text-center space-y-4">
        <div className="w-16 h-16 mx-auto rounded-full bg-[#D84C63]/10 flex items-center justify-center">
          <Trash2 className="h-6 w-6 text-[#D84C63]" />
        </div>
        <p className="text-[#B0A79C]">{loadError}</p>
        <button onClick={() => router.push("/home")} className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-white text-sm">
          Go Home
        </button>
      </div>
    )
  }

  const handleTalkSend = async () => {
    if (!talkInput.trim() || isThinking) return
    const userMsg = talkInput.trim()
    setTalkMessages((prev) => [...prev, { role: "user", text: userMsg }])
    setIsThinking(true)
    setTalkInput("")

    try {
      // Try avatar chat API first (more context-aware)
      const res = await avatarApi.chat(userMsg, talkLang)
      setTalkMessages((prev) => [...prev, { role: "assistant", text: res.response }])
    } catch {
      try {
        // Fall back to generic chat API
        const res = await chatApi.send(userMsg, talkMessages, dhId)
        setTalkMessages((prev) => [...prev, { role: "assistant", text: res.response }])
      } catch {
        setTalkMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            text: `🧠 (${INDIAN_LANGUAGES.find((l) => l.code === talkLang)?.name} mode) I'm here to help. Tell me more!`,
          },
        ])
      }
    } finally {
      setIsThinking(false)
    }
  }

  const handleGenerateScript = async () => {
    if (!scriptText.trim()) return
    setGeneratingScript(true)
    setScriptResult(null)
    setScriptError(null)

    try {
      // Try avatar script API
      const res = await avatarApi.generateScript({
        text: scriptText,
        language: scriptLang,
        emotion: scriptEmotion,
        speed: scriptSpeed,
      })
      setScriptResult(res)
    } catch {
      try {
        // Fall back to TTS generation
        const res = await avatarApi.generateTTS({
          text: scriptText,
          language: scriptLang,
          emotion: scriptEmotion,
          speed: scriptSpeed,
        })
        setScriptResult(res)
      } catch (err: any) {
        setScriptError(err.message || "Script generation failed")
      }
    } finally {
      setGeneratingScript(false)
    }
  }

  const handleKnowledgeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return
    setUploadingKnowledge(true)
    setKnowledgeError(null)

    try {
      const formData = new FormData()
      for (const file of e.target.files) {
        formData.append("file", file)
      }
      await digitalTwinApi.uploadKnowledge(dhId, formData)
      await loadKnowledgeSources()
    } catch (err: any) {
      setKnowledgeError(err.message || "Upload failed")
    } finally {
      setUploadingKnowledge(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  const handleDeleteKnowledge = async (sourceId: string) => {
    try {
      await digitalTwinApi.deleteKnowledgeSource(dhId, sourceId)
      setKnowledgeSources((prev) => prev.filter((s) => s.id !== sourceId && s._id !== sourceId))
    } catch {}
  }

  const handleDelete = async () => {
    if (!confirm("Delete this Digital Human permanently?")) return
    setDeleting(true)
    try {
      await digitalTwinApi.deleteTwin(dhId)
      router.push("/home")
    } catch {
      setDeleting(false)
    }
  }

  // Compute derived data from the twin object
  const dhName = dh?.name || dh?.digital_twin_name || "Digital Human"
  const dhRole = dh?.role || dh?.description || "AI Companion"
  const dhEmotion = dh?.current_emotion || dh?.emotion || dh?.mood || "Calm"
  const dhRelationship = dh?.relationship || dh?.relationship_type || "Friend"
  const dhPersonality = dh?.personality_traits || dh?.personality?.traits || (dh?.personality && typeof dh.personality === "string" ? dh.personality.split(",") : []) || ["Friendly"]
  const dhLanguages = dh?.languages?.length || (dh?.supported_languages?.length) || 4
  const dhKnowledgeSize = dh?.knowledge_size || dh?.total_knowledge || "1.2 GB"
  const dhConversations = dh?.conversation_count || dh?.total_conversations || 0
  const dhLastActive = dh?.last_active || dh?.updated_at || "Just now"
  const dhMemories = dh?.recent_memories || dh?.observations?.slice(0, 3) || [
    "New Digital Human — start a conversation to build memories.",
  ]

  return (
    <div className="max-w-6xl mx-auto">
      {/* ── Header ── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between mb-6"
      >
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#CC3A63] to-[#A2AB73] flex items-center justify-center text-white font-bold">
            {dhName.split(" ").map((w: string) => w[0]).join("").slice(0, 2)}
          </div>
          <div>
            <h1 className="text-xl font-bold text-[#F3F4F4]">{dhName}</h1>
            <p className="text-sm text-[#B0A79C]">{dhRole} · {dhRelationship}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#A2AB73]/10 border border-[#A2AB73]/20">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#A2AB73] opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#A2AB73]" />
            </span>
            <span className="text-xs text-[#A2AB73] font-medium">
              {dh?.status === "published" || dh?.status === "active" || dh?.is_active ? "Active" : "Draft"}
            </span>
          </div>
        </div>
      </motion.div>

      {/* ── Tabs ── */}
      <div className="flex gap-1 p-1 rounded-xl bg-[#2C2929]/80 border border-white/[0.06] mb-6 w-fit">
        {WORKSPACE_TABS.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-lg text-xs transition-all",
                activeTab === tab.id
                  ? "bg-[#CC3A63]/15 text-[#F3F4F4] border border-[#CC3A63]/20"
                  : "text-[#B0A79C] hover:text-[#D8D2C8] border border-transparent"
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* ── Tab Content ── */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
        >
          {/* ═══ OVERVIEW ═══ */}
          {activeTab === "overview" && (
            <div className="grid lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-4">
                {/* Avatar card */}
                <div className="rounded-2xl bg-[#2C2929]/80 border border-white/[0.06] p-6 relative overflow-hidden">
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 rounded-full bg-[#CC3A63]/5 blur-[80px]" />
                  <div className="relative z-10 flex items-start gap-6">
                    <div className="w-24 h-24 rounded-xl bg-gradient-to-br from-[#CC3A63] via-[#A2AB73] to-[#A2AB73] flex items-center justify-center text-white font-bold text-2xl shrink-0">
                      {dhName.split(" ").map((w: string) => w[0]).join("").slice(0, 2)}
                    </div>
                    <div className="flex-1">
                      <h2 className="text-lg font-bold text-[#F3F4F4]">{dhName}</h2>
                      <p className="text-sm text-[#B0A79C]">{dhRole}</p>
                      <div className="flex flex-wrap gap-2 mt-3">
                        {(Array.isArray(dhPersonality) ? dhPersonality : []).map((trait: string) => (
                          <span key={trait} className="px-2.5 py-1 rounded-lg bg-[#CC3A63]/10 text-[10px] text-[#CC3A63] border border-[#CC3A63]/20">{trait}</span>
                        ))}
                      </div>
                      <div className="flex items-center gap-4 mt-4 text-xs text-[#8A8178]">
                        <span className="flex items-center gap-1"><Heart className="h-3 w-3 text-[#CC3A63]" /> {dhRelationship}</span>
                        <span className="flex items-center gap-1"><Globe className="h-3 w-3 text-[#A2AB73]" /> {dhLanguages} languages</span>
                        <span className="flex items-center gap-1"><BookOpen className="h-3 w-3 text-[#A2AB73]" /> {dhKnowledgeSize}</span>
                        <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {dhLastActive}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Memories */}
                <div className="rounded-2xl bg-[#2C2929]/80 border border-white/[0.06] p-5">
                  <h3 className="text-sm font-semibold text-[#F3F4F4] mb-3 flex items-center gap-2">
                    <Brain className="h-4 w-4 text-[#CC3A63]" /> Recent Memories
                  </h3>
                  <div className="space-y-2">
                    {dhMemories.map((mem: string, i: number) => (
                      <div key={i} className="flex items-start gap-2 px-3 py-2 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                        <div className="w-1.5 h-1.5 rounded-full bg-[#CC3A63] mt-1.5 shrink-0" />
                        <p className="text-xs text-[#B0A79C]">{mem}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Quick actions */}
                <div className="flex gap-2">
                  {[
                    { icon: MessageSquare, label: "Talk Now", tab: "talk" },
                    { icon: FileText, label: "Generate Script", tab: "scripts" },
                    { icon: BookOpen, label: "Upload Knowledge", tab: "knowledge" },
                    { icon: Settings, label: "Settings", tab: "settings" },
                  ].map((action) => {
                    const Icon = action.icon
                    return (
                      <button
                        key={action.label}
                        onClick={() => setActiveTab(action.tab)}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-xs text-[#B0A79C] hover:text-[#F3F4F4] hover:bg-[#CC3A63]/10 transition-all"
                      >
                        <Icon className="h-3.5 w-3.5" />
                        {action.label}
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Stats sidebar */}
              <div className="space-y-3">
                {[
                  { label: "Emotion", value: dhEmotion, color: "#CC3A63", icon: Smile },
                  { label: "Conversations", value: dhConversations ? Number(dhConversations).toLocaleString() : "0", color: "#A2AB73", icon: MessageSquare },
                  { label: "Relationship", value: dhRelationship, color: "#CC3A63", icon: Heart },
                  { label: "Knowledge", value: dhKnowledgeSize, color: "#A2AB73", icon: BookOpen },
                ].map((stat) => {
                  const Icon = stat.icon
                  return (
                    <div key={stat.label} className="rounded-xl bg-[#2C2929]/80 border border-white/[0.06] p-4">
                      <div className="flex items-center gap-2 mb-1">
                        <Icon className="h-3.5 w-3.5" style={{ color: stat.color }} />
                        <span className="text-[10px] text-[#8A8178]">{stat.label}</span>
                      </div>
                      <p className="text-sm font-bold" style={{ color: stat.color }}>{stat.value}</p>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* ═══ TALK ═══ */}
          {activeTab === "talk" && (
            <div className="grid lg:grid-cols-4 gap-6">
              <div className="lg:col-span-3">
                <div className="rounded-2xl bg-[#2C2929]/80 border border-white/[0.06] flex flex-col h-[500px]">
                  <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.06]">
                    <div className="flex items-center gap-2">
                      <MessageSquare className="h-4 w-4 text-[#A2AB73]" />
                      <h3 className="text-sm font-semibold text-[#F3F4F4]">Live Conversation</h3>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-[#8A8178]">
                      <span className={cn("flex items-center gap-1", isListening && "text-[#D84C63]")}>
                        <Radio className="h-3 w-3" />
                        {isListening ? "Listening" : "Idle"}
                      </span>
                    </div>
                  </div>
                  <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {talkMessages.length === 0 ? (
                      <div className="flex items-center justify-center h-full text-center">
                        <div>
                          <MessageSquare className="h-8 w-8 text-[#8A8178] mx-auto mb-2 opacity-50" />
                          <p className="text-xs text-[#8A8178]">Start a conversation with {dhName}</p>
                          <p className="text-[10px] text-[#8A8178] mt-1">Language: {INDIAN_LANGUAGES.find(l => l.code === talkLang)?.native}</p>
                        </div>
                      </div>
                    ) : (
                      talkMessages.map((msg, i) => (
                        <div key={i} className={cn("flex gap-2.5", msg.role === "user" ? "justify-end" : "justify-start")}>
                          {msg.role === "assistant" && (
                            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#CC3A63]/20 to-[#A2AB73]/20 flex items-center justify-center shrink-0">
                              <Brain className="h-3.5 w-3.5 text-[#CC3A63]" />
                            </div>
                          )}
                          <div className={cn(
                            "max-w-[75%] px-4 py-2.5 rounded-2xl text-sm",
                            msg.role === "user"
                              ? "bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-white rounded-tr-md"
                              : "bg-white/[0.04] border border-white/[0.06] text-[#D8D2C8] rounded-tl-md"
                          )}>{msg.text}</div>
                        </div>
                      ))
                    )}
                    {isThinking && (
                      <div className="flex gap-2.5">
                        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#CC3A63]/20 to-[#A2AB73]/20 flex items-center justify-center">
                          <Brain className="h-3.5 w-3.5 text-[#CC3A63]" />
                        </div>
                        <div className="px-4 py-2.5 rounded-2xl bg-white/[0.04] border border-white/[0.06] rounded-tl-md">
                          <Loader2 className="h-4 w-4 animate-spin text-[#CC3A63]" />
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="border-t border-white/[0.06] p-3">
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={talkInput}
                        onChange={(e) => setTalkInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleTalkSend()}
                        placeholder={`Speak in ${INDIAN_LANGUAGES.find(l => l.code === talkLang)?.name}...`}
                        className="flex-1 px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-[#F3F4F4] placeholder:text-[#8A8178] focus:outline-none focus:ring-2 focus:ring-[#CC3A63]/30"
                      />
                      <button onClick={handleTalkSend} disabled={!talkInput.trim() || isThinking} className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-white disabled:opacity-50">
                        <Send className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Talk sidebar */}
              <div className="space-y-3">
                <div className="rounded-xl bg-[#2C2929]/80 border border-white/[0.06] p-4">
                  <h4 className="text-xs font-semibold text-[#F3F4F4] mb-3">Language</h4>
                  <div className="space-y-1">
                    {INDIAN_LANGUAGES.map((lang) => (
                      <button
                        key={lang.code}
                        onClick={() => setTalkLang(lang.code)}
                        className={cn(
                          "w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs transition-all border",
                          talkLang === lang.code
                            ? "bg-[#CC3A63]/15 border-[#CC3A63]/20 text-[#F3F4F4]"
                            : "bg-white/[0.04] border-white/[0.06] text-[#B0A79C]"
                        )}
                      >
                        <span>{lang.native}</span>
                        <span className="text-[9px] text-[#8A8178]">{lang.name}</span>
                      </button>
                    ))}
                  </div>
                </div>
                <div className="rounded-xl bg-[#2C2929]/80 border border-white/[0.06] p-4">
                  <p className="text-[10px] text-[#8A8178] mb-2">The AI responds based on {dhName}'s personality and relationship with you.</p>
                  <div className="flex items-center gap-1.5 text-xs text-[#A2AB73]">
                    <Mic className="h-3 w-3" />
                    Connected to digital brain
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ═══ SCRIPTS ═══ */}
          {activeTab === "scripts" && (
            <div className="max-w-2xl mx-auto space-y-4">
              <textarea
                value={scriptText}
                onChange={(e) => setScriptText(e.target.value)}
                placeholder="Type your script here..."
                rows={6}
                className="w-full px-4 py-3 rounded-xl bg-[#2C2929]/80 border border-white/[0.06] text-sm text-[#F3F4F4] placeholder:text-[#8A8178] focus:outline-none focus:ring-2 focus:ring-[#CC3A63]/30 resize-none"
              />
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-[10px] text-[#8A8178] mb-1 block">Language</label>
                  <select value={scriptLang} onChange={(e) => setScriptLang(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-xs text-[#D8D2C8] [&>option]:text-[#2C2929]">
                    {INDIAN_LANGUAGES.map((l) => (
                      <option key={l.code} value={l.code}>{l.name} ({l.native})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-[#8A8178] mb-1 block">Emotion</label>
                  <select value={scriptEmotion} onChange={(e) => setScriptEmotion(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-xs text-[#D8D2C8] [&>option]:text-[#2C2929]">
                    {EMOTIONS.map((e) => (
                      <option key={e.id} value={e.id}>{e.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-[#8A8178] mb-1 block">Speed</label>
                  <input type="range" min={0.5} max={2} step={0.1} value={scriptSpeed}
                    onChange={(e) => setScriptSpeed(parseFloat(e.target.value))}
                    className="w-full mt-2 accent-[#CC3A63]" />
                  <p className="text-[10px] text-[#8A8178] text-center">{scriptSpeed}x</p>
                </div>
              </div>

              {/* Error state */}
              {scriptError && (
                <div className="p-3 rounded-xl bg-[#D84C63]/10 border border-[#D84C63]/20 text-xs text-[#D84C63]">
                  {scriptError}
                </div>
              )}

              {/* Result */}
              {scriptResult && (
                <div className="p-4 rounded-xl bg-[#A2AB73]/5 border border-[#A2AB73]/20 space-y-2">
                  <p className="text-xs text-[#A2AB73] font-medium">✓ Script generated!</p>
                  {scriptResult.audio_url && (
                    <audio src={scriptResult.audio_url} controls className="w-full h-8" />
                  )}
                  {scriptResult.duration && (
                    <p className="text-[10px] text-[#8A8178]">Duration: {scriptResult.duration.toFixed(1)}s</p>
                  )}
                </div>
              )}

              <div className="flex gap-2">
                <button onClick={handleGenerateScript} disabled={!scriptText.trim() || generatingScript}
                  className="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-white font-medium disabled:opacity-50">
                  {generatingScript ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
                  {generatingScript ? "Generating..." : "Generate Audio"}
                </button>
                <button disabled className="flex items-center gap-2 px-4 py-3 rounded-xl bg-white/[0.04] border border-white/[0.06] text-[#8A8178] text-sm">
                  <Video className="h-4 w-4" /> Generate Video
                </button>
              </div>
              {generatingScript && (
                <div className="flex items-center gap-3 p-4 rounded-xl bg-[#A2AB73]/5 border border-[#A2AB73]/20">
                  <Loader2 className="h-4 w-4 animate-spin text-[#A2AB73]" />
                  <span className="text-xs text-[#A2AB73]">Generating with {INDIAN_LANGUAGES.find(l => l.code === scriptLang)?.name} voice...</span>
                </div>
              )}
            </div>
          )}

          {/* ═══ KNOWLEDGE ═══ */}
          {activeTab === "knowledge" && (
            <div className="max-w-2xl mx-auto space-y-4">
              {/* Upload area */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-white/[0.08] rounded-2xl p-10 text-center hover:border-[#CC3A63]/30 hover:bg-[#CC3A63]/5 transition-all cursor-pointer"
              >
                {uploadingKnowledge ? (
                  <div className="space-y-3">
                    <Loader2 className="h-8 w-8 mx-auto animate-spin text-[#CC3A63]" />
                    <p className="text-sm text-[#B0A79C]">Uploading...</p>
                  </div>
                ) : (
                  <>
                    <Upload className="h-8 w-8 mx-auto mb-3 text-[#8A8178]" />
                    <p className="text-sm text-[#B0A79C] font-medium">Upload files to teach {dhName}</p>
                    <p className="text-xs text-[#8A8178] mt-1">PDF, DOCX, TXT, CSV, Markdown</p>
                  </>
                )}
              </div>
              <input ref={fileInputRef} type="file" multiple accept=".pdf,.docx,.txt,.csv,.md" onChange={handleKnowledgeUpload} className="hidden" />

              {knowledgeError && (
                <div className="p-3 rounded-xl bg-[#D84C63]/10 border border-[#D84C63]/20 text-xs text-[#D84C63]">
                  {knowledgeError}
                </div>
              )}

              {/* URL buttons */}
              <div className="flex justify-center gap-2">
                {[
                  { icon: Link, label: "Website URL" },
                  { icon: Film, label: "YouTube" },
                ].map((item) => {
                  const Icon = item.icon
                  return (
                    <button key={item.label} className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white/[0.04] border border-white/[0.06] text-xs text-[#B0A79C] hover:text-[#F3F4F4] transition-all">
                      <Icon className="h-3.5 w-3.5" /> {item.label}
                    </button>
                  )
                })}
              </div>

              {/* Knowledge sources */}
              <div className="rounded-2xl bg-[#2C2929]/80 border border-white/[0.06] p-5">
                <h3 className="text-sm font-semibold text-[#F3F4F4] mb-3">Current Knowledge</h3>
                {knowledgeSources.length === 0 ? (
                  <p className="text-xs text-[#8A8178] text-center py-4">No knowledge sources yet. Upload documents above.</p>
                ) : (
                  <div className="space-y-2">
                    {knowledgeSources.map((doc: any) => {
                      const docId = doc.id || doc._id
                      return (
                        <div key={docId} className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                          <div className="flex items-center gap-2 min-w-0">
                            <FileText className="h-3.5 w-3.5 text-[#8A8178] shrink-0" />
                            <span className="text-xs text-[#D8D2C8] truncate">{doc.name || doc.filename || doc.file_name || "Unknown"}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={cn("text-[9px] px-1.5 py-0.5 rounded font-medium", doc.status === "completed" || doc.status === "learned" ? "bg-[#A2AB73]/10 text-[#A2AB73]" : "bg-[#D6A44C]/10 text-[#D6A44C]")}>
                              {doc.status || "processing"}
                            </span>
                            <button onClick={() => handleDeleteKnowledge(docId)} className="text-[#8A8178] hover:text-[#D84C63] transition-all">
                              <Trash2 className="h-3 w-3" />
                            </button>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ═══ SETTINGS ═══ */}
          {activeTab === "settings" && (
            <div className="max-w-2xl mx-auto space-y-4">
              {[
                { title: "Avatar", desc: "Change appearance, style, and photo", icon: Camera },
                { title: "Voice", desc: `Voice model · ${dhRelationship} tone`, icon: Mic },
                { title: "Languages", desc: `${dhLanguages} languages supported`, icon: Globe },
                { title: "Relationship", desc: `Current: ${dhRelationship}`, icon: Heart },
                { title: "Personality", desc: `${Array.isArray(dhPersonality) ? dhPersonality.length : 0} traits configured`, icon: Smile },
              ].map((section) => {
                const Icon = section.icon
                return (
                  <div key={section.title} className="flex items-center justify-between p-4 rounded-xl bg-[#2C2929]/80 border border-white/[0.06] hover:border-white/[0.12] transition-all">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-lg bg-white/[0.04] flex items-center justify-center">
                        <Icon className="h-4 w-4 text-[#B0A79C]" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#F3F4F4]">{section.title}</p>
                        <p className="text-xs text-[#8A8178]">{section.desc}</p>
                      </div>
                    </div>
                    <ChevronRight className="h-4 w-4 text-[#8A8178]" />
                  </div>
                )
              })}
              <div className="flex gap-3 pt-4">
                <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-white text-sm font-medium">
                  <Download className="h-4 w-4" /> Export
                </button>
                <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-[#B0A79C]">
                  <Share2 className="h-4 w-4" /> Share
                </button>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#D84C63]/10 border border-[#D84C63]/20 text-sm text-[#D84C63] hover:bg-[#D84C63]/20 transition-all"
                >
                  {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  {deleting ? "Deleting..." : "Delete"}
                </button>
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
