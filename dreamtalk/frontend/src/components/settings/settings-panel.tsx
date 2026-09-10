"use client"

import React, { useState } from "react"
import { motion } from "motion/react"
import { Brain, Mic, Volume2, Sliders, RefreshCw } from "lucide-react"
import { ModelSelector } from "./model-selector"
import { BlurFade } from "@/components/magic/blur-fade"
import { cn } from "@/lib/utils"
import { LLM_MODELS, VOICE_MODELS } from "@/lib/constants"

const TTS_MODELS = [
  { id: "gpt-sovits", name: "GPT-SoVITS", provider: "Local GPU" },
  { id: "openvoice", name: "OpenVoice", provider: "Local GPU" },
  { id: "chattts", name: "ChatTTS", provider: "Local GPU" },
  { id: "fish-speech", name: "Fish Speech", provider: "Local GPU" },
  { id: "edge-tts", name: "Edge TTS", provider: "Cloud" },
  { id: "elevenlabs", name: "ElevenLabs", provider: "Cloud API" },
] as const

const VOICE_OPTIONS = [
  { id: "default-female", name: "Aria (Female)", provider: "Default" },
  { id: "default-male", name: "Orion (Male)", provider: "Default" },
  { id: "soft-female", name: "Luna (Soft)", provider: "Default" },
  { id: "warm-male", name: "Atlas (Warm)", provider: "Default" },
] as const

const PERSONA_OPTIONS = [
  { id: "dr-aria", name: "Dr. Aria", provider: "Health Companion" },
  { id: "orion", name: "Orion", provider: "General Assistant" },
  { id: "sage", name: "Sage", provider: "Academic Tutor" },
  { id: "nova", name: "Nova", provider: "Creative Partner" },
] as const

type SettingsTab = "models" | "voice" | "persona" | "system"

const tabs: { id: SettingsTab; label: string; icon: React.FC<{ className?: string }> }[] = [
  { id: "models", label: "AI Models", icon: Brain },
  { id: "voice", label: "Voice", icon: Mic },
  { id: "persona", label: "Persona", icon: Volume2 },
  { id: "system", label: "System", icon: Sliders },
]

export function SettingsPanel() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("models")

  const [llmModel, setLlmModel] = useState<string>(LLM_MODELS[0].id)
  const [ttsModel, setTtsModel] = useState<string>(TTS_MODELS[0].id)
  const [voiceId, setVoiceId] = useState<string>(VOICE_OPTIONS[0].id)
  const [personaId, setPersonaId] = useState<string>(PERSONA_OPTIONS[0].id)
  const [temperature, setTemperature] = useState(0.7)
  const [maxTokens, setMaxTokens] = useState(2048)

  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    await new Promise((r) => setTimeout(r, 800))
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleReset = () => {
    setLlmModel(LLM_MODELS[0].id)
    setTtsModel(TTS_MODELS[0].id)
    setVoiceId(VOICE_OPTIONS[0].id)
    setPersonaId(PERSONA_OPTIONS[0].id)
    setTemperature(0.7)
    setMaxTokens(2048)
  }

  const tabContent = {
    models: (
      <div className="space-y-8">
        <ModelSelector
          label="LLM Model"
          description="Language model powering conversations"
          options={LLM_MODELS}
          value={llmModel}
          onChange={setLlmModel}
          icon={<Brain className="h-4 w-4" />}
        />
        <ModelSelector
          label="TTS Engine"
          description="Text-to-speech synthesis backend"
          options={TTS_MODELS}
          value={ttsModel}
          onChange={setTtsModel}
          icon={<Volume2 className="h-4 w-4" />}
        />
      </div>
    ),
    voice: (
      <div className="space-y-8">
        <ModelSelector
          label="Voice Profile"
          description="Active voice for your AI companion"
          options={VOICE_OPTIONS}
          value={voiceId}
          onChange={setVoiceId}
          icon={<Mic className="h-4 w-4" />}
        />
        <div className="space-y-3">
          <h3 className="text-sm font-medium">Temperature</h3>
          <p className="text-xs text-muted-foreground">Controls response creativity (0 = precise, 1 = creative)</p>
          <div className="flex items-center gap-4">
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="flex-1 accent-emerald-500 h-1.5 rounded-full appearance-none bg-muted cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-emerald-500"
            />
            <span className="text-sm font-mono text-muted-foreground w-8 text-right">{temperature.toFixed(2)}</span>
          </div>
        </div>
        <div className="space-y-3">
          <h3 className="text-sm font-medium">Max Tokens</h3>
          <p className="text-xs text-muted-foreground">Maximum response length</p>
          <div className="flex items-center gap-4">
            <input
              type="range"
              min="256"
              max="8192"
              step="256"
              value={maxTokens}
              onChange={(e) => setMaxTokens(parseInt(e.target.value))}
              className="flex-1 accent-emerald-500 h-1.5 rounded-full appearance-none bg-muted cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-emerald-500"
            />
            <span className="text-sm font-mono text-muted-foreground w-14 text-right">{maxTokens}</span>
          </div>
        </div>
      </div>
    ),
    persona: (
      <div className="space-y-8">
        <ModelSelector
          label="AI Persona"
          description="Personality and expertise profile"
          options={PERSONA_OPTIONS}
          value={personaId}
          onChange={setPersonaId}
          icon={<Volume2 className="h-4 w-4" />}
        />
        {personaId === "dr-aria" && (
          <div className="rounded-xl bg-emerald-500/5 border border-emerald-500/10 p-4 space-y-2">
            <h4 className="text-sm font-medium text-emerald-400">Dr. Aria Profile</h4>
            <p className="text-xs text-muted-foreground leading-relaxed">
              A compassionate AI health companion specialized in medical information, wellness guidance,
              and emotional support. Trained on medical literature with a warm, empathetic communication style.
            </p>
          </div>
        )}
      </div>
    ),
    system: (
      <div className="space-y-8">
        <div className="rounded-xl bg-muted/20 border border-border/50 p-4 space-y-3">
          <h3 className="text-sm font-medium">System Status</h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            {[
              { label: "Backend", value: "Connected", ok: true },
              { label: "GPU Server", value: "Online", ok: true },
              { label: "Voice Engine", value: "Ready", ok: true },
              { label: "Memory Store", value: "Active", ok: true },
            ].map((s) => (
              <div key={s.label} className="flex items-center justify-between p-2 rounded-lg bg-background/50">
                <span className="text-muted-foreground text-xs">{s.label}</span>
                <span className={cn("flex items-center gap-1 text-xs", s.ok ? "text-emerald-400" : "text-red-400")}>
                  <span className={cn("h-1.5 w-1.5 rounded-full", s.ok ? "bg-emerald-500" : "bg-red-500")} />
                  {s.value}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-xl bg-muted/20 border border-border/50 p-4 space-y-3">
          <h3 className="text-sm font-medium">API Configuration</h3>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">API URL</span>
              <code className="text-foreground/80">http://localhost:5001</code>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">WebSocket</span>
              <code className="text-foreground/80">ws://localhost:5001/ws</code>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Model Cache</span>
              <code className="text-foreground/80">~/.dreamtalk/models</code>
            </div>
          </div>
        </div>
      </div>
    ),
  }

  return (
    <div className="max-w-4xl mx-auto">
      <BlurFade inView offset={10} blur="4px">
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
            <p className="text-sm text-muted-foreground mt-1">Configure your AI companion</p>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 rounded-xl bg-muted/30 border border-border/50 p-1">
        {tabs.map((tab) => {
          const Icon = tab.icon as React.ComponentType<{ className?: string }>
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
                activeTab === tab.id
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {React.createElement(Icon, { className: "h-4 w-4" })}
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          )
        })}
          </div>

          {/* Content */}
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="min-h-[300px]"
          >
            {tabContent[activeTab]}
          </motion.div>

          {/* Actions */}
          <div className="flex items-center justify-between pt-4 border-t border-border/50">
            <button
              type="button"
              onClick={handleReset}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm text-muted-foreground hover:text-foreground hover:bg-muted/30 transition-all"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Reset Defaults
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className={cn(
                "px-6 py-2 rounded-xl text-sm font-medium transition-all",
                saved
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                  : "bg-foreground text-background hover:opacity-90",
                saving && "opacity-50 cursor-not-allowed"
              )}
            >
              {saving ? "Saving..." : saved ? "Saved!" : "Save Settings"}
            </button>
          </div>
        </div>
      </BlurFade>
    </div>
  )
}
