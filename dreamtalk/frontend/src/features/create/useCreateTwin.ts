"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { avatarApi, digitalTwinApi, getAccessToken } from "@/lib/api"
import { avatarRuntime } from "@/services/avatar/client"

// ── View-model types (frontend-only; wire shapes live in lib/api.ts) ──
export type Step = "consent" | "identity" | "voice" | "processing" | "preview"
export const STEP_ORDER: Step[] = ["consent", "identity", "voice", "processing", "preview"]

export interface Language { code: string; name: string; native: string }

type PhaseStatus = "idle" | "uploading" | "analyzing" | "done" | "error"

interface FaceResult { faceDetected: boolean; quality: number; previewUrl?: string; statusRaw: string }
interface VoiceResult { isCloned: boolean; isSynthetic: boolean; quality: number; statusRaw: string }
interface Pipeline { status: string; progress: number; stage: string }

const TERMINAL_OK = new Set(["complete", "completed", "cloned", "ready", "appearance_complete", "voice_complete"])
const TERMINAL_FAIL = new Set(["failed", "error"])

const isOk = (s?: string) => !!s && TERMINAL_OK.has(String(s).toLowerCase())
const isFail = (s?: string) => !!s && TERMINAL_FAIL.has(String(s).toLowerCase())

/** Native scripts for the scheduled languages; falls back to the English name. */
const NATIVE_NAMES: Record<string, string> = {
  as: "অসমীয়া", bn: "বাংলা", brx: "बर'", doi: "डोगरी", en: "English",
  gu: "ગુજરાતી", hi: "हिन्दी", kn: "ಕನ್ನಡ", kok: "कोंकणी", ks: "کٲشُر",
  mai: "मैथिली", ml: "മലയാളം", mni: "ꯃꯤꯇꯩꯂꯣꯟ", mr: "मराठी", ne: "नेपाली",
  or: "ଓଡ଼ିଆ", pa: "ਪੰਜਾਬੀ", sa: "संस्कृतम्", sat: "ᱥᱟᱱᱛᱟᱲᱤ", sd: "سنڌي",
  ta: "தமிழ்", te: "తెలుగు", ur: "اردو",
}

/**
 * Normalise `/api/v1/avatar/languages` into the view model.
 *
 * The runtime returns a dict (`{ languages: { hi: "Hindi" } }`). Older code
 * assumed an array and called `.map()` on it, which threw a TypeError and
 * hard-crashed the voice step. Tolerates both shapes.
 */
export function toLanguageList(res: unknown): Language[] {
  const dict = (res as { languages?: Record<string, string> })?.languages
  if (dict && typeof dict === "object" && !Array.isArray(dict)) {
    return Object.entries(dict)
      .map(([code, name]) => ({ code, name, native: NATIVE_NAMES[code] ?? name }))
      .sort((a, b) => a.name.localeCompare(b.name))
  }
  if (Array.isArray(res)) return res as Language[]
  return []
}

async function pollUntil<T>(
  fn: () => Promise<T>,
  done: (v: T) => boolean,
  { tries = 60, intervalMs = 1500 }: { tries?: number; intervalMs?: number } = {},
): Promise<T> {
  let last = await fn()
  let n = 0
  while (!done(last) && n < tries) {
    await new Promise((r) => setTimeout(r, intervalMs))
    last = await fn()
    n++
  }
  return last
}

/* eslint-disable @typescript-eslint/no-explicit-any */
export function useCreateTwin() {
  const [authed, setAuthed] = useState<boolean | null>(null)
  const [step, setStep] = useState<Step>("consent")

  const [name, setName] = useState("")
  const [consent, setConsent] = useState(false)

  const [twinId, setTwinId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Identity
  const [faceFile, setFaceFile] = useState<File | null>(null)
  const [facePreviewUrl, setFacePreviewUrl] = useState<string | null>(null)
  const [faceStatus, setFaceStatus] = useState<PhaseStatus>("idle")
  const [faceResult, setFaceResult] = useState<FaceResult | null>(null)

  // Voice
  const [voiceUrl, setVoiceUrl] = useState<string | null>(null)
  const [voiceDuration, setVoiceDuration] = useState(0)
  const [voiceStatus, setVoiceStatus] = useState<PhaseStatus>("idle")
  const [voiceResult, setVoiceResult] = useState<VoiceResult | null>(null)

  // Languages
  const [languages, setLanguages] = useState<Language[]>([])
  // Must match the runtime's codes ("en", "hi", …) — "en-IN" matched nothing,
  // so the default language never appeared selected in the picker.
  const [selectedLangs, setSelectedLangs] = useState<string[]>(["en"])

  // Processing
  const [pipeline, setPipeline] = useState<Pipeline | null>(null)

  const blobUrls = useRef<string[]>([])
  const voiceBlobRef = useRef<Blob | null>(null)
  const faceFileRef = useRef<File | null>(null)
  const track = (url: string) => { blobUrls.current.push(url); return url }

  useEffect(() => {
    setAuthed(!!getAccessToken())
  }, [])

  useEffect(() => {
    let alive = true
    avatarApi.languages()
      .then((l) => alive && setLanguages(toLanguageList(l)))
      .catch(() => { /* backend offline — languages stay empty, surfaced in UI */ })
    return () => { alive = false }
  }, [])

  useEffect(() => () => { blobUrls.current.forEach(URL.revokeObjectURL) }, [])

  const primaryLang = () => (selectedLangs[0]?.split("-")[0] || "en")

  // Step 0 → create the twin, then enter identity.
  const beginCreation = useCallback(async () => {
    setError(null)
    setBusy(true)
    try {
      const twin: any = await digitalTwinApi.create({
        name: name.trim() || "My Twin",
        description: "Created with DreamTalk",
      })
      setTwinId(twin.id ?? twin.twin_id)
      setStep("identity")
    } catch (e: any) {
      setError(e?.message?.includes("Failed to fetch") || e?.message?.includes("HTTP")
        ? "Couldn't reach the backend. Make sure the DreamTalk API is running."
        : e?.message || "Could not create your twin.")
    } finally {
      setBusy(false)
    }
  }, [name, selectedLangs])

  const analyzeFace = useCallback(async (file: File) => {
    if (!twinId) return
    faceFileRef.current = file
    const url = track(URL.createObjectURL(file))
    setFaceFile(file)
    setFacePreviewUrl(url)
    setFaceStatus("uploading")
    setFaceResult(null)
    setError(null)
    try {
      const form = new FormData()
      form.append("files", file)
      await digitalTwinApi.uploadAppearance(twinId, form)
      setFaceStatus("analyzing")
      const res: any = await pollUntil(
        () => digitalTwinApi.getAppearanceResult(twinId),
        (r: any) => isOk(r?.status) || isFail(r?.status) || r?.face_detected === true,
      )
      setFaceResult({
        faceDetected: !!res.face_detected,
        quality: res.quality_score ?? 0,
        previewUrl: res.preview_url,
        statusRaw: res.status,
      })
      setFaceStatus(isFail(res.status) || res.face_detected === false ? "error" : "done")
    } catch (e: any) {
      setFaceStatus("error")
      setError(e?.message || "Face analysis failed.")
    }
  }, [twinId])

  const clearFace = useCallback(() => {
    setFaceFile(null); setFacePreviewUrl(null); setFaceStatus("idle"); setFaceResult(null)
  }, [])

  const setVoice = useCallback(async (blob: Blob, durationSec: number) => {
    if (!twinId) return
    voiceBlobRef.current = blob
    const url = track(URL.createObjectURL(blob))
    setVoiceUrl(url)
    setVoiceDuration(durationSec)
    setVoiceStatus("uploading")
    setVoiceResult(null)
    setError(null)
    try {
      const form = new FormData()
      form.append("files", blob, "voice-sample.webm")
      await digitalTwinApi.uploadVoice(twinId, form)
      setVoiceStatus("analyzing")
      const res: any = await pollUntil(
        () => digitalTwinApi.getVoiceResult(twinId),
        (r: any) => isOk(r?.status) || isFail(r?.status) || r?.is_cloned === true,
      )
      setVoiceResult({
        isCloned: !!res.is_cloned,
        isSynthetic: !!res.is_synthetic,
        quality: res.quality_score ?? 0,
        statusRaw: res.status,
      })
      setVoiceStatus(isFail(res.status) ? "error" : "done")
    } catch (e: any) {
      setVoiceStatus("error")
      setError(e?.message || "Voice processing failed.")
    }
  }, [twinId])

  const clearVoice = useCallback(() => {
    setVoiceUrl(null); setVoiceDuration(0); setVoiceStatus("idle"); setVoiceResult(null)
  }, [])

  const toggleLang = useCallback((code: string) => {
    setSelectedLangs((prev) => prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code])
  }, [])

  const startProcessing = useCallback(async () => {
    if (!twinId) return
    setStep("processing")
    setError(null)
    try {
      await digitalTwinApi.update(twinId, { language: primaryLang() }).catch(() => {})
      await digitalTwinApi.runPipeline(twinId)
      const final: any = await pollUntil(
        () => digitalTwinApi.getPipelineStatus(twinId),
        (r: any) => isOk(r?.status) || isFail(r?.status),
        { tries: 120, intervalMs: 2000 },
      )
      setPipeline({
        status: final.status,
        progress: final.progress ?? (isOk(final.status) ? 100 : 0),
        stage: final.stage ?? final.status,
      })
      if (isFail(final.status)) {
        setError("Avatar processing failed. Please try again.")
      } else {
        // Best-effort: register a runtime profile so /talk has a digital human
        // to speak with. Failure here never blocks the twin preview.
        if (voiceBlobRef.current) {
          try {
            await avatarRuntime.createProfile({
              name: name.trim() || "My Twin",
              voiceSample: voiceBlobRef.current,
              faceImages: faceFileRef.current ? [faceFileRef.current] : [],
              consentConfirmed: consent,
              consentSubjectName: name.trim() || undefined,
              language: primaryLang(),
            })
          } catch { /* runtime profile is optional; preview still proceeds */ }
        }
        setStep("preview")
      }
    } catch (e: any) {
      setError(e?.message || "Processing failed.")
    }
  }, [twinId, selectedLangs, name, consent])

  // Live-ish progress display while the pipeline runs.
  useEffect(() => {
    if (step !== "processing" || !twinId) return
    let alive = true
    const id = setInterval(async () => {
      try {
        const s: any = await digitalTwinApi.getPipelineStatus(twinId)
        if (alive) setPipeline({ status: s.status, progress: s.progress ?? 0, stage: s.stage ?? s.status })
      } catch { /* ignore */ }
    }, 2000)
    return () => { alive = false; clearInterval(id) }
  }, [step, twinId])

  const canProceed: Record<Step, boolean> = {
    consent: consent && name.trim().length > 0 && authed === true && !busy,
    identity: faceStatus === "done",
    voice: voiceStatus === "done" && selectedLangs.length > 0,
    processing: pipeline ? isOk(pipeline.status) : false,
    preview: true,
  }

  const goNext = useCallback(() => setStep((s) => STEP_ORDER[Math.min(STEP_ORDER.length - 1, STEP_ORDER.indexOf(s) + 1)]), [])
  const goBack = useCallback(() => setStep((s) => STEP_ORDER[Math.max(1, STEP_ORDER.indexOf(s) - 1)]), [])

  return {
    authed, step, setStep, goNext, goBack, canProceed,
    name, setName, consent, setConsent, busy, error, twinId, beginCreation,
    faceFile, facePreviewUrl, faceStatus, faceResult, analyzeFace, clearFace,
    voiceUrl, voiceDuration, voiceStatus, voiceResult, setVoice, clearVoice,
    languages, selectedLangs, toggleLang,
    pipeline, startProcessing, isOk,
  }
}
/* eslint-enable @typescript-eslint/no-explicit-any */
