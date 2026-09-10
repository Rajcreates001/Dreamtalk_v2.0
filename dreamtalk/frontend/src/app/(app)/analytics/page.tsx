"use client"

import { useState, useEffect } from "react"
import { motion } from "motion/react"
import {
  BarChart3, TrendingUp, Users, MessageSquare, Heart,
  Brain, BookOpen, Cpu, Clock, Zap, ArrowUp, ArrowDown, RefreshCw,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { API_BASE_URL } from "@/lib/constants"
import { EmotionTimeline } from "@/components/analytics/emotion-timeline"
import { BrainActivity } from "@/components/analytics/brain-activity"
import { Spinner } from "@/components/loading-states"

export default function AnalyticsPage() {
  const [stats, setStats] = useState<any>(null)
  const [emotionData, setEmotionData] = useState<any>(null)
  const [brainData, setBrainData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [statsRes, emotionRes, brainRes] = await Promise.allSettled([
          fetch(`${API_BASE_URL}/analytics/stats`).then(r => r.json()),
          fetch(`${API_BASE_URL}/analytics/emotions`).then(r => r.json()),
          fetch(`${API_BASE_URL}/analytics/brain`).then(r => r.json()),
        ])
        if (statsRes.status === "fulfilled") setStats(statsRes.value)
        if (emotionRes.status === "fulfilled") setEmotionData(emotionRes.value)
        if (brainRes.status === "fulfilled") setBrainData(brainRes.value)
      } catch (err) {
        console.error("Failed to load analytics:", err)
      } finally {
        setLoading(false)
      }
    }
    load()
    const interval = setInterval(load, 10000)
    return () => clearInterval(interval)
  }, [])

  const metrics = [
    {
      label: "Total Events",
      value: stats?.total_events ?? emotionData?.total_events ?? "—",
      icon: MessageSquare,
      color: "#7C5CFF",
    },
    {
      label: "Sessions Tracked",
      value: stats?.total_sessions ?? "—",
      icon: Users,
      color: "#00E5FF",
    },
    {
      label: "Dominant Emotion",
      value: emotionData?.dominant_emotion ?? "—",
      icon: Heart,
      color: "#FF6B9D",
    },
    {
      label: "Avg Valence",
      value: emotionData?.avg_valence?.toFixed(2) ?? "—",
      icon: TrendingUp,
      color: "#42FFC6",
    },
  ]

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">Analytics</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time emotion, brain, and pipeline analytics
          </p>
        </div>
        <button
          onClick={() => {
            setLoading(true)
            fetch(`${API_BASE_URL}/analytics/stats`)
              .then(r => r.json())
              .then(setStats)
              .finally(() => setLoading(false))
          }}
          className="flex items-center gap-2 rounded-lg border bg-background px-3 py-2 text-sm hover:bg-accent"
        >
          {loading ? <Spinner size="sm" /> : <RefreshCw className="h-4 w-4" />}
          Refresh
        </button>
      </div>

      {/* Metrics grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((metric, i) => {
          const Icon = metric.icon
          return (
            <motion.div
              key={metric.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
              className="p-4 rounded-xl border bg-card"
            >
              <div className="flex items-center gap-3 mb-3">
                <div
                  className="w-9 h-9 rounded-lg flex items-center justify-center"
                  style={{ background: `${metric.color}12` }}
                >
                  <Icon className="h-4 w-4" style={{ color: metric.color }} />
                </div>
              </div>
              <p className="text-2xl font-bold">{metric.value}</p>
              <p className="text-xs text-muted-foreground mt-1">{metric.label}</p>
            </motion.div>
          )
        })}
      </div>

      {/* Emotion Timeline + Brain Activity */}
      <div className="grid lg:grid-cols-2 gap-4">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <EmotionTimeline refreshInterval={5000} />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <BrainActivity refreshInterval={3000} />
        </motion.div>
      </div>

      {/* Session Stats */}
      {stats && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="p-5 rounded-xl border bg-card"
        >
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
            <BarChart3 className="h-4 w-4" /> Session Statistics
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            {Object.entries(stats).filter(([k]) => !k.startsWith("_")).map(([key, value]) => (
              <div key={key}>
                <div className="text-lg font-bold">{String(value)}</div>
                <div className="text-xs text-muted-foreground">{key.replace(/_/g, " ")}</div>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  )
}
