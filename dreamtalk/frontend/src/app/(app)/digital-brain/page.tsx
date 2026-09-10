"use client"

import { useState, useEffect } from "react"
import { motion } from "motion/react"
import { Brain, Zap, Activity, Eye, Heart, AlertTriangle, RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"
import { API_BASE_URL } from "@/lib/constants"
import { BrainActivity } from "@/components/analytics/brain-activity"
import { Spinner } from "@/components/loading-states"

const BRAIN_AREAS = [
  { key: "pfc", name: "Prefrontal Cortex", icon: Brain, color: "#3b82f6", desc: "Executive function, response planning" },
  { key: "dacc", name: "dACC", icon: AlertTriangle, color: "#ef4444", desc: "Conflict monitoring, intent validation" },
  { key: "insula", name: "Insula", icon: Heart, color: "#a855f7", desc: "Emotion processing, interoception" },
  { key: "ipl", name: "IPL", icon: Eye, color: "#22c55e", desc: "Context integration, multimodal binding" },
  { key: "bg", name: "Basal Ganglia", icon: Zap, color: "#f59e0b", desc: "Action selection, response gating" },
]

export default function DigitalBrainPage() {
  const [brainData, setBrainData] = useState<any>(null)
  const [healthData, setHealthData] = useState<any>(null)
  const [testMessage, setTestMessage] = useState("")
  const [testResult, setTestResult] = useState<any>(null)
  const [testing, setTesting] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [brainRes, healthRes] = await Promise.allSettled([
          fetch(`${API_BASE_URL}/analytics/brain`).then(r => r.json()),
          fetch(`${API_BASE_URL}/pipeline/health`).then(r => r.json()),
        ])
        if (brainRes.status === "fulfilled") setBrainData(brainRes.value)
        if (healthRes.status === "fulfilled") setHealthData(healthRes.value)
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const testBrain = async () => {
    if (!testMessage.trim()) return
    setTesting(true)
    setTestResult(null)
    try {
      const res = await fetch(`${API_BASE_URL}/api/chat/public`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: testMessage }),
      })
      const data = await res.json()
      setTestResult(data)
      // Refresh brain data
      const brainRes = await fetch(`${API_BASE_URL}/analytics/brain`).then(r => r.json())
      setBrainData(brainRes)
    } catch (err) {
      setTestResult({ error: String(err) })
    } finally {
      setTesting(false)
    }
  }

  const brainHealth = healthData?.checks?.brain_pipeline

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Brain className="h-5 w-5 text-blue-500" /> Digital Brain
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Neuromorphic SNN cognitive architecture — 5 brain areas
          </p>
        </div>
        <div className={cn(
          "px-3 py-1 rounded-full text-xs font-medium",
          brainHealth?.status === "healthy" ? "bg-green-500/10 text-green-500" : "bg-yellow-500/10 text-yellow-500"
        )}>
          {brainHealth?.status === "healthy" ? "✅ Healthy" : "⚠️ Degraded"}
        </div>
      </div>

      {/* Brain Areas */}
      <div className="grid md:grid-cols-5 gap-4">
        {BRAIN_AREAS.map((area, i) => {
          const Icon = area.icon
          const areaData = brainData?.brain_areas?.[area.key]
          const firingRate = areaData?.firing_rate ?? areaData?.total ?? 0
          return (
            <motion.div
              key={area.key}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              className="p-4 rounded-xl border bg-card text-center"
            >
              <div className="w-12 h-12 rounded-full mx-auto mb-3 flex items-center justify-center"
                style={{ background: `${area.color}15` }}>
                <Icon className="h-6 w-6" style={{ color: area.color }} />
              </div>
              <h3 className="text-sm font-semibold">{area.name}</h3>
              <p className="text-2xl font-bold mt-2">{firingRate.toFixed(1)} <span className="text-xs text-muted-foreground">Hz</span></p>
              <p className="text-[10px] text-muted-foreground mt-1">{area.desc}</p>
            </motion.div>
          )
        })}
      </div>

      {/* Brain Activity Visualization */}
      <BrainActivity refreshInterval={3000} />

      {/* Test the Brain */}
      <div className="p-5 rounded-xl border bg-card">
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <Zap className="h-4 w-4" /> Test Brain Pipeline
        </h3>
        <div className="flex gap-2">
          <input
            type="text"
            value={testMessage}
            onChange={(e) => setTestMessage(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && testBrain()}
            placeholder="Type a message to test the brain..."
            className="flex-1 rounded-lg border bg-background px-3 py-2 text-sm"
          />
          <button
            onClick={testBrain}
            disabled={testing || !testMessage.trim()}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {testing ? <Spinner size="sm" /> : "Send"}
          </button>
        </div>
        {testResult && !testResult.error && (
          <div className="mt-4 p-3 rounded-lg bg-muted/50 space-y-2 text-sm">
            <div><strong>Emotion:</strong> {testResult.emotion} (valence: {testResult.emotion_detail?.valence})</div>
            <div><strong>Brain Action:</strong> {testResult.brain?.action} (confidence: {testResult.brain?.confidence})</div>
            <div><strong>Response:</strong> {testResult.response?.substring(0, 200)}</div>
            {testResult.audio_url && <div><strong>Audio:</strong> ✅ Generated</div>}
            {testResult.expression && <div><strong>Expression:</strong> mouth_smile={testResult.expression?.mouth?.mouth_smile_left}</div>}
          </div>
        )}
      </div>

      {/* SNN Info */}
      <div className="p-5 rounded-xl border bg-card">
        <h3 className="text-sm font-semibold mb-3">Architecture</h3>
        <div className="grid md:grid-cols-3 gap-4 text-sm">
          <div>
            <div className="font-medium">Encoding</div>
            <div className="text-muted-foreground">Spike rate encoding (256×16)</div>
          </div>
          <div>
            <div className="font-medium">Learning</div>
            <div className="text-muted-foreground">STDP + TD reinforcement</div>
          </div>
          <div>
            <div className="font-medium">Decision</div>
            <div className="text-muted-foreground">Basal ganglia action selection</div>
          </div>
        </div>
      </div>
    </div>
  )
}
