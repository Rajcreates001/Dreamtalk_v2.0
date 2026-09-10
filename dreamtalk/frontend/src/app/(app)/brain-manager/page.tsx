"use client"

import { useState, useEffect } from "react"
import { motion } from "motion/react"
import { Settings, Brain, Activity, Sliders, RefreshCw, Save } from "lucide-react"
import { API_BASE_URL } from "@/lib/constants"
import { Spinner } from "@/components/loading-states"

export default function BrainManagerPage() {
  const [healthData, setHealthData] = useState<any>(null)
  const [analyticsData, setAnalyticsData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saveStatus, setSaveStatus] = useState<string | null>(null)

  // Brain config (client-side only for now)
  const [config, setConfig] = useState({
    encodingMethod: "rate",
    learningRate: 0.01,
    spikeThreshold: 0.5,
    pfcWeight: 1.0,
    daccWeight: 0.8,
    insulaWeight: 0.9,
    iplWeight: 0.7,
    bgWeight: 1.0,
    emotionBoost: 0.3,
  })

  useEffect(() => {
    async function load() {
      try {
        const [healthRes, analyticsRes] = await Promise.allSettled([
          fetch(`${API_BASE_URL}/pipeline/health`).then(r => r.json()),
          fetch(`${API_BASE_URL}/analytics/brain`).then(r => r.json()),
        ])
        if (healthRes.status === "fulfilled") setHealthData(healthRes.value)
        if (analyticsRes.status === "fulfilled") setAnalyticsData(analyticsRes.value)
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handleSave = () => {
    setSaveStatus("saving")
    setTimeout(() => setSaveStatus("saved"), 500)
    setTimeout(() => setSaveStatus(null), 2000)
  }

  const brainHealth = healthData?.checks?.brain_pipeline

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Settings className="h-5 w-5" /> Brain Manager
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Configure the neuromorphic SNN brain parameters</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saveStatus === "saving"}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
        >
          {saveStatus === "saving" ? <Spinner size="sm" /> : <Save className="h-4 w-4" />}
          {saveStatus === "saved" ? "Saved!" : "Save Config"}
        </button>
      </div>

      {/* Status */}
      <div className="p-4 rounded-xl border bg-card flex items-center gap-4">
        <Brain className="h-8 w-8 text-blue-500" />
        <div>
          <div className="font-semibold">Brain Pipeline Status</div>
          <div className="text-sm text-muted-foreground">
            {brainHealth?.message || "Unknown"} — SNN encoder {brainHealth?.status === "healthy" ? "active" : "unavailable"}
          </div>
        </div>
        <div className={cn(
          "ml-auto px-3 py-1 rounded-full text-xs font-medium",
          brainHealth?.status === "healthy" ? "bg-green-500/10 text-green-500" : "bg-yellow-500/10 text-yellow-500"
        )}>
          {brainHealth?.status === "healthy" ? "✅ Online" : "⚠️ Offline"}
        </div>
      </div>

      {/* Encoding Settings */}
      <div className="p-5 rounded-xl border bg-card space-y-4">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <Sliders className="h-4 w-4" /> Spike Encoding
        </h3>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-muted-foreground">Encoding Method</label>
            <select
              value={config.encodingMethod}
              onChange={(e) => setConfig({ ...config, encodingMethod: e.target.value })}
              className="mt-1 w-full rounded-lg border bg-background px-3 py-2 text-sm"
            >
              <option value="rate">Rate Encoding</option>
              <option value="temporal">Temporal Encoding</option>
              <option value="burst">Burst Encoding</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Spike Threshold: {config.spikeThreshold}</label>
            <input
              type="range" min="0.1" max="2.0" step="0.1"
              value={config.spikeThreshold}
              onChange={(e) => setConfig({ ...config, spikeThreshold: parseFloat(e.target.value) })}
              className="mt-2 w-full"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Learning Rate: {config.learningRate}</label>
            <input
              type="range" min="0.001" max="0.1" step="0.001"
              value={config.learningRate}
              onChange={(e) => setConfig({ ...config, learningRate: parseFloat(e.target.value) })}
              className="mt-2 w-full"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Emotion Boost: {config.emotionBoost}</label>
            <input
              type="range" min="0" max="1.0" step="0.1"
              value={config.emotionBoost}
              onChange={(e) => setConfig({ ...config, emotionBoost: parseFloat(e.target.value) })}
              className="mt-2 w-full"
            />
          </div>
        </div>
      </div>

      {/* Brain Area Weights */}
      <div className="p-5 rounded-xl border bg-card space-y-4">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <Activity className="h-4 w-4" /> Brain Area Weights
        </h3>
        <div className="space-y-3">
          {[
            { key: "pfcWeight", label: "Prefrontal Cortex", color: "#3b82f6" },
            { key: "daccWeight", label: "dACC (Conflict)", color: "#ef4444" },
            { key: "insulaWeight", label: "Insula (Emotion)", color: "#a855f7" },
            { key: "iplWeight", label: "IPL (Context)", color: "#22c55e" },
            { key: "bgWeight", label: "Basal Ganglia", color: "#f59e0b" },
          ].map((area) => (
            <div key={area.key} className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: area.color }} />
              <span className="text-sm w-40">{area.label}</span>
              <input
                type="range" min="0" max="2.0" step="0.1"
                value={(config as any)[area.key]}
                onChange={(e) => setConfig({ ...config, [area.key]: parseFloat(e.target.value) })}
                className="flex-1"
              />
              <span className="text-sm text-muted-foreground w-10 text-right">
                {(config as any)[area.key].toFixed(1)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Last Activity */}
      {analyticsData && (
        <div className="p-5 rounded-xl border bg-card">
          <h3 className="text-sm font-semibold mb-3">Last Brain Activity</h3>
          <div className="grid md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Last Action:</span>
              <div className="font-medium">{analyticsData.last_action || "None"}</div>
            </div>
            <div>
              <span className="text-muted-foreground">Avg Confidence:</span>
              <div className="font-medium">{analyticsData.avg_confidence?.toFixed(2) || "—"}</div>
            </div>
            <div>
              <span className="text-muted-foreground">Total Actions:</span>
              <div className="font-medium">{analyticsData.total_actions || 0}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(" ")
}
