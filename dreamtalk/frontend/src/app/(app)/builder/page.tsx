"use client"

import { useState, useEffect } from "react"
import { motion } from "motion/react"
import { Wrench, Play, Settings, CheckCircle, XCircle, Loader2, RefreshCw } from "lucide-react"
import { API_BASE_URL } from "@/lib/constants"
import { Spinner } from "@/components/loading-states"

type ComponentStatus = {
  name: string
  status: "healthy" | "unhealthy" | "degraded" | "unknown"
  message: string
  latencyMs: number
}

export default function BuilderPage() {
  const [components, setComponents] = useState<ComponentStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [testMessage, setTestMessage] = useState("Hello, how are you?")
  const [testResult, setTestResult] = useState<any>(null)
  const [testing, setTesting] = useState(false)

  const loadHealth = async () => {
    setLoading(true)
    try {
      const resp = await fetch(`${API_BASE_URL}/pipeline/health`)
      const data = await resp.json()
      const checks = data.checks || {}
      setComponents(
        Object.entries(checks).map(([key, info]: [string, any]) => ({
          name: key,
          status: info.status || "unknown",
          message: info.message || "",
          latencyMs: info.latency_ms || 0,
        }))
      )
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadHealth()
  }, [])

  const runPipelineTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const start = Date.now()
      const res = await fetch(`${API_BASE_URL}/api/chat/public`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: testMessage }),
      })
      const data = await res.json()
      const elapsed = Date.now() - start
      setTestResult({ ...data, latencyMs: elapsed })
    } catch (err: any) {
      setTestResult({ error: err.message })
    } finally {
      setTesting(false)
    }
  }

  const statusIcon = (s: string) => {
    if (s === "healthy") return <CheckCircle className="h-4 w-4 text-green-500" />
    if (s === "unreachable") return <XCircle className="h-4 w-4 text-red-500" />
    return <span className="h-4 w-4 rounded-full bg-yellow-500" />
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Wrench className="h-5 w-5" /> Pipeline Builder
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Test and monitor all pipeline components</p>
        </div>
        <button onClick={loadHealth} className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-accent">
          {loading ? <Spinner size="sm" /> : <RefreshCw className="h-4 w-4" />}
          Refresh
        </button>
      </div>

      {/* Component Status */}
      <div className="grid md:grid-cols-2 gap-3">
        {components.map((comp) => (
          <motion.div
            key={comp.name}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 rounded-xl border bg-card flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              {statusIcon(comp.status)}
              <div>
                <div className="text-sm font-medium">{comp.name}</div>
                <div className="text-xs text-muted-foreground">{comp.message}</div>
              </div>
            </div>
            <div className="text-xs text-muted-foreground">{comp.latencyMs.toFixed(1)}ms</div>
          </motion.div>
        ))}
      </div>

      {/* Pipeline Test */}
      <div className="p-5 rounded-xl border bg-card space-y-4">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <Play className="h-4 w-4" /> End-to-End Pipeline Test
        </h3>
        <div className="flex gap-2">
          <input
            type="text"
            value={testMessage}
            onChange={(e) => setTestMessage(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runPipelineTest()}
            placeholder="Enter test message..."
            className="flex-1 rounded-lg border bg-background px-3 py-2 text-sm"
          />
          <button
            onClick={runPipelineTest}
            disabled={testing}
            className="rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
          >
            {testing ? <Spinner size="sm" /> : <Play className="h-4 w-4" />}
            Run Test
          </button>
        </div>

        {testResult && !testResult.error && (
          <div className="p-4 rounded-lg bg-muted/50 space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="font-medium">Pipeline Test Result</span>
              <span className="text-xs text-muted-foreground">{testResult.latencyMs}ms total</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <div className="text-xs text-muted-foreground">Emotion</div>
                <div className="font-medium">{testResult.emotion}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Brain Action</div>
                <div className="font-medium">{testResult.brain?.action}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">TTS Audio</div>
                <div className="font-medium">{testResult.audio_url ? "✅ Generated" : "❌ None"}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Expression</div>
                <div className="font-medium">{testResult.expression?.mouth?.mouth_smile_left?.toFixed(2) || "N/A"}</div>
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Response</div>
              <div>{testResult.response?.substring(0, 200)}</div>
            </div>
          </div>
        )}

        {testResult?.error && (
          <div className="p-4 rounded-lg bg-red-500/10 text-sm text-red-500">
            Error: {testResult.error}
          </div>
        )}
      </div>
    </div>
  )
}
