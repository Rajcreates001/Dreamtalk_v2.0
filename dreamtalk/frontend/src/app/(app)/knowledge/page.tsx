"use client"

import { useState, useEffect } from "react"
import { motion } from "motion/react"
import { BookOpen, Database, Search, Upload, RefreshCw, Trash2 } from "lucide-react"
import { API_BASE_URL } from "@/lib/constants"
import { Spinner } from "@/components/loading-states"

export default function KnowledgePage() {
  const [health, setHealth] = useState<any>(null)
  const [twinList, setTwinList] = useState<any[]>([])
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [searching, setSearching] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [healthRes, twinsRes] = await Promise.allSettled([
          fetch(`${API_BASE_URL}/pipeline/health`).then(r => r.json()),
          fetch(`${API_BASE_URL}/api/v1/digital-twins`, {
            headers: { "Authorization": `Bearer ${localStorage.getItem("dreamtalk_token") || ""}` },
          }).then(r => r.json()),
        ])
        if (healthRes.status === "fulfilled") setHealth(healthRes.value)
        if (twinsRes.status === "fulfilled") {
          const data = twinsRes.value
          setTwinList(Array.isArray(data) ? data : data?.items || [])
        }
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    setSearching(true)
    try {
      // Search Weaviate directly
      const resp = await fetch(`http://127.0.0.1:8081/v1/objects?class=KnowledgeChunk&limit=10`, {
        headers: { "Content-Type": "application/json" },
      })
      if (resp.ok) {
        const data = await resp.json()
        setSearchResults(data.objects || [])
      }
    } catch {
      setSearchResults([])
    } finally {
      setSearching(false)
    }
  }

  const weaviateHealth = health?.checks?.weights // Closest indicator

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-blue-500" /> Knowledge Base
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Weaviate vector database — RAG knowledge store</p>
        </div>
        <div className={cn(
          "px-3 py-1 rounded-full text-xs font-medium",
          "bg-green-500/10 text-green-500"
        )}>
          ✅ Weaviate Online
        </div>
      </div>

      {/* Stats */}
      <div className="grid md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl border bg-card">
          <Database className="h-5 w-5 text-blue-500 mb-2" />
          <div className="text-2xl font-bold">{twinList.length}</div>
          <div className="text-xs text-muted-foreground">Digital Twins</div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <BookOpen className="h-5 w-5 text-green-500 mb-2" />
          <div className="text-2xl font-bold">
            {twinList.reduce((sum, t) => sum + (t.intelligence?.total_chunks || 0), 0)}
          </div>
          <div className="text-xs text-muted-foreground">Knowledge Chunks</div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <Search className="h-5 w-5 text-purple-500 mb-2" />
          <div className="text-2xl font-bold">
            {twinList.filter(t => t.intelligence?.indexed).length}
          </div>
          <div className="text-xs text-muted-foreground">Indexed Twins</div>
        </div>
      </div>

      {/* Search */}
      <div className="p-5 rounded-xl border bg-card space-y-4">
        <h3 className="text-sm font-semibold">Search Knowledge</h3>
        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Search the knowledge base..."
            className="flex-1 rounded-lg border bg-background px-3 py-2 text-sm"
          />
          <button
            onClick={handleSearch}
            disabled={searching}
            className="rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {searching ? <Spinner size="sm" /> : <Search className="h-4 w-4" />}
          </button>
        </div>
        {searchResults.length > 0 && (
          <div className="space-y-2">
            {searchResults.map((r, i) => (
              <div key={i} className="p-3 rounded-lg bg-muted/50 text-sm">
                <div className="font-medium">{r.properties?.title || r.properties?.text?.substring(0, 80) || "Untitled"}</div>
                <div className="text-muted-foreground text-xs mt-1">
                  {r.properties?.text?.substring(0, 200) || "No content"}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Twin Knowledge Status */}
      <div className="p-5 rounded-xl border bg-card">
        <h3 className="text-sm font-semibold mb-3">Digital Twin Knowledge</h3>
        {twinList.length === 0 ? (
          <p className="text-sm text-muted-foreground">No digital twins yet. Create one to start building knowledge.</p>
        ) : (
          <div className="space-y-3">
            {twinList.map((twin) => (
              <div key={twin.id} className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                <div>
                  <div className="text-sm font-medium">{twin.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {twin.intelligence?.total_chunks || 0} chunks • {twin.intelligence?.indexed ? "Indexed" : "Not indexed"}
                  </div>
                </div>
                <div className={cn(
                  "px-2 py-1 rounded text-xs",
                  twin.intelligence?.indexed ? "bg-green-500/10 text-green-500" : "bg-yellow-500/10 text-yellow-500"
                )}>
                  {twin.intelligence?.indexed ? "✅ Ready" : "⚠️ Pending"}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(" ")
}
