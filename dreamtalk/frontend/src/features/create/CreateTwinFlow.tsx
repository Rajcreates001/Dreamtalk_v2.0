"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import Link from "next/link"
import { AnimatePresence, motion } from "motion/react"
import {
  ArrowLeft, ArrowRight, Camera, Check, ChevronRight, Cpu, Globe, Info,
  Loader2, LogIn, Mic, Pause, Play, RotateCcw, ScanFace, ShieldCheck, Sparkles,
  Square, Trash2, TriangleAlert, Upload, Volume2,
} from "lucide-react"
import { STEP_ORDER, useCreateTwin, type Step } from "./useCreateTwin"
import { useVoiceRecorder } from "./useVoiceRecorder"
import { ThemeToggle } from "@/components/theme-toggle"

const STEP_META: Record<Exclude<Step, "consent">, { n: string; label: string }> = {
  identity: { n: "01", label: "Identity" },
  voice: { n: "02", label: "Voice" },
  processing: { n: "03", label: "Processing" },
  preview: { n: "04", label: "Preview" },
}

const fmtTime = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`

// ═══════════════════════════════════════════════════════════════════
export function CreateTwinFlow() {
  const c = useCreateTwin()

  return (
    <div className="relative min-h-dvh bg-background text-foreground overflow-x-hidden">
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute -top-40 -right-32 h-[32rem] w-[32rem] rounded-full blur-3xl opacity-40"
          style={{ background: "radial-gradient(circle, var(--glow-primary), transparent 70%)" }} />
        <div className="absolute -bottom-40 -left-32 h-[30rem] w-[30rem] rounded-full blur-3xl opacity-40"
          style={{ background: "radial-gradient(circle, var(--glow-accent), transparent 70%)" }} />
      </div>

      <header className="sticky top-0 z-20 backdrop-blur-xl bg-background/70 border-b border-border-subtle">
        <div className="mx-auto max-w-5xl px-5 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="grid h-8 w-8 place-items-center rounded-xl bg-gradient-to-br from-primary to-secondary">
              <Sparkles className="h-4 w-4 text-white" />
            </span>
            <span className="font-display font-bold tracking-tight">
              Dream<span className="text-primary">Talk</span>
            </span>
          </Link>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link href="/" className="text-sm text-foreground-muted hover:text-foreground transition-colors">Exit</Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-5 pb-28 pt-10">
        {c.authed === false ? (
          <AuthGate />
        ) : c.authed === null ? (
          <div className="grid place-items-center py-24 text-foreground-muted">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : c.step === "consent" ? (
          <ConsentGate c={c} />
        ) : (
          <>
            <Stepper step={c.step} />
            <div className="mt-10">
              <motion.div
                key={c.step}
                initial={{ opacity: 0, y: 16, filter: "blur(6px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
              >
                {c.step === "identity" && <IdentityStep c={c} />}
                {c.step === "voice" && <VoiceStep c={c} />}
                {c.step === "processing" && <ProcessingStep c={c} />}
                {c.step === "preview" && <PreviewStep c={c} />}
              </motion.div>
            </div>
          </>
        )}
      </main>

      {c.authed && c.step !== "consent" && c.step !== "processing" && (
        <div className="fixed bottom-0 inset-x-0 z-20 border-t border-border-subtle bg-background/80 backdrop-blur-xl">
          <div className="mx-auto max-w-5xl px-5 h-20 flex items-center justify-between">
            <button onClick={c.goBack} disabled={STEP_ORDER.indexOf(c.step) <= 1}
              className="inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm text-foreground-muted hover:text-foreground disabled:opacity-40 transition-colors">
              <ArrowLeft className="h-4 w-4" /> Back
            </button>
            {c.step === "voice" ? (
              <button onClick={c.startProcessing} disabled={!c.canProceed.voice}
                className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/20 enabled:hover:bg-primary-hover disabled:opacity-40 transition-all">
                Build my digital twin <ArrowRight className="h-4 w-4" />
              </button>
            ) : c.step === "preview" ? (
              <Link href="/studio"
                className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/20 hover:bg-primary-hover transition-all">
                Enter Studio <ArrowRight className="h-4 w-4" />
              </Link>
            ) : (
              <button onClick={c.goNext} disabled={!c.canProceed[c.step]}
                className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/20 enabled:hover:bg-primary-hover disabled:opacity-40 transition-all">
                Continue <ArrowRight className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════
function AuthGate() {
  return (
    <div className="mx-auto max-w-md text-center py-16">
      <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-primary/12 text-primary">
        <LogIn className="h-7 w-7" />
      </span>
      <h1 className="mt-5 font-display text-2xl font-bold">Sign in to create your twin</h1>
      <p className="mt-2 text-foreground-muted">
        Creating a digital twin uploads your face and voice to your private
        account. Please sign in to continue.
      </p>
      <div className="mt-6 flex justify-center gap-3">
        <Link href="/login" className="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary-hover transition-all">Sign in</Link>
        <Link href="/signup" className="rounded-xl border border-border px-5 py-2.5 text-sm font-medium hover:border-primary/40 transition-colors">Create account</Link>
      </div>
    </div>
  )
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="mt-4 flex items-start gap-2 rounded-2xl border border-destructive/40 bg-destructive/8 p-4 text-sm">
      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
      <span className="text-foreground">{message}</span>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════
function Stepper({ step }: { step: Step }) {
  const active = STEP_ORDER.indexOf(step)
  const steps = (Object.keys(STEP_META) as Array<keyof typeof STEP_META>)
  return (
    <div className="flex items-center gap-2 sm:gap-4">
      {steps.map((key, i) => {
        const idx = i + 1
        const isActive = active === idx
        const isDone = active > idx
        return (
          <div key={key} className="flex flex-1 items-center gap-2 sm:gap-4">
            <div className="flex items-center gap-3">
              <div className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl border text-xs font-semibold transition-all ${
                isActive ? "border-primary bg-primary/12 text-primary"
                  : isDone ? "border-secondary/50 bg-secondary/15 text-secondary"
                    : "border-border text-foreground-muted"}`}>
                {isDone ? <Check className="h-4 w-4" /> : STEP_META[key].n}
              </div>
              <span className={`hidden sm:block text-sm font-medium ${isActive ? "text-foreground" : "text-foreground-muted"}`}>
                {STEP_META[key].label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className="h-px flex-1 bg-border relative overflow-hidden rounded-full">
                <div className={`absolute inset-y-0 left-0 bg-secondary transition-all duration-500 ${isDone ? "w-full" : "w-0"}`} />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════
type C = ReturnType<typeof useCreateTwin>

function ConsentGate({ c }: { c: C }) {
  return (
    <div className="mx-auto max-w-xl">
      <motion.div
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="rounded-3xl border border-border bg-card/80 backdrop-blur-xl p-8 shadow-xl"
      >
        <span className="label-mono">Create your digital twin</span>
        <h1 className="mt-3 font-display text-3xl font-bold leading-tight">Build your visual and vocal identity.</h1>
        <p className="mt-3 text-foreground-muted">
          A digital twin resembles your appearance and speaks in your voice across
          Indian languages. Let&apos;s start with a name and your consent.
        </p>

        <label className="mt-8 block">
          <span className="label-mono">Name your twin</span>
          <input value={c.name} onChange={(e) => c.setName(e.target.value)} placeholder="e.g. Aarav"
            className="mt-2 w-full rounded-xl border border-input bg-background px-4 py-3 text-foreground placeholder:text-foreground-muted/70 focus:outline-none focus:ring-2 focus:ring-ring/40 focus:border-primary/50 transition-all" />
        </label>

        <button onClick={() => c.setConsent(!c.consent)}
          className="mt-6 flex w-full items-start gap-3 rounded-2xl border border-border bg-surface/60 p-4 text-left hover:border-primary/40 transition-colors">
          <span className={`mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-md border transition-all ${
            c.consent ? "border-primary bg-primary text-primary-foreground" : "border-border"}`}>
            {c.consent && <Check className="h-3.5 w-3.5" />}
          </span>
          <span className="text-sm text-foreground-muted">
            <ShieldCheck className="mr-1 inline h-4 w-4 text-secondary" />
            I confirm that I have the right and permission to create and use this digital representation.
          </span>
        </button>

        {c.error && <ErrorBanner message={c.error} />}

        <button onClick={c.beginCreation} disabled={!c.canProceed.consent}
          className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/20 enabled:hover:bg-primary-hover disabled:opacity-40 transition-all">
          {c.busy ? <><Loader2 className="h-4 w-4 animate-spin" /> Creating…</> : <>Begin <ChevronRight className="h-4 w-4" /></>}
        </button>
      </motion.div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════
function IdentityStep({ c }: { c: C }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [camOpen, setCamOpen] = useState(false)
  const scanning = c.faceStatus === "uploading" || c.faceStatus === "analyzing"

  const onFiles = useCallback((files: FileList | null) => {
    const f = files?.[0]
    if (f && f.type.startsWith("image/")) c.analyzeFace(f)
  }, [c])

  const r = c.faceResult
  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <div>
        <span className="label-mono">Step 01</span>
        <h2 className="mt-2 font-display text-3xl font-bold">Introduce your face</h2>
        <p className="mt-2 text-foreground-muted">Upload a clear, front-facing photo. Good lighting and a neutral expression produce the best digital twin.</p>

        {!c.facePreviewUrl && !camOpen && (
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); onFiles(e.dataTransfer.files) }}
            className={`mt-6 rounded-3xl border-2 border-dashed p-10 text-center transition-all ${dragging ? "border-primary bg-primary/5" : "border-border bg-surface/40"}`}
          >
            <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-primary/10"><Upload className="h-7 w-7 text-primary" /></div>
            <p className="mt-4 font-medium">Drag & drop your photo</p>
            <p className="text-sm text-foreground-muted">PNG or JPG, front-facing</p>
            <div className="mt-5 flex items-center justify-center gap-3">
              <button onClick={() => inputRef.current?.click()} className="rounded-xl border border-border bg-card px-4 py-2 text-sm font-medium hover:border-primary/40 transition-colors">Browse files</button>
              <button onClick={() => setCamOpen(true)} className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2 text-sm font-medium hover:border-primary/40 transition-colors"><Camera className="h-4 w-4" /> Use camera</button>
            </div>
            <input ref={inputRef} type="file" accept="image/*" hidden onChange={(e) => onFiles(e.target.files)} />
          </div>
        )}

        {camOpen && <CameraCapture onCapture={(f) => { setCamOpen(false); c.analyzeFace(f) }} onCancel={() => setCamOpen(false)} />}

        {r && c.faceStatus === "done" && (
          <div className="mt-6 rounded-2xl border border-secondary/40 bg-secondary/8 p-4">
            <div className="flex items-center gap-2 text-sm font-medium"><Check className="h-4 w-4 text-secondary" /> Face detected — ready to build.</div>
            <dl className="mt-3 grid grid-cols-2 gap-3 text-xs">
              <Stat k="Face detected" v={r.faceDetected ? "Yes" : "No"} />
              <Stat k="Quality" v={r.quality ? `${Math.round(r.quality * 100)}%` : "—"} />
            </dl>
          </div>
        )}
        {c.faceStatus === "error" && c.error && <ErrorBanner message={c.error} />}
        {c.faceStatus === "error" && !c.error && <ErrorBanner message="No clear face detected. Try another photo." />}
      </div>

      <div className="relative">
        <div className="aspect-[4/5] overflow-hidden rounded-3xl border border-border bg-surface/50">
          {c.facePreviewUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={c.facePreviewUrl} alt="Face preview" className="h-full w-full object-cover" />
          ) : (
            <div className="grid h-full place-items-center text-foreground-muted"><ScanFace className="h-16 w-16 opacity-30" /></div>
          )}
          {scanning && (
            <>
              <div className="absolute inset-0 bg-background/30 backdrop-blur-[1px]" />
              <motion.div className="absolute inset-x-0 h-16"
                style={{ background: "linear-gradient(180deg, transparent, var(--glow-primary), transparent)" }}
                animate={{ top: ["-10%", "100%"] }} transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }} />
              <div className="absolute inset-0 grid place-items-center">
                <span className="inline-flex items-center gap-2 rounded-full bg-background/80 px-3 py-1.5 text-xs font-medium">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" /> {c.faceStatus === "uploading" ? "Uploading…" : "Analyzing face…"}
                </span>
              </div>
            </>
          )}
          {c.faceStatus === "done" && (
            <span className="absolute left-3 top-3 inline-flex items-center gap-1.5 rounded-full bg-secondary/90 px-2.5 py-1 text-[11px] font-semibold text-white"><Check className="h-3 w-3" /> Face detected</span>
          )}
        </div>
        {c.facePreviewUrl && !scanning && (
          <button onClick={c.clearFace} className="absolute right-3 top-3 grid h-9 w-9 place-items-center rounded-full bg-background/80 text-foreground-muted hover:text-foreground transition-colors"><Trash2 className="h-4 w-4" /></button>
        )}
      </div>
    </div>
  )
}

function CameraCapture({ onCapture, onCancel }: { onCapture: (f: File) => void; onCancel: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [err, setErr] = useState<string | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  useEffect(() => {
    let cancelled = false
    navigator.mediaDevices?.getUserMedia({ video: { facingMode: "user" } })
      .then((s) => {
        if (cancelled) { s.getTracks().forEach((t) => t.stop()); return }
        streamRef.current = s
        if (videoRef.current) { videoRef.current.srcObject = s; videoRef.current.play().catch(() => {}) }
      })
      .catch(() => setErr("Camera access denied. Upload a photo instead."))
    return () => { cancelled = true; streamRef.current?.getTracks().forEach((t) => t.stop()) }
  }, [])

  const snap = () => {
    const v = videoRef.current
    if (!v) return
    const canvas = document.createElement("canvas")
    canvas.width = v.videoWidth || 720
    canvas.height = v.videoHeight || 900
    canvas.getContext("2d")?.drawImage(v, 0, 0, canvas.width, canvas.height)
    canvas.toBlob((b) => b && onCapture(new File([b], "capture.jpg", { type: "image/jpeg" })), "image/jpeg", 0.92)
  }

  return (
    <div className="mt-6 rounded-3xl border border-border bg-surface/40 p-4">
      {err ? <p className="p-6 text-center text-sm text-warning">{err}</p> : (
        <>
          <video ref={videoRef} className="aspect-video w-full rounded-2xl bg-black object-cover" muted playsInline />
          <div className="mt-3 flex justify-center gap-3">
            <button onClick={onCancel} className="rounded-xl border border-border px-4 py-2 text-sm">Cancel</button>
            <button onClick={snap} className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"><Camera className="h-4 w-4" /> Capture</button>
          </div>
        </>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════
function VoiceStep({ c }: { c: C }) {
  const rec = useVoiceRecorder()
  const [tab, setTab] = useState<"record" | "upload">("record")
  const uploadRef = useRef<HTMLInputElement>(null)
  const audioRef = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const analyzing = c.voiceStatus === "uploading" || c.voiceStatus === "analyzing"

  const onStop = async () => { const r = await rec.stop(); if (r) c.setVoice(r.blob, r.duration) }
  const onUpload = (files: FileList | null) => {
    const f = files?.[0]; if (!f) return
    const audio = new Audio(URL.createObjectURL(f))
    audio.onloadedmetadata = () => c.setVoice(f, isFinite(audio.duration) ? audio.duration : 10)
  }

  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <div>
        <span className="label-mono">Step 02</span>
        <h2 className="mt-2 font-display text-3xl font-bold">Introduce your voice</h2>
        <p className="mt-2 text-foreground-muted">Record or upload 8–15 seconds of clear speech. This becomes your twin&apos;s vocal identity.</p>

        <div className="mt-6 inline-flex rounded-xl border border-border bg-surface/50 p-1">
          {(["record", "upload"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)} className={`rounded-lg px-4 py-1.5 text-sm font-medium capitalize transition-all ${tab === t ? "bg-primary/12 text-primary" : "text-foreground-muted hover:text-foreground"}`}>{t}</button>
          ))}
        </div>

        {tab === "record" ? (
          <div className="mt-6 rounded-3xl border border-border bg-surface/40 p-6">
            <Waveform levels={rec.state === "recording" ? rec.levels : undefined} active={rec.state === "recording"} />
            <div className="mt-5 flex items-center justify-between">
              <span className="label-mono">{rec.state === "recording" ? fmtTime(rec.elapsed) : "0:00"}</span>
              {rec.state === "recording" ? (
                <button onClick={onStop} className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground"><Square className="h-4 w-4" /> Stop</button>
              ) : (
                <button onClick={rec.start} className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/20 hover:bg-primary-hover transition-all"><Mic className="h-4 w-4" /> Record</button>
              )}
            </div>
            {rec.error && <p className="mt-3 text-sm text-warning">{rec.error}</p>}
          </div>
        ) : (
          <div className="mt-6 rounded-3xl border-2 border-dashed border-border bg-surface/40 p-10 text-center">
            <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-primary/10"><Volume2 className="h-6 w-6 text-primary" /></div>
            <p className="mt-3 font-medium">Upload an audio file</p>
            <p className="text-sm text-foreground-muted">WAV, MP3 or WebM</p>
            <button onClick={() => uploadRef.current?.click()} className="mt-4 rounded-xl border border-border bg-card px-4 py-2 text-sm font-medium hover:border-primary/40 transition-colors">Browse files</button>
            <input ref={uploadRef} type="file" accept="audio/*" hidden onChange={(e) => onUpload(e.target.files)} />
          </div>
        )}

        {c.voiceUrl && (
          <div className="mt-4 flex items-center gap-3 rounded-2xl border border-border bg-card/70 p-3">
            <button onClick={() => { const el = audioRef.current; if (!el) return; playing ? el.pause() : el.play() }} className="grid h-10 w-10 place-items-center rounded-full bg-primary/12 text-primary">{playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}</button>
            <div className="flex-1">
              <div className="text-sm font-medium">Your recording</div>
              <div className="text-xs text-foreground-muted">{fmtTime(c.voiceDuration)}{c.voiceResult ? ` · ${c.voiceResult.isCloned ? "cloned" : c.voiceResult.isSynthetic ? "synthetic" : "processed"}` : ""}</div>
            </div>
            <button onClick={c.clearVoice} className="grid h-9 w-9 place-items-center rounded-full text-foreground-muted hover:text-foreground"><Trash2 className="h-4 w-4" /></button>
            <audio ref={audioRef} src={c.voiceUrl} onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onEnded={() => setPlaying(false)} hidden />
          </div>
        )}

        {analyzing && <p className="mt-3 inline-flex items-center gap-2 text-sm text-foreground-muted"><Loader2 className="h-4 w-4 animate-spin text-primary" /> {c.voiceStatus === "uploading" ? "Uploading voice…" : "Cloning voice…"}</p>}
        {c.voiceStatus === "done" && <p className="mt-3 text-sm text-secondary">Voice captured — {c.voiceResult?.isCloned ? "cloned successfully." : "profile ready."}</p>}
        {c.voiceStatus === "error" && <ErrorBanner message={c.error ?? "Voice processing failed."} />}
      </div>

      <div>
        <span className="label-mono flex items-center gap-1.5"><Globe className="h-3.5 w-3.5" /> Indian languages</span>
        <h3 className="mt-2 font-display text-xl font-bold">One identity. Many languages.</h3>
        <p className="mt-1 text-sm text-foreground-muted">Choose the languages your twin should speak.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {c.languages.length === 0 && <span className="text-sm text-foreground-muted">No languages returned by the backend yet.</span>}
          {c.languages.map((l) => {
            const on = c.selectedLangs.includes(l.code)
            return (
              <button key={l.code} onClick={() => c.toggleLang(l.code)} className={`rounded-full border px-3.5 py-2 text-sm transition-all ${on ? "border-primary bg-primary/12 text-primary" : "border-border text-foreground-muted hover:border-primary/40 hover:text-foreground"}`}>
                <span className="font-medium">{l.native}</span><span className="ml-1.5 text-xs opacity-70">{l.name}</span>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function Waveform({ levels, active }: { levels?: number[]; active?: boolean }) {
  const bars = levels ?? Array.from({ length: 48 }, (_, i) => 0.1 + 0.06 * Math.sin(i))
  return (
    <div className="flex h-24 items-center justify-center gap-[3px]">
      {bars.map((v, i) => (
        <div key={i} className={`w-[3px] rounded-full transition-[height] duration-75 ${active ? "bg-primary" : "bg-border"}`} style={{ height: `${Math.max(4, v * 96)}px` }} />
      ))}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════
const PIPELINE = ["Face analysis", "3D reconstruction", "Voice processing", "Speaker profile", "Avatar preparation"]

function ProcessingStep({ c }: { c: C }) {
  const [showTech, setShowTech] = useState(false)
  const p = c.pipeline
  const progress = p?.progress ?? 0
  const failed = p ? !c.isOk(p.status) && (p.status === "failed" || p.status === "error") : false
  const activeIdx = Math.min(PIPELINE.length - 1, Math.floor((progress / 100) * PIPELINE.length))

  return (
    <div className="mx-auto max-w-2xl text-center">
      <span className="label-mono">Step 03</span>
      <h2 className="mt-2 font-display text-3xl font-bold">Building your digital identity</h2>
      <p className="mt-2 text-foreground-muted">This runs on your DreamTalk backend. Keep this tab open.</p>

      <div className="relative mx-auto mt-8 grid h-40 w-40 place-items-center">
        <div className="absolute inset-0 rounded-full border border-border" />
        <div className="absolute inset-0 rounded-full"
          style={{ background: `conic-gradient(var(--primary) ${progress * 3.6}deg, transparent 0)`, mask: "radial-gradient(farthest-side, transparent 66%, #000 67%)", WebkitMask: "radial-gradient(farthest-side, transparent 66%, #000 67%)" }} />
        <div className="grid h-24 w-24 place-items-center rounded-full bg-surface/60">
          <span className="font-display text-2xl font-bold">{Math.round(progress)}%</span>
        </div>
      </div>

      <div className="mt-8 space-y-2 text-left">
        {PIPELINE.map((label, i) => {
          const done = c.isOk(p?.status) || i < activeIdx
          const activeNow = !done && i === activeIdx && !failed
          return (
            <div key={label} className="flex items-center gap-3 rounded-xl border border-border-subtle bg-card/50 px-4 py-3">
              <span className={`grid h-7 w-7 place-items-center rounded-lg ${done ? "bg-secondary/15 text-secondary" : activeNow ? "bg-primary/12 text-primary" : "bg-surface text-foreground-muted"}`}>
                {done ? <Check className="h-4 w-4" /> : activeNow ? <Loader2 className="h-4 w-4 animate-spin" /> : <span className="text-xs">{i + 1}</span>}
              </span>
              <span className={`text-sm ${done || activeNow ? "text-foreground" : "text-foreground-muted"}`}>{label}</span>
            </div>
          )
        })}
      </div>

      {c.error && <ErrorBanner message={c.error} />}

      <div className="mt-6 text-left">
        <button onClick={() => setShowTech((s) => !s)} className="inline-flex items-center gap-2 text-sm text-foreground-muted hover:text-foreground transition-colors">
          <Cpu className="h-4 w-4" /> {showTech ? "Hide" : "Show"} technical details
        </button>
        <AnimatePresence>
          {showTech && (
            <motion.dl initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
              className="mt-3 grid grid-cols-2 gap-3 overflow-hidden rounded-2xl border border-border bg-card/60 p-4 text-xs sm:grid-cols-3">
              <Stat k="Twin ID" v={c.twinId ?? "—"} />
              <Stat k="Stage" v={p?.stage ?? "—"} />
              <Stat k="Status" v={p?.status ?? "…"} />
            </motion.dl>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════
function PreviewStep({ c }: { c: C }) {
  return (
    <div className="mx-auto max-w-3xl">
      <div className="text-center">
        <motion.span initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ type: "spring", stiffness: 200, damping: 18 }}
          className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-secondary/15 text-secondary"><Check className="h-7 w-7" /></motion.span>
        <h2 className="mt-4 font-display text-3xl font-bold">Your digital twin is ready.</h2>
        <p className="mt-2 text-foreground-muted">Preview {c.name}, then step into the studio to make them speak.</p>
      </div>

      <div className="mt-8 grid gap-6 sm:grid-cols-5">
        <div className="sm:col-span-2 aspect-[4/5] overflow-hidden rounded-3xl border border-border bg-surface/50">
          {c.faceResult?.previewUrl || c.facePreviewUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={c.faceResult?.previewUrl || c.facePreviewUrl!} alt={c.name} className="h-full w-full object-cover" />
          ) : (
            <div className="grid h-full place-items-center"><ScanFace className="h-16 w-16 text-foreground-muted opacity-30" /></div>
          )}
        </div>
        <div className="sm:col-span-3 rounded-3xl border border-border bg-card/70 p-6">
          <span className="label-mono">Identity summary</span>
          <h3 className="mt-1 font-display text-2xl font-bold">{c.name}</h3>
          <dl className="mt-4 space-y-3 text-sm">
            <Row k="Visual identity" v={c.faceResult?.faceDetected ? "Ready" : "—"} good={c.faceResult?.faceDetected} />
            <Row k="Voice identity" v={c.voiceResult ? (c.voiceResult.isCloned ? "Cloned" : c.voiceResult.isSynthetic ? "Synthetic" : "Ready") : "—"} good={!!c.voiceResult} />
            <Row k="Status" v={c.pipeline?.status ?? "—"} good={c.isOk(c.pipeline?.status)} />
          </dl>
          <div className="mt-5 flex flex-wrap gap-2">
            {c.selectedLangs.map((code) => {
              const l = c.languages.find((x) => x.code === code)
              return <span key={code} className="rounded-full border border-border bg-surface/60 px-3 py-1 text-xs">{l?.native ?? code}</span>
            })}
          </div>
          <div className="mt-6 flex gap-3">
            <Link href="/studio" className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary-hover transition-all">Enter Studio <ArrowRight className="h-4 w-4" /></Link>
            <Link href="/dashboard/my-avatars" className="inline-flex items-center gap-2 rounded-xl border border-border px-5 py-2.5 text-sm font-medium hover:border-primary/40 transition-colors"><RotateCcw className="h-4 w-4" /> My avatars</Link>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── shared ─────────────────────────────────────────────────────────
function Stat({ k, v }: { k: string; v: string }) {
  return (
    <div className="rounded-lg bg-surface/60 px-3 py-2">
      <dt className="label-mono !text-[9px]">{k}</dt>
      <dd className="mt-0.5 font-medium capitalize text-foreground truncate">{v}</dd>
    </div>
  )
}
function Row({ k, v, good }: { k: string; v: string; good?: boolean }) {
  return (
    <div className="flex items-center justify-between border-b border-border-subtle pb-2">
      <dt className="text-foreground-muted">{k}</dt>
      <dd className={`font-medium capitalize ${good ? "text-secondary" : "text-foreground"}`}>{v}</dd>
    </div>
  )
}
