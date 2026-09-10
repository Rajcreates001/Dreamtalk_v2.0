"use client"

import { useState, useCallback, useRef, useEffect } from "react"
import type { Message, PipelineResult } from "@/types/chat"
import { API_BASE_URL, WS_URL, getAuthToken } from "@/lib/constants"
import { pipelineApi } from "@/lib/api"

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [emotion, setEmotion] = useState<string | undefined>(undefined)
  const [pipelineStatus, setPipelineStatus] = useState<PipelineResult["status"]>("idle")
  const [pipelineResult, setPipelineResult] = useState<{
    videoUrl?: string
    audioUrl?: string
  } | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // WebSocket connection for real-time updates
  useEffect(() => {
    let mounted = true
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null

    function connect() {
      if (!mounted) return
      try {
        const ws = new WebSocket(WS_URL)
        wsRef.current = ws

        ws.onopen = () => {
          if (!mounted) { ws.close(); return }
        }

        ws.onmessage = (event) => {
          if (!mounted) return
          try {
            const data = JSON.parse(event.data)

            switch (data.type) {
              case "message":
                setMessages((prev) => {
                  const exists = prev.some((m) => m.id === data.id)
                  if (exists) return prev
                  const assistantMsg: Message = {
                    id: data.id || crypto.randomUUID(),
                    role: "assistant",
                    content: data.content || data.response || "",
                    timestamp: Date.now(),
                    emotion: data.emotion,
                    audioUrl: data.audio_url,
                    videoUrl: data.video_url,
                  }
                  return [...prev, assistantMsg]
                })
                break

              case "emotion":
                setEmotion(data.emotion)
                break

              case "speaking":
                setIsSpeaking(data.speaking)
                break

              case "pipeline_update":
                setPipelineStatus(data.status)
                if (data.progress !== undefined) {
                  setPipelineResult((prev) => ({
                    ...prev,
                    progress: data.progress,
                  }))
                }
                if (data.status === "done") {
                  setPipelineResult({
                    videoUrl: data.result?.video_url,
                    audioUrl: data.result?.audio_url,
                  })
                }
                if (data.status === "error") {
                  setPipelineResult(null)
                }
                break

              case "typing":
                setIsLoading(data.typing)
                break
            }
          } catch {
            // non-JSON messages are ignored
          }
        }

        ws.onclose = () => {
          wsRef.current = null
          if (mounted) {
            reconnectTimer = setTimeout(connect, 3000)
          }
        }

        ws.onerror = () => {
          ws.close()
        }
      } catch {
        if (mounted) {
          reconnectTimer = setTimeout(connect, 3000)
        }
      }
    }

    connect()

    return () => {
      mounted = false
      if (reconnectTimer) clearTimeout(reconnectTimer)
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [])

  const sendMessage = useCallback(async (content: string) => {
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      timestamp: Date.now(),
    }
    setMessages((prev) => [...prev, userMsg])
    setIsLoading(true)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      // Use public endpoint if no auth, authenticated endpoint otherwise
      const token = getAuthToken()
      const chatUrl = token ? `${API_BASE_URL}/api/chat` : `${API_BASE_URL}/api/chat/public`
      const headers: Record<string, string> = { "Content-Type": "application/json" }
      if (token) headers["Authorization"] = `Bearer ${token}`

      const res = await fetch(chatUrl, {
        method: "POST",
        headers,
        body: JSON.stringify({
          message: content,
          history: messages.slice(-10).map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
        signal: controller.signal,
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const data = await res.json()
      const assistantMsg: Message = {
        id: data.id || crypto.randomUUID(),
        role: "assistant",
        content: data.response || data.content || "",
        timestamp: Date.now(),
        emotion: data.emotion,
        audioUrl: data.audio_url,
        videoUrl: data.video_url,
      }

      setMessages((prev) => [...prev, assistantMsg])

      if (data.emotion) setEmotion(data.emotion)
      if (data.audio_url || data.video_url) {
        setPipelineResult({
          audioUrl: data.audio_url,
          videoUrl: data.video_url,
        })
      }

      return assistantMsg
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return
      console.error("Chat error:", err)
    } finally {
      setIsLoading(false)
      abortRef.current = null
    }
  }, [messages])

  const runPipeline = useCallback(async (config: {
    model: string
    appearance_url?: string
    audio_url?: string
    text?: string
  }) => {
    setPipelineStatus("processing")
    setPipelineResult(null)

    try {
      const result = await pipelineApi.run(config)
      setPipelineStatus("processing")

      // Poll for result
      const pipelineId = result.pipeline_id
      const poll = setInterval(async () => {
        try {
          const status = await pipelineApi.getResult(pipelineId)
          if (status.progress !== undefined) {
            setPipelineResult((prev) => ({ ...prev, progress: status.progress }))
          }
          if (status.status === "done") {
            setPipelineStatus("done")
            setPipelineResult({
              videoUrl: status.result?.video_url,
              audioUrl: status.result?.audio_url,
            })
            clearInterval(poll)
          } else if (status.status === "error") {
            setPipelineStatus("error")
            clearInterval(poll)
          }
        } catch {
          clearInterval(poll)
          setPipelineStatus("error")
        }
      }, 2000)

      pollRef.current = poll
    } catch {
      setPipelineStatus("error")
    }
  }, [])

  const stopGeneration = useCallback(() => {
    abortRef.current?.abort()
    setIsLoading(false)
    setIsSpeaking(false)
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
    setPipelineResult(null)
    setPipelineStatus("idle")
    setEmotion(undefined)
  }, [])

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  return {
    messages,
    isLoading,
    isSpeaking,
    emotion,
    pipelineStatus,
    pipelineResult,
    sendMessage,
    runPipeline,
    stopGeneration,
    clearMessages,
  }
}
