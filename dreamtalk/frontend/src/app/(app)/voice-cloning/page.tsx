"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import { motion, AnimatePresence } from "motion/react"
import { cn } from "@/lib/utils"
import {
  Mic, Download, Wand2, Loader2, Check, AlertCircle,
  Zap, FileAudio, Radio, Square, Play, Pause, Volume2,
  Upload, RotateCcw, Sparkles,
} from "lucide-react"
import { voiceApi, chatApi } from "@/lib/api"
import { API_BASE_URL } from "@/lib/constants"

const LANGUAGES = [
  { code: "en", name: "English", native: true },
  { code: "en-gb", name: "British English", native: true },
  { code: "hi", name: "Hindi", native: true },
  { code: "es", name: "Spanish", native: true },
  { code: "fr", name: "French", native: true },
  { code: "it", name: "Italian", native: true },
  { code: "pt", name: "Portuguese", native: true },
  { code: "ja", name: "Japanese", native: true },
  { code: "zh", name: "Chinese", native: true },
  { code: "ta", name: "Tamil", native: false },
  { code: "te", name: "Telugu", native: false },
  { code: "ml", name: "Malayalam", native: false },
  { code: "kn", name: "Kannada", native: false },
  { code: "de", name: "German", native: false },
  { code: "ru", name: "Russian", native: false },
  { code: "ko", name: "Korean", native: false },
]

const PRESET_SAMPLES = [
  { label: "Greeting", text: "Hello! Welcome to DreamTalk. I'm your digital assistant, and I'm excited to talk with you today." },
  { label: "Story", text: "Once upon a time, in a land far beyond the mountains, there lived a curious inventor who dreamed of giving voices to machines." },
  { label: "News", text: "Scientists have developed a new method for real-time voice cloning that can replicate human speech patterns with remarkable accuracy." },
  { label: "Poetry", text: "Shall I compare thee to a summer's day? Thou art more lovely and more temperate. Rough winds do shake the darling buds of May." },
]

type CloneError = { message: string; detail?: string } | null
type Step = "record" | "clone" | "preview" | "generate"

export default function VoiceCloningPage() {
  // ── Recording state ─────────────────────────────────────────────────
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null)
  const [recordedUrl, setRecordedUrl] = useState<string | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animFrameRef = useRef<number>(0)
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  // ── Upload state ────────────────────────────────────────────────────
  const [voiceFile, setVoiceFile] = useState<File | null>(null)
  const [voiceName, setVoiceName] = useState("")

  // ── Clone state ─────────────────────────────────────────────────────
  const [cloneStatus, setCloneStatus] = useState<string | null>(null)
  const [clonedVoiceId, setClonedVoiceId] = useState<string | null>(null)

  // ── Generate state ──────────────────────────────────────────────────
  const [outputLang, setOutputLang] = useState("en")
  const [script, setScript] = useState(PRESET_SAMPLES[0].text)
  const [generating, setGenerating] = useState(false)
  const [generatedAudio, setGeneratedAudio] = useState<string | null>(null)

  // ── Preview state ───────────────────────────────────────────────────
  const [previewing, setPreviewing] = useState(false)
  const [previewAudio, setPreviewAudio] = useState<string | null>(null)

  // ── Live conversation ───────────────────────────────────────────────
  const [isLive, setIsLive] = useState(false)
  const isLiveRef = useRef(false)
  const [isListening, setIsListening] = useState(false)
  const [liveTranscript, setLiveTranscript] = useState("")
  const [liveResponse, setLiveResponse] = useState("")
  const [liveLoading, setLiveLoading] = useState(false)
  const recognitionRef = useRef<any>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const sendLiveMessageRef = useRef<(text: string) => void>(() => {})

  const [tab, setTab] = useState<"generate" | "live">("generate")
  const [error, setError] = useState<CloneError>(null)

  useEffect(() => { isLiveRef.current = isLive }, [isLive])

  // ── Determine current step ──────────────────────────────────────────
  const currentStep: Step = cloneStatus === "ready"
    ? (generatedAudio ? "generate" : "preview")
    : (recordedBlob || voiceFile) ? "clone" : "record"

  // ── Mic Recording ───────────────────────────────────────────────────
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      // Set up analyser for waveform
      const ctx = new AudioContext()
      const source = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      analyserRef.current = analyser

      // Set up recorder
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" })
      const chunks: Blob[] = []
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data) }
      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop())
        streamRef.current = null
        if (chunks.length > 0) {
          const blob = new Blob(chunks, { type: "audio/webm" })
          setRecordedBlob(blob)
          setRecordedUrl(URL.createObjectURL(blob))
          setVoiceFile(new File([blob], "recorded-voice.webm", { type: "audio/webm" }))
          setVoiceName("My Recorded Voice")
        }
      }

      mediaRecorderRef.current = recorder
      recorder.start(100) // 100ms chunks for waveform
      setIsRecording(true)
      setRecordingTime(0)

      // Timer
      timerRef.current = setInterval(() => setRecordingTime(t => t + 1), 1000)

      // Waveform animation
      const canvas = canvasRef.current
      if (canvas) {
        const ctx2d = canvas.getContext("2d")!
        const width = canvas.width
        const height = canvas.height
        const drawWave = () => {
          if (!analyserRef.current) return
          const data = new Uint8Array(analyserRef.current.frequencyBinCount)
          analyserRef.current.getByteFrequencyData(data)

          ctx2d.clearRect(0, 0, width, height)
          ctx2d.fillStyle = "rgba(204,58,99, 0.1)"
          ctx2d.fillRect(0, 0, width, height)

          const barWidth = width / data.length * 2.5
          let x = 0
          for (let i = 0; i < data.length && x < width; i++) {
            const barHeight = (data[i] / 255) * height * 0.8
            const gradient = ctx2d.createLinearGradient(0, height, 0, height - barHeight)
            gradient.addColorStop(0, "#CC3A63")
            gradient.addColorStop(1, "#CC3A63")
            ctx2d.fillStyle = gradient
            ctx2d.fillRect(x, height - barHeight, barWidth - 1, barHeight)
            x += barWidth
          }
          animFrameRef.current = requestAnimationFrame(drawWave)
        }
        drawWave()
      }
    } catch (err) {
      setError({ message: "Microphone access denied", detail: "Please allow microphone access in your browser." })
    }
  }, [])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop()
    }
    setIsRecording(false)
    cancelAnimationFrame(animFrameRef.current)
    if (timerRef.current) clearInterval(timerRef.current)
    analyserRef.current = null
  }, [])

  const resetRecording = useCallback(() => {
    setRecordedBlob(null)
    setRecordedUrl(null)
    setVoiceFile(null)
    setCloneStatus(null)
    setClonedVoiceId(null)
    setGeneratedAudio(null)
    setPreviewAudio(null)
    setRecordingTime(0)
    setVoiceName("")
  }, [])

  // Cleanup
  useEffect(() => {
    return () => {
      cancelAnimationFrame(animFrameRef.current)
      if (timerRef.current) clearInterval(timerRef.current)
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop())
    }
  }, [])

  // ── File upload ─────────────────────────────────────────────────────
  const openFilePicker = () => {
    const input = document.createElement("input")
    input.type = "file"
    input.accept = "audio/*"
    input.onchange = (e: any) => {
      const file = e.target.files?.[0]
      if (file) {
        setVoiceFile(file)
        setVoiceName(file.name.replace(/\.[^.]+$/, ""))
        setRecordedBlob(null)
        setRecordedUrl(null)
        setError(null)
      }
    }
    input.click()
  }

  // ── Clone Voice ─────────────────────────────────────────────────────
  const handleClone = useCallback(async () => {
    if (!voiceFile) return
    setCloneStatus("cloning")
    setError(null)
    try {
      const formData = new FormData()
      formData.append("file", voiceFile)
      formData.append("name", voiceName || "cloned-voice")
      formData.append("description", `Cloned from ${voiceFile.name}`)
      const result = await voiceApi.cloneVoice(formData)
      const voiceId = (result as any)?.voice_id
      if (voiceId) {
        setClonedVoiceId(voiceId)
        setCloneStatus("ready")
      } else {
        throw new Error("No voice_id returned")
      }
    } catch (err: any) {
      setCloneStatus("error")
      setError({ message: "Voice cloning failed", detail: err?.message || "Check that the server is running." })
    }
  }, [voiceFile, voiceName])

  // ── Preview cloned voice ────────────────────────────────────────────
  const handlePreview = useCallback(async () => {
    if (!clonedVoiceId) return
    setPreviewing(true)
    try {
      const result = await voiceApi.generateVoice({
        text: "Hello! This is a preview of my cloned voice. How does it sound?",
        voice_id: clonedVoiceId,
        emotion: "neutral",
        engine: "rvc",
        language: outputLang,
      })
      if (result.audio_url) {
        const url = result.audio_url.startsWith("http") ? result.audio_url : `${API_BASE_URL}${result.audio_url}`
        setPreviewAudio(url)
      }
    } catch (err: any) {
      setError({ message: "Preview failed", detail: err?.message })
    } finally {
      setPreviewing(false)
    }
  }, [clonedVoiceId, outputLang])

  // ── Generate Audio ──────────────────────────────────────────────────
  const handleGenerate = useCallback(async () => {
    if (!script.trim()) return
    setGenerating(true)
    setError(null)
    try {
      const result = await voiceApi.generateVoice({
        text: script,
        voice_id: clonedVoiceId || "af_heart",
        emotion: "neutral",
        engine: clonedVoiceId ? "rvc" : "kokoro",
        language: outputLang,
      })
      if (result.audio_url) {
        const url = result.audio_url.startsWith("http") ? result.audio_url : `${API_BASE_URL}${result.audio_url}`
        setGeneratedAudio(url)
      } else {
        throw new Error("No audio_url returned")
      }
    } catch (err: any) {
      setError({ message: "Generation failed", detail: err?.message })
    } finally {
      setGenerating(false)
    }
  }, [script, clonedVoiceId, outputLang])

  // ── Live Conversation ───────────────────────────────────────────────
  const startLiveConversation = useCallback(() => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SR) {
      setError({ message: "Speech recognition not supported", detail: "Use Chrome or Edge." })
      return
    }
    const recognition = new SR()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = outputLang === "en" ? "en-US" : outputLang
    recognition.onstart = () => { setIsListening(true); setIsLive(true) }
    recognition.onresult = (event: any) => {
      let transcript = ""
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript
      }
      setLiveTranscript(transcript)
      if (event.results[event.resultIndex].isFinal) {
        sendLiveMessageRef.current(transcript)
      }
    }
    recognition.onerror = (event: any) => {
      if (event.error === "not-allowed") {
        setError({ message: "Mic denied", detail: "Allow mic in browser settings." })
        setIsLive(false); isLiveRef.current = false
      }
    }
    recognition.onend = () => {
      setIsListening(false)
      if (isLiveRef.current && recognitionRef.current) {
        try { recognition.start() } catch {}
      }
    }
    recognitionRef.current = recognition
    try { recognition.start() } catch {}
  }, [outputLang])

  const stopLiveConversation = useCallback(() => {
    setIsLive(false); setIsListening(false); setLiveTranscript(""); setLiveResponse("")
    if (recognitionRef.current) { try { recognitionRef.current.stop() } catch {} recognitionRef.current = null }
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null }
  }, [])

  const sendLiveMessage = useCallback(async (text: string) => {
    setLiveLoading(true)
    try {
      if (audioRef.current) { audioRef.current.pause(); audioRef.current = null }
      const chatData = await chatApi.send(text)
      const responseText = chatData.response || "I didn't understand that."
      setLiveResponse(responseText)
      const ttsResult = await voiceApi.generateVoice({
        text: responseText, voice_id: clonedVoiceId || "af_heart",
        emotion: chatData.emotion || "neutral", engine: clonedVoiceId ? "rvc" : "kokoro", language: outputLang,
      })
      if (ttsResult.audio_url) {
        const fullUrl = ttsResult.audio_url.startsWith("http") ? ttsResult.audio_url : `${API_BASE_URL}${ttsResult.audio_url}`
        const audio = new Audio(fullUrl); audioRef.current = audio; audio.play().catch(() => {})
      }
    } catch {} finally { setLiveLoading(false) }
  }, [clonedVoiceId, outputLang])

  useEffect(() => { sendLiveMessageRef.current = sendLiveMessage }, [sendLiveMessage])
  useEffect(() => {
    return () => {
      if (recognitionRef.current) try { recognitionRef.current.stop() } catch {}
      if (audioRef.current) audioRef.current.pause()
    }
  }, [])

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`

  const STEPS: { id: Step; label: string; num: number }[] = [
    { id: "record", label: "Record / Upload", num: 1 },
    { id: "clone", label: "Clone Voice", num: 2 },
    { id: "preview", label: "Preview", num: 3 },
    { id: "generate", label: "Generate", num: 4 },
  ]

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-foreground mb-1">Voice Cloning</h1>
        <p className="text-sm text-foreground-muted">Record or upload a voice, clone it, and generate speech in any language</p>
      </div>

      {/* ── Step Progress Bar ──────────────────────────────────────────── */}
      <div className="flex items-center justify-center gap-2">
        {STEPS.map((step, i) => {
          const isActive = currentStep === step.id
          const isDone = STEPS.findIndex(s => s.id === currentStep) > i
          return (
            <div key={step.id} className="flex items-center gap-2">
              <div className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all",
                isActive ? "bg-[#CC3A63]/15 text-[#CC3A63] border border-[#CC3A63]/30" :
                isDone ? "bg-[#A2AB73]/10 text-[#A2AB73] border border-[#A2AB73]/20" :
                "bg-white/[0.04] text-foreground-muted border border-white/[0.06]"
              )}>
                {isDone ? <Check className="h-3 w-3" /> : <span className="w-4 text-center">{step.num}</span>}
                <span className="hidden sm:inline">{step.label}</span>
              </div>
              {i < STEPS.length - 1 && <div className={cn("w-6 h-px", isDone ? "bg-[#A2AB73]/30" : "bg-white/[0.08]")} />}
            </div>
          )
        })}
      </div>

      {/* ── Error Banner ────────────────────────────────────────────────── */}
      <AnimatePresence>
        {error && (
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
            className="flex items-start gap-3 p-4 rounded-xl bg-[#D84C63]/10 border border-[#D84C63]/30">
            <AlertCircle className="h-5 w-5 text-[#D84C63] shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-[#D84C63]">{error.message}</p>
              {error.detail && <p className="text-xs text-foreground-muted mt-1">{error.detail}</p>}
            </div>
            <button onClick={() => setError(null)} className="text-foreground-muted hover:text-foreground text-xs">Dismiss</button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Step 1: Record or Upload ─────────────────────────────────── */}
      <div className="rounded-2xl bg-card/80 border border-white/[0.06] p-6">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-7 h-7 rounded-lg bg-[#CC3A63]/15 flex items-center justify-center">
            <span className="text-xs font-bold text-[#CC3A63]">1</span>
          </div>
          <h2 className="text-sm font-semibold text-foreground">Record or Upload Voice</h2>
          {cloneStatus === "ready" && <Check className="h-4 w-4 text-[#A2AB73]" />}
        </div>

        {/* Voice name */}
        <div className="mb-4">
          <label className="text-[10px] text-foreground-muted mb-1 block">Voice Profile Name</label>
          <input type="text" value={voiceName} onChange={(e) => setVoiceName(e.target.value)}
            placeholder="e.g. My Voice, Speaker A"
            className="w-full px-3 py-2 rounded-lg bg-white/[0.04] border border-white/[0.06] text-sm text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-[#CC3A63]/30" />
        </div>

        {/* Record / Upload buttons */}
        {!recordedBlob && !voiceFile && (
          <div className="grid grid-cols-2 gap-3">
            {/* Record from mic */}
            <button onClick={startRecording}
              className="flex flex-col items-center gap-2 p-6 rounded-xl border-2 border-dashed border-[#CC3A63]/30 hover:border-[#CC3A63]/60 bg-[#CC3A63]/5 hover:bg-[#CC3A63]/10 transition-all">
              <Mic className="h-8 w-8 text-[#CC3A63]" />
              <span className="text-sm font-medium text-[#CC3A63]">Record from Mic</span>
              <span className="text-xs text-foreground-muted">Click to start recording</span>
            </button>
            {/* Upload file */}
            <button onClick={openFilePicker}
              className="flex flex-col items-center gap-2 p-6 rounded-xl border-2 border-dashed border-[#CC3A63]/30 hover:border-[#CC3A63]/60 bg-[#CC3A63]/5 hover:bg-[#CC3A63]/10 transition-all">
              <Upload className="h-8 w-8 text-[#CC3A63]" />
              <span className="text-sm font-medium text-[#CC3A63]">Upload File</span>
              <span className="text-xs text-foreground-muted">MP3, WAV, M4A, FLAC</span>
            </button>
          </div>
        )}

        {/* Recording in progress */}
        {isRecording && (
          <div className="space-y-3">
            <canvas ref={canvasRef} width={400} height={80} className="w-full h-20 rounded-xl bg-[#CC3A63]/5" />
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="relative flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#D84C63]" />
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-[#D84C63]" />
                </span>
                <span className="text-sm font-mono text-[#D84C63]">{formatTime(recordingTime)}</span>
              </div>
              <button onClick={stopRecording}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#D84C63]/15 border border-[#D84C63]/30 text-[#D84C63] text-sm font-medium hover:bg-[#D84C63]/25 transition-all">
                <Square className="h-4 w-4 fill-current" /> Stop Recording
              </button>
            </div>
          </div>
        )}

        {/* Recorded / uploaded file */}
        {(recordedBlob || voiceFile) && !isRecording && (
          <div className="space-y-3">
            <div className="flex items-center gap-3 p-4 rounded-xl bg-[#A2AB73]/5 border border-[#A2AB73]/20">
              <Check className="h-4 w-4 text-[#A2AB73] shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-[#A2AB73] truncate">{voiceFile?.name || "Recorded voice"}</p>
                {recordedUrl && <p className="text-xs text-foreground-muted">{formatTime(recordingTime)} recorded</p>}
              </div>
              <button onClick={resetRecording} className="text-foreground-muted hover:text-foreground transition-colors">
                <RotateCcw className="h-4 w-4" />
              </button>
            </div>
            {recordedUrl && (
              <audio controls src={recordedUrl} className="w-full h-10 rounded-lg" />
            )}
          </div>
        )}

        {/* Clone button */}
        {voiceFile && cloneStatus !== "cloning" && cloneStatus !== "ready" && (
          <button onClick={handleClone}
            className="mt-4 flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-[#CC3A63] to-[#CC3A63] text-white text-sm font-medium hover:shadow-lg hover:shadow-[#CC3A63]/20 transition-all">
            <Wand2 className="h-4 w-4" /> Clone Voice
          </button>
        )}

        {/* Cloning progress */}
        {cloneStatus === "cloning" && (
          <div className="mt-4 flex items-center gap-3 p-4 rounded-xl bg-[#D6A44C]/5 border border-[#D6A44C]/20">
            <Loader2 className="h-5 w-5 animate-spin text-[#D6A44C]" />
            <div>
              <p className="text-sm text-[#D6A44C]">Cloning voice...</p>
              <p className="text-xs text-foreground-muted">Analyzing voice characteristics</p>
            </div>
          </div>
        )}

        {clonedVoiceId && (
          <div className="mt-3 flex items-center gap-2 text-xs text-foreground-muted">
            <span className="h-1.5 w-1.5 rounded-full bg-[#A2AB73]" />
            Voice ID: <code className="text-foreground-muted font-mono">{clonedVoiceId}</code>
          </div>
        )}
      </div>

      {/* ── Step 2 & 3: Preview (only after cloning) ─────────────────── */}
      {cloneStatus === "ready" && (
        <div className="rounded-2xl bg-card/80 border border-white/[0.06] p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-7 h-7 rounded-lg bg-[#D6A44C]/15 flex items-center justify-center">
              <span className="text-xs font-bold text-[#D6A44C]">2</span>
            </div>
            <h2 className="text-sm font-semibold text-foreground">Preview Cloned Voice</h2>
          </div>
          <p className="text-xs text-foreground-muted mb-4">Hear a sample of your cloned voice before generating full audio</p>
          <div className="flex items-center gap-3">
            <button onClick={handlePreview} disabled={previewing}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#D6A44C]/15 border border-[#D6A44C]/30 text-[#D6A44C] text-sm font-medium hover:bg-[#D6A44C]/25 transition-all disabled:opacity-50">
              {previewing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {previewing ? "Generating preview..." : "Play Preview"}
            </button>
            {previewAudio && (
              <audio controls src={previewAudio} className="flex-1 h-10 rounded-lg" />
            )}
          </div>
        </div>
      )}

      {/* ── Step 3: Language ─────────────────────────────────────────── */}
      {cloneStatus === "ready" && (
        <div className="rounded-2xl bg-card/80 border border-white/[0.06] p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-7 h-7 rounded-lg bg-[#CC3A63]/15 flex items-center justify-center">
              <span className="text-xs font-bold text-[#CC3A63]">3</span>
            </div>
            <h2 className="text-sm font-semibold text-foreground">Output Language</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {LANGUAGES.map((l) => (
              <button key={l.code} onClick={() => setOutputLang(l.code)}
                className={cn("px-4 py-2 rounded-xl text-xs transition-all border flex items-center gap-1.5",
                  outputLang === l.code
                    ? "bg-[#CC3A63]/15 border-[#CC3A63]/30 text-foreground"
                    : "bg-white/[0.04] border-white/[0.06] text-foreground-muted hover:text-foreground")}>
                {l.name}
                {l.native && <span className="w-1.5 h-1.5 rounded-full bg-[#A2AB73] shrink-0" />}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Step 4: Generate / Live ──────────────────────────────────── */}
      {cloneStatus === "ready" && (
        <div className="rounded-2xl bg-card/80 border border-white/[0.06] p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-7 h-7 rounded-lg bg-[#A2AB73]/15 flex items-center justify-center">
              <span className="text-xs font-bold text-[#A2AB73]">4</span>
            </div>
            <h2 className="text-sm font-semibold text-foreground">Generate Speech</h2>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 p-1 rounded-xl bg-white/[0.04] w-fit mb-4">
            {[{ id: "generate" as const, label: "Text to Speech", icon: FileAudio },
              { id: "live" as const, label: "Live Conversation", icon: Radio }].map((t) => {
              const Icon = t.icon
              return (
                <button key={t.id} onClick={() => setTab(t.id)}
                  className={cn("flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs transition-all",
                    tab === t.id ? "bg-[#CC3A63]/15 text-foreground" : "text-foreground-muted")}>
                  <Icon className="h-3.5 w-3.5" /> {t.label}
                </button>
              )
            })}
          </div>

          {tab === "generate" ? (
            <div className="space-y-4">
              {/* Preset samples */}
              <div className="flex flex-wrap gap-2">
                {PRESET_SAMPLES.map((sample) => (
                  <button key={sample.label} onClick={() => setScript(sample.text)}
                    className={cn("px-3 py-1.5 rounded-lg text-xs border transition-all",
                      script === sample.text
                        ? "bg-[#CC3A63]/10 border-[#CC3A63]/30 text-[#CC3A63]"
                        : "bg-white/[0.04] border-white/[0.06] text-foreground-muted hover:text-foreground")}>
                    <Sparkles className="h-3 w-3 inline mr-1" />{sample.label}
                  </button>
                ))}
              </div>

              <textarea value={script} onChange={(e) => setScript(e.target.value)}
                placeholder="Type your script here..." rows={5}
                className="w-full px-4 py-3 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-[#CC3A63]/30 resize-none" />

              <div className="flex gap-2">
                <button onClick={handleGenerate} disabled={!script.trim() || generating}
                  className="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-[#CC3A63] to-[#CC3A63] text-white font-medium disabled:opacity-50 transition-all hover:shadow-lg hover:shadow-[#CC3A63]/20">
                  {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
                  {generating ? "Generating..." : "Generate Audio"}
                </button>
                {generatedAudio && (
                  <a href={generatedAudio} download
                    className="flex items-center gap-2 px-4 py-3 rounded-xl bg-white/[0.04] border border-white/[0.06] text-foreground text-sm hover:bg-white/[0.08] transition-all">
                    <Download className="h-4 w-4" /> Download
                  </a>
                )}
              </div>

              {generatedAudio && (
                <div className="space-y-3">
                  <div className="flex items-center gap-3 p-4 rounded-xl bg-[#A2AB73]/5 border border-[#A2AB73]/20">
                    <Check className="h-4 w-4 text-[#A2AB73]" />
                    <span className="text-xs text-[#A2AB73]">Audio generated successfully</span>
                  </div>
                  <audio controls src={generatedAudio} className="w-full h-10 rounded-lg" />
                </div>
              )}
            </div>
          ) : (
            /* Live Voice Conversation */
            <div className="space-y-4">
              <div className="flex items-center justify-center gap-3 p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <div className={cn("w-16 h-16 rounded-full flex items-center justify-center transition-all",
                  isLive ? "bg-[#CC3A63]/15 border border-[#CC3A63]/30 animate-pulse" : "bg-[#A2AB73]/10 border border-[#A2AB73]/20")}>
                  {isListening ? <Mic className="h-8 w-8 text-[#CC3A63] animate-bounce" /> : <Radio className="h-8 w-8 text-[#A2AB73]" />}
                </div>
              </div>

              {isLive && (
                <div className="space-y-3">
                  {liveTranscript && (
                    <div className="p-3 rounded-xl bg-[#CC3A63]/5 border border-[#CC3A63]/20">
                      <p className="text-[10px] text-[#CC3A63] mb-1 font-medium">You said:</p>
                      <p className="text-sm text-foreground">{liveTranscript}</p>
                    </div>
                  )}
                  {liveLoading && (
                    <div className="flex items-center gap-2 text-xs text-[#D6A44C]">
                      <Loader2 className="h-3 w-3 animate-spin" /> Processing response...
                    </div>
                  )}
                  {liveResponse && (
                    <div className="p-3 rounded-xl bg-[#A2AB73]/5 border border-[#A2AB73]/20">
                      <p className="text-[10px] text-[#A2AB73] mb-1 font-medium">Response:</p>
                      <p className="text-sm text-foreground">{liveResponse}</p>
                    </div>
                  )}
                </div>
              )}

              <div className="text-center">
                <button onClick={isLive ? stopLiveConversation : startLiveConversation}
                  className={cn("inline-flex items-center gap-2 px-8 py-4 rounded-xl font-medium transition-all text-sm",
                    isLive ? "bg-[#D84C63]/15 text-[#D84C63] border border-[#D84C63]/30" : "bg-gradient-to-r from-[#CC3A63] to-[#CC3A63] text-white hover:shadow-lg hover:shadow-[#CC3A63]/20")}>
                  {isLive ? <><Square className="h-4 w-4 fill-current" /> Stop</> : <><Mic className="h-4 w-4" /> Start Live</>}
                </button>
              </div>

              {isLive && isListening && (
                <div className="flex items-center justify-center gap-2 text-xs text-[#A2AB73]">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#A2AB73]" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-[#A2AB73]" />
                  </span>
                  Listening... Speak now
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
