"use client"

import { useState, useRef, useCallback } from "react"
import { motion } from "motion/react"
import { cn } from "@/lib/utils"
import { Mic, MicOff, Send, Volume2, Loader2 } from "lucide-react"
import { API_BASE_URL, WS_URL } from "@/lib/constants"
import { Spinner } from "@/components/loading-states"

export default function VoiceChatPage() {
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [messages, setMessages] = useState<{ role: string; text: string; audioUrl?: string }[]>([])
  const [inputText, setInputText] = useState("")
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentEmotion, setCurrentEmotion] = useState("neutral")
  const wsRef = useRef<WebSocket | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const connectWs = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === "response") {
            const resp = data.data?.text || ""
            const audio = data.data?.audio_url
            setMessages(prev => [...prev.slice(-20), { role: "assistant", text: resp, audioUrl: audio }])
            setIsProcessing(false)
          }
          if (data.type === "emotion") {
            setCurrentEmotion(data.data?.primary_mood || "neutral")
          }
        } catch {}
      }
      ws.onclose = () => { wsRef.current = null }
    } catch {}
  }, [])

  const sendTextMessage = async () => {
    if (!inputText.trim()) return
    setMessages(prev => [...prev.slice(-20), { role: "user", text: inputText }])
    setIsProcessing(true)
    setInputText("")

    try {
      const res = await fetch(`${API_BASE_URL}/api/chat/public`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: inputText }),
      })
      const data = await res.json()
      setMessages(prev => [...prev.slice(-20), {
        role: "assistant",
        text: data.response || "",
        audioUrl: data.audio_url,
      }])
      if (data.emotion) setCurrentEmotion(data.emotion)
    } catch {
      setMessages(prev => [...prev, { role: "assistant", text: "Failed to get response" }])
    } finally {
      setIsProcessing(false)
    }
  }

  const toggleRecording = async () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop()
      setIsRecording(false)
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" })
      const chunks: Blob[] = []
      recorder.ondataavailable = (e) => chunks.push(e.data)
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        streamRef.current = null
        if (chunks.length === 0) return
        const blob = new Blob(chunks, { type: "audio/webm" })
        await transcribeAndSend(blob)
      }
      mediaRecorderRef.current = recorder
      recorder.start()
      setIsRecording(true)
    } catch (err) {
      console.error("Mic access denied:", err)
    }
  }

  const transcribeAndSend = async (audioBlob: Blob) => {
    setIsTranscribing(true)
    try {
      // Send audio to STT endpoint
      const formData = new FormData()
      formData.append("audio", audioBlob, "recording.webm")
      formData.append("language", "en")

      const res = await fetch(`${API_BASE_URL}/api/v1/voice/transcribe`, {
        method: "POST",
        body: formData,
      })

      if (!res.ok) throw new Error(`STT failed: ${res.status}`)
      const { text } = await res.json()

      if (!text || text.trim().length === 0) {
        setMessages(prev => [...prev, { role: "user", text: "[No speech detected]" }])
        return
      }

      // Show transcribed text as user message
      setMessages(prev => [...prev.slice(-20), { role: "user", text }])
      setIsProcessing(true)

      // Send transcribed text through chat pipeline
      const chatRes = await fetch(`${API_BASE_URL}/api/chat/public`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      })
      const chatData = await chatRes.json()
      setMessages(prev => [...prev.slice(-20), {
        role: "assistant",
        text: chatData.response || "",
        audioUrl: chatData.audio_url,
      }])
      if (chatData.emotion) setCurrentEmotion(chatData.emotion)
    } catch (err) {
      console.error("Transcription failed:", err)
      setMessages(prev => [...prev, { role: "assistant", text: "Failed to transcribe audio. Please try again." }])
    } finally {
      setIsTranscribing(false)
      setIsProcessing(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold">Voice Chat</h1>
        <p className="text-sm text-muted-foreground mt-1">Speak or type to chat with your digital twin</p>
      </div>

      {/* Messages */}
      <div className="min-h-[400px] max-h-[500px] overflow-y-auto rounded-xl border bg-card p-4 space-y-3">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
            Start a conversation by typing or recording
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
            <div className={cn(
              "max-w-[75%] rounded-xl px-4 py-2.5 text-sm",
              m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
            )}>
              {m.text}
              {m.audioUrl && (
                <div className="mt-2">
                  <audio
                    src={m.audioUrl.startsWith("http") ? m.audioUrl : `${API_BASE_URL}${m.audioUrl}`}
                    controls
                    className="w-full h-8"
                  />
                </div>
              )}
            </div>
          </div>
        ))}
        {isProcessing && (
          <div className="flex justify-start">
            <div className="bg-muted rounded-xl px-4 py-3 flex items-center gap-2">
              <Spinner size="sm" />
              <span className="text-sm text-muted-foreground">Thinking...</span>
            </div>
          </div>
        )}
      </div>

      {/* Emotion indicator */}
      <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
        <span>Detected emotion:</span>
        <span className="font-medium">
          {currentEmotion === "happy" ? "😊" : currentEmotion === "sad" ? "😢" : currentEmotion === "angry" ? "😠" : "😐"}
          {" "}{currentEmotion}
        </span>
      </div>

      {/* Input */}
      <div className="flex items-center gap-3">
        <button
          onClick={toggleRecording}
          disabled={isTranscribing}
          className={cn(
            "w-14 h-14 rounded-full flex items-center justify-center transition-all",
            isRecording ? "bg-red-500 text-white animate-pulse" : "",
            isTranscribing ? "bg-yellow-500 text-white animate-spin" : "",
            !isRecording && !isTranscribing ? "bg-muted hover:bg-accent" : ""
          )}
        >
          {isTranscribing ? <Loader2 className="h-6 w-6 animate-spin" /> : isRecording ? <MicOff className="h-6 w-6" /> : <Mic className="h-6 w-6" />}
        </button>
        {isRecording && <span className="text-xs text-red-500 animate-pulse">Recording... click to stop</span>}
        {isTranscribing && <span className="text-xs text-yellow-500">Transcribing...</span>}
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendTextMessage()}
          placeholder="Type a message or click mic to speak..."
          className="flex-1 rounded-xl border bg-background px-4 py-3 text-sm"
          disabled={isProcessing}
        />
        <button
          onClick={sendTextMessage}
          disabled={!inputText.trim() || isProcessing}
          className="w-14 h-14 rounded-xl bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 disabled:opacity-50"
        >
          <Send className="h-5 w-5" />
        </button>
      </div>
    </div>
  )
}
