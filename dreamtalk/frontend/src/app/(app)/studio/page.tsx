"use client"

import { useState, useEffect } from "react"
import { useSearchParams } from "next/navigation"
import { motion, AnimatePresence } from "motion/react"
import { cn } from "@/lib/utils"
import {
  Palette, Mic, Heart, BookOpen, Brain,
  Smile, Eye, HeartHandshake, Move3d, Camera,
  Zap, Sliders, FlaskConical, Rocket, Save,
  Play, Check, Upload, Loader2,
  RefreshCw, Plus, GripVertical, Monitor,
} from "lucide-react"
import { digitalTwinApi, digitalHumanApi } from "@/lib/api"

const STUDIO_TABS = [
  { id: "appearance", label: "Appearance", icon: Palette, desc: "Name, style & look" },
  { id: "voice", label: "Voice", icon: Mic, desc: "Speech synthesis & accent" },
  { id: "personality", label: "Personality", icon: Heart, desc: "Traits & behavior" },
  { id: "knowledge", label: "Knowledge", icon: BookOpen, desc: "Documents & sources" },
  { id: "memory", label: "Memory", icon: Brain, desc: "Retention & context" },
  { id: "emotion", label: "Emotion", icon: Smile, desc: "Range & sensitivity" },
  { id: "expressions", label: "Expressions", icon: Eye, desc: "Facial & gestures" },
  { id: "relationships", label: "Relationships", icon: HeartHandshake, desc: "Bonding & rapport" },
  { id: "motion", label: "Motion", icon: Move3d, desc: "Idle & animations" },
  { id: "camera", label: "Camera", icon: Camera, desc: "FOV, angle & distance" },
  { id: "actions", label: "Actions", icon: Zap, desc: "Triggers & responses" },
  { id: "finetuning", label: "Fine Tuning", icon: Sliders, desc: "Model params & data" },
  { id: "testing", label: "Testing", icon: FlaskConical, desc: "Test & validate" },
  { id: "preview", label: "Preview", icon: Monitor, desc: "3D view & display" },
  { id: "deploy", label: "Deploy", icon: Rocket, desc: "Publish & go live" },
]

export default function StudioPage() {
  const searchParams = useSearchParams()
  const [activeTab, setActiveTab] = useState("appearance")
  const [avatarId, setAvatarId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [saveStatus, setSaveStatus] = useState<"idle" | "saved" | "error">("idle")

  // Load existing avatar if ?id= param is present
  useEffect(() => {
    const idFromUrl = searchParams.get("id")
    if (!idFromUrl) return
    const loadId: string = idFromUrl
    setAvatarId(loadId)

    async function loadAvatar() {
      try {
        setLoading(true)
        // Try digital twins API first, fall back to digital humans
        let avatar: any = null
        try {
          avatar = await digitalTwinApi.get(loadId)
        } catch {
          try {
            avatar = await digitalHumanApi.get(loadId)
          } catch {}
        }
        if (avatar) {
          // Pre-fill tab fields with avatar data
          // (individual tab components will read from a shared state in a future iteration)
          console.log("Loaded avatar:", avatar.name)
        }
      } catch {
        console.error("Failed to load avatar")
      } finally {
        setLoading(false)
      }
    }
    loadAvatar()
  }, [searchParams])

  const handleSave = async () => {
    try {
      setSaving(true)
      setSaveStatus("idle")
      const data = {
        name: "My Avatar",
        description: "Created in Avatar Studio",
        style: "realistic",
      }
      if (avatarId) {
        await digitalTwinApi.update(avatarId, data)
      } else {
        const result = await digitalTwinApi.create(data)
        setAvatarId(result.id || result._id)
      }
      setSaveStatus("saved")
      setTimeout(() => setSaveStatus("idle"), 3000)
    } catch (err) {
      console.error("Save failed:", err)
      setSaveStatus("error")
      setTimeout(() => setSaveStatus("idle"), 3000)
    } finally {
      setSaving(false)
    }
  }

  const handleDeploy = async () => {
    if (!avatarId) {
      // Save first, then deploy
      await handleSave()
    }
    if (!avatarId) return
    try {
      setPublishing(true)
      await digitalTwinApi.publish(avatarId)
    } catch (err) {
      console.error("Deploy failed:", err)
    } finally {
      setPublishing(false)
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* ─── Header ─── */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div>
          <h1 className="text-xl font-bold text-foreground">Avatar Studio</h1>
          <p className="text-sm text-foreground-muted mt-0.5">Design, train, and deploy your digital human</p>
        </div>
        <div className="flex items-center gap-2">
          {loading && (
            <div className="flex items-center gap-2 text-xs text-foreground-muted">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Loading...
            </div>
          )}
          {saveStatus === "saved" && (
            <span className="flex items-center gap-1 text-xs text-[#A2AB73]">
              <Check className="h-3 w-3" />
              Saved
            </span>
          )}
          {saveStatus === "error" && (
            <span className="flex items-center gap-1 text-xs text-[#D84C63]">Save failed</span>
          )}
          <button
            onClick={handleSave}
            disabled={saving || loading}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-xs text-foreground-muted hover:text-foreground hover:bg-white/[0.08] transition-all disabled:opacity-50"
          >
            {saving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Save className="h-3.5 w-3.5" />
            )}
            {saving ? "Saving..." : "Save Draft"}
          </button>
          <button
            onClick={handleDeploy}
            disabled={publishing || loading}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-white text-xs font-medium shadow-lg shadow-[#CC3A63]/20 hover:shadow-[#CC3A63]/30 transition-all disabled:opacity-50"
          >
            {publishing ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Rocket className="h-3.5 w-3.5" />
            )}
            {publishing ? "Publishing..." : (avatarId ? "Update & Deploy" : "Save & Deploy")}
          </button>
        </div>
      </div>

      {/* ─── Main Content ─── */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Left: Vertical Tab Bar */}
        <div className="w-[180px] shrink-0 overflow-y-auto rounded-xl bg-card/80 border border-white/[0.06] p-1.5 space-y-0.5 scrollbar-thin">
          {STUDIO_TABS.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "w-full text-left px-3 py-2.5 rounded-lg transition-all group",
                  isActive
                    ? "bg-[#CC3A63]/15 border border-[#CC3A63]/20"
                    : "hover:bg-white/[0.04] border border-transparent"
                )}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={cn("h-3.5 w-3.5 shrink-0", isActive ? "text-[#CC3A63]" : "text-foreground-muted group-hover:text-foreground-muted")} />
                  <div className="min-w-0">
                    <p className={cn("text-xs font-medium truncate", isActive ? "text-foreground" : "text-foreground-muted group-hover:text-foreground")}>
                      {tab.label}
                    </p>
                    <p className={cn("text-[9px] truncate", isActive ? "text-[#CC3A63]/60" : "text-foreground-muted")}>
                      {tab.desc}
                    </p>
                  </div>
                </div>
              </button>
            )
          })}
        </div>

        {/* Center: Tab Content Panel */}
        <div className="w-[400px] xl:w-[440px] shrink-0 overflow-y-auto rounded-xl bg-card/80 border border-white/[0.06] p-5 scrollbar-thin">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              transition={{ duration: 0.15 }}
            >
              {activeTab === "appearance" && <AppearanceTab />}
              {activeTab === "voice" && <VoiceTab />}
              {activeTab === "personality" && <PersonalityTab />}
              {activeTab === "knowledge" && <KnowledgeTab />}
              {activeTab === "memory" && <MemoryTab />}
              {activeTab === "emotion" && <EmotionTab />}
              {activeTab === "expressions" && <ExpressionsTab />}
              {activeTab === "relationships" && <RelationshipsTab />}
              {activeTab === "motion" && <MotionTab />}
              {activeTab === "camera" && <CameraTab />}
              {activeTab === "actions" && <ActionsTab />}
              {activeTab === "finetuning" && <FineTuningTab />}
              {activeTab === "testing" && <TestingTab />}
              {activeTab === "preview" && <PreviewTab />}
              {activeTab === "deploy" && <DeployTab />}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Right: 3D Preview */}
        <div className="flex-1 rounded-xl bg-gradient-to-br from-[#2C2929] to-[#0a0e1a] border border-white/[0.06] flex items-center justify-center relative overflow-hidden">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 rounded-full bg-[#CC3A63]/8 blur-[100px]" />

          <div className="relative text-center">
            <div className="w-28 h-28 mx-auto mb-4 rounded-full bg-gradient-to-br from-[#CC3A63]/20 to-[#A2AB73]/20 border border-white/[0.06] flex items-center justify-center">
              <div className="w-14 h-14 rounded-full bg-gradient-to-br from-[#CC3A63] to-[#A2AB73] opacity-60 animate-breathe" />
            </div>
            <p className="text-sm text-foreground-muted">3D Preview</p>
            <p className="text-xs text-foreground-muted mt-1">Avatar will appear here</p>
          </div>

          {/* Bottom toolbar */}
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 px-3 py-2 rounded-xl bg-card/80 border border-white/[0.06]">
            <button className="px-3 py-1.5 rounded-lg bg-white/[0.04] text-xs text-foreground-muted hover:text-foreground transition-all">Reset</button>
            <div className="w-px h-4 bg-white/[0.06]" />
            <button className="px-3 py-1.5 rounded-lg bg-white/[0.04] text-xs text-foreground-muted hover:text-foreground transition-all">Auto-rotate</button>
            <div className="w-px h-4 bg-white/[0.06]" />
            <button className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-xs text-white font-medium shadow-lg shadow-[#CC3A63]/20">
              <Play className="h-3 w-3" />
              Preview
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ════════════════════════════════════════════════════════════════
   TAB COMPONENTS
   ════════════════════════════════════════════════════════════════ */

/* ─── APPEARANCE ─── */
function AppearanceTab() {
  return (
    <TabShell title="Appearance" desc="Name, style, and visual identity">
      <div className="space-y-3">
        <Field label="Avatar Name">
          <input type="text" placeholder="Enter name..." className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-[#CC3A63]/30" />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Gender">
            <select className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-foreground [&>option]:text-[#2C2929]">
              <option>Neutral</option>
              <option>Male</option>
              <option>Female</option>
            </select>
          </Field>
          <Field label="Age">
            <input type="number" min={18} max={80} defaultValue={30} className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-[#CC3A63]/30" />
          </Field>
        </div>
        <Field label="Style">
          <div className="grid grid-cols-3 gap-2">
            {["Realistic", "Stylized", "Cartoon"].map((s) => (
              <button key={s} className="px-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-xs text-foreground-muted hover:text-foreground hover:bg-[#CC3A63]/10 transition-all">{s}</button>
            ))}
          </div>
        </Field>
        <Field label="Color Scheme">
          <div className="flex flex-wrap gap-2">
            {["#CC3A63", "#A2AB73", "#A2AB73", "#CC3A63", "#D6A44C", "#D84C63"].map((c) => (
              <button key={c} className="w-7 h-7 rounded-lg border border-white/[0.1] hover:scale-110 transition-transform" style={{ background: c }} />
            ))}
          </div>
        </Field>
      </div>
    </TabShell>
  )
}

/* ─── VOICE ─── */
function VoiceTab() {
  const [selectedVoice, setSelectedVoice] = useState("natural-female")
  const voices = [
    { id: "natural-female", label: "Natural Female", lang: "EN" },
    { id: "natural-male", label: "Natural Male", lang: "EN" },
    { id: "warm-female", label: "Warm Female", lang: "EN" },
    { id: "deep-male", label: "Deep Male", lang: "EN" },
  ]
  return (
    <TabShell title="Voice" desc="Speech synthesis and vocal identity">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Language">
            <select className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-foreground [&>option]:text-[#2C2929]">
              <option>English</option>
              <option>Spanish</option>
              <option>French</option>
              <option>Hindi</option>
              <option>Tamil</option>
            </select>
          </Field>
          <Field label="Accent">
            <select className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-foreground [&>option]:text-[#2C2929]">
              <option>American</option>
              <option>British</option>
              <option>Indian</option>
              <option>Australian</option>
            </select>
          </Field>
        </div>
        <Field label="Voice Model">
          <div className="space-y-1.5">
            {voices.map((v) => (
              <button
                key={v.id}
                onClick={() => setSelectedVoice(v.id)}
                className={cn(
                  "w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs transition-all",
                  selectedVoice === v.id
                    ? "bg-[#CC3A63]/15 border border-[#CC3A63]/20 text-foreground"
                    : "bg-white/[0.04] border border-white/[0.06] text-foreground-muted hover:text-foreground"
                )}
              >
                <span>{v.label}</span>
                <div className="flex items-center gap-2">
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/[0.04]">{v.lang}</span>
                  {selectedVoice === v.id && <Check className="h-3 w-3 text-[#CC3A63]" />}
                </div>
              </button>
            ))}
          </div>
        </Field>
        <div className="flex items-center gap-2 pt-1">
          <button className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-xs text-foreground-muted hover:text-foreground transition-all">
            <Play className="h-3 w-3" />
            Test Voice
          </button>
          <button className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-xs text-foreground-muted hover:text-foreground transition-all">
            <Upload className="h-3 w-3" />
            Upload Sample
          </button>
        </div>
      </div>
    </TabShell>
  )
}

/* ─── PERSONALITY ─── */
function PersonalityTab() {
  const [traits, setTraits] = useState(["Empathetic", "Professional"])
  const allTraits = ["Empathetic", "Professional", "Creative", "Analytical", "Warm", "Energetic", "Calm", "Witty", "Supportive", "Curious"]
  return (
    <TabShell title="Personality" desc="Behavioral traits and identity">
      <div className="space-y-3">
        <Field label="Traits">
          <div className="flex flex-wrap gap-1.5">
            {allTraits.map((t) => {
              const isSelected = traits.includes(t)
              return (
                <button
                  key={t}
                  onClick={() => setTraits(isSelected ? traits.filter(x => x !== t) : [...traits, t])}
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-xs transition-all border",
                    isSelected
                      ? "bg-[#CC3A63]/15 border-[#CC3A63]/20 text-foreground"
                      : "bg-white/[0.04] border-white/[0.06] text-foreground-muted hover:text-foreground"
                  )}
                >
                  {t}
                </button>
              )
            })}
          </div>
        </Field>
        <Field label="Description">
          <textarea rows={3} placeholder="Describe how your avatar should behave..." className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-[#CC3A63]/30 resize-none" />
        </Field>
        <Field label="Interaction Style">
          <select className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-foreground [&>option]:text-[#2C2929]">
            <option>Friendly & Casual</option>
            <option>Professional & Formal</option>
            <option>Academic & Detailed</option>
            <option>Creative & Playful</option>
            <option>Supportive & Empathetic</option>
          </select>
        </Field>
      </div>
    </TabShell>
  )
}

/* ─── KNOWLEDGE ─── */
function KnowledgeTab() {
  const sources = [
    { name: "medical_reference.pdf", size: "2.4 MB", status: "synced", chunks: 128 },
    { name: "company_policies.docx", size: "1.1 MB", status: "synced", chunks: 64 },
    { name: "product_catalog.csv", size: "0.8 MB", status: "processing", chunks: 42 },
  ]
  return (
    <TabShell title="Knowledge" desc="Documents, data sources, and training material">
      <div className="space-y-3">
        <button className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border-2 border-dashed border-white/[0.08] text-xs text-foreground-muted hover:text-foreground-muted hover:border-[#CC3A63]/30 hover:bg-[#CC3A63]/5 transition-all">
          <Upload className="h-4 w-4" />
          Upload Documents
        </button>
        <div className="space-y-1.5">
          {sources.map((src) => (
            <div key={src.name} className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06]">
              <div className="min-w-0">
                <p className="text-xs text-foreground truncate">{src.name}</p>
                <p className="text-[10px] text-foreground-muted">{src.size} · {src.chunks} chunks</p>
              </div>
              <div className={cn(
                "px-1.5 py-0.5 rounded text-[9px] font-medium",
                src.status === "synced" ? "bg-[#A2AB73]/10 text-[#A2AB73]" : "bg-[#D6A44C]/10 text-[#D6A44C]"
              )}>
                {src.status}
              </div>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-foreground-muted pt-1">
          <RefreshCw className="h-3 w-3" />
          Auto-sync enabled · Updates every 24h
        </div>
      </div>
    </TabShell>
  )
}

/* ─── MEMORY ─── */
function MemoryTab() {
  return (
    <TabShell title="Memory" desc="Retention, context, and recall settings">
      <div className="space-y-3">
        <SliderField label="Context Window" value={8} max={32} unit="K tokens" />
        <SliderField label="Memory Retention" value={85} unit="%" />
        <SliderField label="Long-term Recall" value={70} unit="%" />
        <Field label="Memory Types">
          <div className="space-y-1.5">
            {[
              { id: "conversation", label: "Conversation History", on: true },
              { id: "preferences", label: "User Preferences", on: true },
              { id: "facts", label: "Learned Facts", on: true },
              { id: "emotions", label: "Emotional Context", on: false },
            ].map((m) => (
              <div key={m.id} className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/[0.03]">
                <span className="text-xs text-foreground-muted">{m.label}</span>
                <div className={cn("w-8 h-4 rounded-full transition-colors relative cursor-pointer", m.on ? "bg-[#CC3A63]" : "bg-white/[0.08]")}>
                  <div className={cn("absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform", m.on ? "left-4" : "left-0.5")} />
                </div>
              </div>
            ))}
          </div>
        </Field>
      </div>
    </TabShell>
  )
}

/* ─── EMOTION ─── */
function EmotionTab() {
  return (
    <TabShell title="Emotion" desc="Emotional range, sensitivity, and expression intensity">
      <div className="space-y-3">
        <SliderField label="Emotional Range" value={80} unit="%" />
        <SliderField label="Sensitivity" value={65} unit="%" />
        <SliderField label="Expression Intensity" value={70} unit="%" />
        <SliderField label="Recovery Speed" value={50} unit="%" />
        <Field label="Base Emotion">
          <select className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-foreground [&>option]:text-[#2C2929]">
            <option>Calm</option>
            <option>Neutral</option>
            <option>Friendly</option>
            <option>Enthusiastic</option>
          </select>
        </Field>
      </div>
    </TabShell>
  )
}

/* ─── EXPRESSIONS ─── */
function ExpressionsTab() {
  const exprs = [
    { name: "Smile", shortcut: "S" },
    { name: "Frown", shortcut: "F" },
    { name: "Surprise", shortcut: "U" },
    { name: "Nod", shortcut: "N" },
    { name: "Tilt", shortcut: "T" },
    { name: "Wink", shortcut: "W" },
  ]
  return (
    <TabShell title="Expressions" desc="Facial expressions and gesture animations">
      <div className="space-y-3">
        <Field label="Default Expression">
          <select className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-foreground [&>option]:text-[#2C2929]">
            <option>Neutral</option>
            <option>Gentle Smile</option>
            <option>Friendly</option>
          </select>
        </Field>
        <SliderField label="Blink Frequency" value={8} max={20} unit="s" />
        <SliderField label="Expression Speed" value={60} unit="%" />
        <Field label="Triggered Expressions">
          <div className="grid grid-cols-2 gap-1.5">
            {exprs.map((e) => (
              <div key={e.name} className="flex items-center justify-between px-2.5 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                <span className="text-xs text-foreground-muted">{e.name}</span>
                <span className="text-[9px] px-1 py-0.5 rounded bg-white/[0.04] text-foreground-muted">{e.shortcut}</span>
              </div>
            ))}
          </div>
        </Field>
      </div>
    </TabShell>
  )
}

/* ─── RELATIONSHIPS ─── */
function RelationshipsTab() {
  const [bondLevel, setBondLevel] = useState(65)
  return (
    <TabShell title="Relationships" desc="Bonding, rapport, and interaction dynamics">
      <div className="space-y-3">
        <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4 text-center">
          <div className="text-3xl font-bold text-[#CC3A63] mb-1">{bondLevel}%</div>
          <p className="text-xs text-foreground-muted">Current Bond Level</p>
          <input type="range" min={0} max={100} value={bondLevel} onChange={(e) => setBondLevel(Number(e.target.value))} className="w-full mt-2 accent-[#CC3A63]" />
        </div>
        <Field label="Bonding Speed">
          <select className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-foreground [&>option]:text-[#2C2929]">
            <option>Slow & Natural</option>
            <option>Balanced</option>
            <option>Fast & Warm</option>
          </select>
        </Field>
        <Field label="Interaction History">
          <div className="space-y-1.5">
            {[
              { type: "Conversations", count: 47 },
              { type: "Shared Memories", count: 12 },
              { type: "Inside Jokes", count: 3 },
              { type: "Milestones", count: 2 },
            ].map((item) => (
              <div key={item.type} className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/[0.03]">
                <span className="text-xs text-foreground-muted">{item.type}</span>
                <span className="text-xs font-medium text-foreground">{item.count}</span>
              </div>
            ))}
          </div>
        </Field>
      </div>
    </TabShell>
  )
}

/* ─── MOTION ─── */
function MotionTab() {
  return (
    <TabShell title="Motion" desc="Idle animations, movement style, and body language">
      <div className="space-y-3">
        <Field label="Idle Animation">
          <select className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-foreground [&>option]:text-[#2C2929]">
            <option>Gentle Breathing</option>
            <option>Standing Still</option>
            <option>Subtle Sway</option>
            <option>Looking Around</option>
          </select>
        </Field>
        <SliderField label="Gesture Frequency" value={60} unit="%" />
        <SliderField label="Animation Speed" value={50} unit="%" />
        <SliderField label="Movement Range" value={40} unit="%" />
        <Field label="Gestures">
          <div className="flex flex-wrap gap-1.5">
            {["Hand Wave", "Nod", "Point", "Shrug", "Lean In", "Cross Arms"].map((g) => (
              <button key={g} className="px-2.5 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.06] text-[10px] text-foreground-muted hover:text-foreground transition-all">{g}</button>
            ))}
          </div>
        </Field>
      </div>
    </TabShell>
  )
}

/* ─── CAMERA ─── */
function CameraTab() {
  return (
    <TabShell title="Camera" desc="Field of view, angle, and positioning">
      <div className="space-y-3">
        <SliderField label="Field of View" value={50} min={20} max={120} unit="°" />
        <SliderField label="Camera Distance" value={3.2} min={1} max={8} step={0.1} unit="m" />
        <SliderField label="Camera Height" value={1.6} min={0.5} max={3} step={0.1} unit="m" />
        <Field label="Camera Angle">
          <div className="grid grid-cols-3 gap-2">
            {["Front", "Three-Quarter", "Side", "Low Angle", "Eye Level", "High Angle"].map((a) => (
              <button key={a} className="px-2.5 py-2 rounded-lg bg-white/[0.04] border border-white/[0.06] text-[10px] text-foreground-muted hover:text-foreground hover:bg-[#CC3A63]/10 transition-all">{a}</button>
            ))}
          </div>
        </Field>
        <label className="flex items-center gap-2 text-xs text-foreground-muted">
          <input type="checkbox" defaultChecked className="accent-[#CC3A63]" />
          Enable Auto-rotate
        </label>
      </div>
    </TabShell>
  )
}

/* ─── ACTIONS ─── */
function ActionsTab() {
  const [actionsList, setActionsList] = useState([
    { trigger: "User says 'hello'", response: "Greet user warmly", active: true },
    { trigger: "User asks for help", response: "Offer assistance", active: true },
    { trigger: "User seems sad", response: "Show empathy and support", active: false },
  ])
  return (
    <TabShell title="Actions" desc="Custom triggers, responses, and automated behaviors">
      <div className="space-y-3">
        <button className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border-2 border-dashed border-white/[0.08] text-xs text-foreground-muted hover:text-foreground-muted hover:border-[#CC3A63]/30 transition-all">
          <Plus className="h-3.5 w-3.5" />
          Add Action
        </button>
        <div className="space-y-1.5">
          {actionsList.map((action, i) => (
            <div key={i} className="flex items-center gap-2 px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06]">
              <GripVertical className="h-3 w-3 text-foreground-muted shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-[11px] text-foreground truncate">{action.trigger}</p>
                <p className="text-[9px] text-foreground-muted truncate">→ {action.response}</p>
              </div>
              <div className={cn("w-7 h-3.5 rounded-full transition-colors relative cursor-pointer shrink-0", action.active ? "bg-[#CC3A63]" : "bg-white/[0.08]")}>
                <div className={cn("absolute top-0.5 w-2.5 h-2.5 rounded-full bg-white transition-transform", action.active ? "left-4" : "left-0.5")} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </TabShell>
  )
}

/* ─── FINE TUNING ─── */
function FineTuningTab() {
  return (
    <TabShell title="Fine Tuning" desc="Model parameters, training data, and optimization">
      <div className="space-y-3">
        <Field label="Base Model">
          <select className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-foreground [&>option]:text-[#2C2929]">
            <option>GPT-4o</option>
            <option>Claude 3.5 Sonnet</option>
            <option>Gemini 1.5 Pro</option>
            <option>Llama 3.1 70B</option>
          </select>
        </Field>
        <SliderField label="Temperature" value={0.7} min={0} max={2} step={0.1} unit="" />
        <SliderField label="Top P" value={0.9} min={0} max={1} step={0.1} unit="" />
        <SliderField label="Max Tokens" value={2048} min={256} max={8192} step={256} unit="" />
        <Field label="Training Data">
          <div className="px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06]">
            <p className="text-xs text-foreground-muted">No custom training data uploaded</p>
            <button className="mt-2 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#CC3A63]/10 border border-[#CC3A63]/20 text-xs text-[#CC3A63] hover:bg-[#CC3A63]/20 transition-all">
              <Upload className="h-3 w-3" />
              Upload Dataset
            </button>
          </div>
        </Field>
      </div>
    </TabShell>
  )
}

/* ─── TESTING ─── */
function TestingTab() {
  const [testInput, setTestInput] = useState("")
  const testResults = [
    { type: "voice", label: "Voice Test", status: "passed" as const },
    { type: "emotion", label: "Emotion Response", status: "passed" as const },
    { type: "knowledge", label: "Knowledge Retrieval", status: "pending" as const },
    { type: "motion", label: "Motion Sync", status: "failed" as const },
  ]
  return (
    <TabShell title="Testing" desc="Validate and preview avatar behavior">
      <div className="space-y-3">
        <Field label="Test Conversation">
          <div className="space-y-2">
            <input
              type="text"
              value={testInput}
              onChange={(e) => setTestInput(e.target.value)}
              placeholder="Type a test message..."
              className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-[#CC3A63]/30"
            />
            <div className="flex gap-2">
              <button disabled={!testInput.trim()} className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-xs text-white font-medium disabled:opacity-50 transition-all">
                <Play className="h-3 w-3" />
                Send
              </button>
              <button className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-xs text-foreground-muted hover:text-foreground transition-all">
                <RefreshCw className="h-3 w-3" />
                Reset
              </button>
            </div>
          </div>
        </Field>
        <Field label="Validation Results">
          <div className="space-y-1.5">
            {testResults.map((r) => (
              <div key={r.type} className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                <span className="text-xs text-foreground-muted">{r.label}</span>
                <span className={cn(
                  "text-[10px] font-medium",
                  r.status === "passed" ? "text-[#A2AB73]" : r.status === "failed" ? "text-[#D84C63]" : "text-[#D6A44C]"
                )}>
                  {r.status === "passed" ? "✓ Passed" : r.status === "failed" ? "✗ Failed" : "○ Pending"}
                </span>
              </div>
            ))}
          </div>
        </Field>
        <button className="w-full flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-gradient-to-r from-[#A2AB73]/20 to-[#A2AB73]/10 border border-[#A2AB73]/20 text-xs text-[#A2AB73] font-medium hover:from-[#A2AB73]/30 transition-all">
          <FlaskConical className="h-3.5 w-3.5" />
          Run All Tests
        </button>
      </div>
    </TabShell>
  )
}

/* ─── PREVIEW ─── */
function PreviewTab() {
  return (
    <TabShell title="Preview" desc="3D view settings, display options, and avatar pose">
      <div className="space-y-3">
        <Field label="Default Pose">
          <div className="grid grid-cols-3 gap-2">
            {["Standing", "Sitting", "Casual"].map((pose) => (
              <button
                key={pose}
                className="px-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-xs text-foreground-muted hover:text-foreground hover:bg-[#CC3A63]/10 transition-all"
              >
                {pose}
              </button>
            ))}
          </div>
        </Field>
        <Field label="Background">
          <div className="grid grid-cols-4 gap-2">
            {["#2C2929", "#1a1f35", "#8F9A5E", "#CC3A63"].map((bg) => (
              <button
                key={bg}
                className="aspect-video rounded-lg border border-white/[0.1] hover:scale-105 transition-transform"
                style={{ background: bg }}
              />
            ))}
          </div>
        </Field>
        <label className="flex items-center gap-2 text-xs text-foreground-muted">
          <input type="checkbox" defaultChecked className="accent-[#CC3A63]" />
          Show emotion overlay
        </label>
        <label className="flex items-center gap-2 text-xs text-foreground-muted">
          <input type="checkbox" defaultChecked className="accent-[#CC3A63]" />
          Show speaking indicator
        </label>
        <SliderField label="Preview Quality" value={80} unit="%" />
      </div>
    </TabShell>
  )
}

/* ─── DEPLOY ─── */
function DeployTab() {
  return (
    <TabShell title="Deploy" desc="Publish, environments, and versioning">
      <div className="space-y-3">
        <Field label="Environment">
          <div className="grid grid-cols-3 gap-2">
            {[
              { id: "dev", label: "Development", color: "#D6A44C" },
              { id: "staging", label: "Staging", color: "#A2AB73" },
              { id: "prod", label: "Production", color: "#A2AB73" },
            ].map((env) => (
              <button key={env.id} className="flex flex-col items-center gap-1 px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] hover:bg-[#CC3A63]/10 transition-all">
                <div className="w-2 h-2 rounded-full" style={{ background: env.color }} />
                <span className="text-[10px] text-foreground-muted">{env.label}</span>
              </button>
            ))}
          </div>
        </Field>
        <Field label="Version">
          <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06]">
            <span className="text-xs text-foreground font-mono">v1.0.0</span>
            <button className="text-[10px] text-[#CC3A63] hover:text-foreground transition-all">Change</button>
          </div>
        </Field>
        <Field label="Publishing Checklist">
          <div className="space-y-1.5">
            {[
              { item: "Appearance configured", done: true },
              { item: "Voice model selected", done: true },
              { item: "Knowledge sources synced", done: true },
              { item: "Personality traits defined", done: true },
              { item: "Tests passed", done: false },
            ].map((c) => (
              <div key={c.item} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.03]">
                <div className={cn("w-3.5 h-3.5 rounded border flex items-center justify-center", c.done ? "bg-[#A2AB73] border-[#A2AB73]" : "border-white/[0.12]")}>
                  {c.done && <Check className="h-2.5 w-2.5 text-[#2C2929]" />}
                </div>
                <span className={cn("text-[11px]", c.done ? "text-foreground" : "text-foreground-muted")}>{c.item}</span>
              </div>
            ))}
          </div>
        </Field>
        <button className="w-full flex items-center justify-center gap-1.5 py-3 rounded-xl bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-white text-sm font-medium shadow-lg shadow-[#CC3A63]/20 hover:shadow-[#CC3A63]/30 transition-all">
          <Rocket className="h-4 w-4" />
          Publish to Production
        </button>
      </div>
    </TabShell>
  )
}

/* ════════════════════════════════════════════════════════════════
   HELPER COMPONENTS
   ════════════════════════════════════════════════════════════════ */

function TabShell({ title, desc, children }: { title: string; desc: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-sm font-bold text-foreground mb-0.5">{title}</h3>
      <p className="text-[11px] text-foreground-muted mb-4">{desc}</p>
      {children}
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-[11px] text-foreground-muted mb-1.5 block font-medium">{label}</label>
      {children}
    </div>
  )
}

function SliderField({ label, value, min = 0, max = 100, step, unit }: {
  label: string
  value: number
  min?: number
  max?: number
  step?: number
  unit?: string
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-[11px] text-foreground-muted font-medium">{label}</label>
        <span className="text-xs text-foreground font-medium">
          {value}{unit ? ` ${unit}` : ""}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step ?? 1}
        defaultValue={value}
        className="w-full accent-[#CC3A63]"
      />
    </div>
  )
}
