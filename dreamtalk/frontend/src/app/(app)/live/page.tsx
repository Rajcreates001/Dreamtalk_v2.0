"use client"

import { useState, useRef } from "react"
import { cn } from "@/lib/utils"
import {
  Radio, Mic, MicOff, Video, VideoOff, Phone, PhoneOff,
  Brain, Heart, MessageSquare, Wifi, WifiOff,
} from "lucide-react"
import { API_BASE_URL, WS_URL } from "@/lib/constants"
import { VRMAvatar } from "@/components/avatar/vrm-avatar"

export default function LivePage() {
  const [connected, setConnected] = useState(false)
  const [micOn, setMicOn] = useState(true)
  const [cameraOn, setCameraOn] = useState(false)
  const [inCall, setInCall] = useState(false)
  const [emotion, setEmotion] = useState<string>("neutral")
  const [brainAction, setBrainAction] = useState<string>("")
  const [messages, setMessages] = useState<{ role: string; text: string; audioUrl?: string }[]>([])
  const [inputText, setInputText] = useState("")
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [lipSyncValue, setLipSyncValue] = useState(0)
  const [lipsyncKeyframes, setLipsyncKeyframes] = useState<any[]>([])
  const [audioStartTime, setAudioStartTime] = useState(0)
  const wsRef = useRef<WebSocket | null>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const audioRef = useRef<HTMLAudioElement>(null)
  const lipSyncRafRef = useRef<number>(0)

  const connectWebSocket = () => {
    try {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        ws.send(JSON.stringify({ type: "text", text: "Hello! I am ready for a live conversation." }))
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          switch (data.type) {
            case "emotion":
              setEmotion(data.data?.primary_mood || data.emotion || "neutral")
              break
            case "brain_state":
              setBrainAction(data.data?.basal_ganglia_action || "")
              break
            case "response": {
              const resp = data.data?.text || data.response || ""
              setMessages(prev => [...prev.slice(-20), { role: "assistant", text: resp }])
              // Generate TTS, get lip sync keyframes, then play
              fetch(`${API_BASE_URL}/api/v1/avatar/tts/generate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: resp, language: "en" }),
              }).then(r => r.json()).then(d => {
                if (d.audio_url && audioRef.current) {
                  // Get lip sync keyframes for this audio
                  const lipsyncUrl = `${API_BASE_URL}/api/avatar/lipsync/analyze`
                  const formData = new FormData()
                  formData.append("audio_path", d.audio_url)
                  formData.append("text", resp)
                  formData.append("emotion", emotion || "neutral")
                  fetch(lipsyncUrl, { method: "POST", body: formData })
                    .then(r => r.json())
                    .then(ls => {
                      setLipsyncKeyframes(ls.keyframes || [])
                      // Play audio with lip sync
                      audioRef.current!.src = `${API_BASE_URL}${d.audio_url}`
                      audioRef.current!.play().then(() => {
                        setIsSpeaking(true)
                        setAudioStartTime(performance.now())
                      }).catch(() => {})
                    })
                    .catch(() => {
                      // Fallback: play without keyframes
                      audioRef.current!.src = `${API_BASE_URL}${d.audio_url}`
                      audioRef.current!.play().then(() => {
                        setIsSpeaking(true)
                        setLipsyncKeyframes([])
                        setAudioStartTime(performance.now())
                      }).catch(() => {})
                    })
                }
              }).catch(() => {})
              break
            }
            case "processing":
              break
          }
        } catch { /* ignore */ }
      }

      ws.onclose = () => {
        setConnected(false)
        setTimeout(connectWebSocket, 3000)
      }

      ws.onerror = () => ws.close()
    } catch {
      setTimeout(connectWebSocket, 3000)
    }
  }

  const startCall = () => {
    setInCall(true)
    connectWebSocket()
    if (cameraOn) {
      navigator.mediaDevices?.getUserMedia({ video: true }).then(stream => {
        if (videoRef.current) videoRef.current.srcObject = stream
      }).catch(() => {})
    }
  }

  const endCall = () => {
    setInCall(false)
    wsRef.current?.close()
    wsRef.current = null
    setConnected(false)
    setMessages([])
    setEmotion("neutral")
    setBrainAction("")
    setIsSpeaking(false)
    setLipSyncValue(0)
    cancelAnimationFrame(lipSyncRafRef.current)
  }

  const sendMessage = () => {
    if (!inputText.trim() || !wsRef.current) return
    wsRef.current.send(JSON.stringify({ type: "text", text: inputText }))
    setMessages(prev => [...prev.slice(-20), { role: "user", text: inputText }])
    setInputText("")
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Radio className="h-5 w-5 text-red-500" /> Live Session
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Real-time conversation with your digital twin</p>
        </div>
        <div className={cn(
          "flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium",
          connected ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500"
        )}>
          {connected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
          {connected ? "Connected" : "Disconnected"}
        </div>
      </div>

      {/* Video Area */}
      <div className="relative aspect-video rounded-xl border bg-gradient-to-b from-gray-900 to-gray-950 overflow-hidden">
        {inCall ? (
          <>
            {cameraOn ? (
              <video ref={videoRef} autoPlay muted className="w-full h-full object-cover" />
            ) : (
              <VRMAvatar
                emotion={emotion}
                isSpeaking={isSpeaking}
                lipSyncValue={lipSyncValue}
                lipsyncKeyframes={lipsyncKeyframes}
                audioStartTime={audioStartTime}
              />
            )}
          </>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-4">
              <div className="text-8xl">🤖</div>
              <div className="text-white/60 text-sm">Click Start to begin</div>
            </div>
          </div>
        )}

        {/* Overlay info */}
        {inCall && (
          <div className="absolute top-4 left-4 space-y-2 z-10">
            <div className="flex items-center gap-2 bg-black/60 rounded-full px-3 py-1 text-xs text-white">
              <Brain className="h-3 w-3 text-blue-400" /> {brainAction || "Idle"}
            </div>
            <div className="flex items-center gap-2 bg-black/60 rounded-full px-3 py-1 text-xs text-white">
              <Heart className="h-3 w-3 text-pink-400" /> {emotion}
            </div>
            {isSpeaking && (
              <div className="flex items-center gap-2 bg-green-500/20 rounded-full px-3 py-1 text-xs text-green-400">
                🗣️ Speaking...
              </div>
            )}
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="flex items-center justify-center gap-4">
        <button
          onClick={() => setMicOn(!micOn)}
          className={cn("w-12 h-12 rounded-full flex items-center justify-center border transition-all",
            micOn ? "bg-background" : "bg-red-500/20 border-red-500/50 text-red-500"
          )}
        >
          {micOn ? <Mic className="h-5 w-5" /> : <MicOff className="h-5 w-5" />}
        </button>
        <button
          onClick={() => setCameraOn(!cameraOn)}
          className={cn("w-12 h-12 rounded-full flex items-center justify-center border transition-all",
            cameraOn ? "bg-background" : "bg-muted text-muted-foreground"
          )}
        >
          {cameraOn ? <Video className="h-5 w-5" /> : <VideoOff className="h-5 w-5" />}
        </button>
        {!inCall ? (
          <button
            onClick={startCall}
            className="w-16 h-16 rounded-full bg-green-500 text-white flex items-center justify-center hover:bg-green-600 transition-all"
          >
            <Phone className="h-6 w-6" />
          </button>
        ) : (
          <button
            onClick={endCall}
            className="w-16 h-16 rounded-full bg-red-500 text-white flex items-center justify-center hover:bg-red-600 transition-all"
          >
            <PhoneOff className="h-6 w-6" />
          </button>
        )}
      </div>

      {/* Hidden audio player for TTS */}
      <audio
        ref={audioRef}
        className="hidden"
        onEnded={() => {
          setIsSpeaking(false)
          setLipSyncValue(0)
          cancelAnimationFrame(lipSyncRafRef.current)
        }}
      />

      {/* Chat during call */}
      {inCall && (
        <div className="p-4 rounded-xl border bg-card space-y-3">
          <div className="max-h-48 overflow-y-auto space-y-2">
            {messages.map((m, i) => (
              <div key={i} className={cn("text-sm", m.role === "user" ? "text-right" : "text-left")}>
                <span className={cn(
                  "inline-block px-3 py-1.5 rounded-xl max-w-[80%]",
                  m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                )}>
                  {m.text}
                </span>
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Type a message..."
              className="flex-1 rounded-lg border bg-background px-3 py-2 text-sm"
            />
            <button
              onClick={sendMessage}
              className="rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
            >
              <MessageSquare className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
