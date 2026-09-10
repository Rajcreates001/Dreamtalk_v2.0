"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import {
  avatarService,
  faceService,
  jobService,
  systemService,
  voiceService,
  type Avatar,
  type FaceAnalysis,
  type Job,
  type Language,
  type VoiceAnalysis,
} from "@/services"

export type Step = "consent" | "identity" | "voice" | "processing" | "preview"
export const STEP_ORDER: Step[] = ["consent", "identity", "voice", "processing", "preview"]

export function useCreateTwin() {
  const [step, setStep] = useState<Step>("consent")

  const [name, setName] = useState("")
  const [consent, setConsent] = useState(false)

  // Identity
  const [faceFile, setFaceFile] = useState<File | null>(null)
  const [facePreviewUrl, setFacePreviewUrl] = useState<string | null>(null)
  const [faceStatus, setFaceStatus] = useState<"idle" | "scanning" | "done" | "error">("idle")
  const [faceAnalysis, setFaceAnalysis] = useState<FaceAnalysis | null>(null)

  // Voice
  const [voiceUrl, setVoiceUrl] = useState<string | null>(null)
  const [voiceDuration, setVoiceDuration] = useState(0)
  const [voiceStatus, setVoiceStatus] = useState<"idle" | "analyzing" | "done" | "error">("idle")
  const [voiceAnalysis, setVoiceAnalysis] = useState<VoiceAnalysis | null>(null)
  const voiceBlobRef = useRef<Blob | null>(null)

  // Languages
  const [languages, setLanguages] = useState<Language[]>([])
  const [selectedLangs, setSelectedLangs] = useState<string[]>(["en-IN"])

  // Processing
  const [job, setJob] = useState<Job | null>(null)
  const [avatar, setAvatar] = useState<Avatar | null>(null)

  useEffect(() => {
    let alive = true
    systemService.languages().then((l) => alive && setLanguages(l)).catch(() => {})
    return () => {
      alive = false
    }
  }, [])

  // Clean up any object URLs.
  useEffect(() => () => {
    if (facePreviewUrl) URL.revokeObjectURL(facePreviewUrl)
    if (voiceUrl) URL.revokeObjectURL(voiceUrl)
  }, [facePreviewUrl, voiceUrl])

  const analyzeFace = useCallback(async (file: File) => {
    if (facePreviewUrl) URL.revokeObjectURL(facePreviewUrl)
    setFaceFile(file)
    setFacePreviewUrl(URL.createObjectURL(file))
    setFaceStatus("scanning")
    setFaceAnalysis(null)
    try {
      const result = await faceService.analyze(file)
      setFaceAnalysis(result)
      setFaceStatus(result.status === "ready" ? "done" : "error")
    } catch {
      setFaceStatus("error")
      setFaceAnalysis({
        status: "no_face", confidence: 0, faces: 0, quality: "low",
        message: "Could not analyze the image. Try another photo.",
      })
    }
  }, [facePreviewUrl])

  const clearFace = useCallback(() => {
    if (facePreviewUrl) URL.revokeObjectURL(facePreviewUrl)
    setFaceFile(null)
    setFacePreviewUrl(null)
    setFaceStatus("idle")
    setFaceAnalysis(null)
  }, [facePreviewUrl])

  const setVoice = useCallback(async (blob: Blob, durationSec: number) => {
    voiceBlobRef.current = blob
    if (voiceUrl) URL.revokeObjectURL(voiceUrl)
    setVoiceUrl(URL.createObjectURL(blob))
    setVoiceDuration(durationSec)
    setVoiceStatus("analyzing")
    setVoiceAnalysis(null)
    try {
      const result = await voiceService.analyze(blob, durationSec)
      setVoiceAnalysis(result)
      setVoiceStatus(result.status === "ready" ? "done" : "error")
    } catch {
      setVoiceStatus("error")
      setVoiceAnalysis({
        status: "low_quality", durationSec, clarity: 0, quality: "low",
        message: "Could not analyze the audio. Try again.",
      })
    }
  }, [voiceUrl])

  const clearVoice = useCallback(() => {
    voiceBlobRef.current = null
    if (voiceUrl) URL.revokeObjectURL(voiceUrl)
    setVoiceUrl(null)
    setVoiceDuration(0)
    setVoiceStatus("idle")
    setVoiceAnalysis(null)
  }, [voiceUrl])

  const toggleLang = useCallback((code: string) => {
    setSelectedLangs((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code],
    )
  }, [])

  const startProcessing = useCallback(async () => {
    setStep("processing")
    const created = await avatarService.create({
      name: name || "My Twin",
      faceFileName: faceFile?.name,
      voiceFileName: voiceBlobRef.current ? "voice-sample" : undefined,
      languages: selectedLangs,
      consent,
    })
    setAvatar(created)
    let current = await jobService.create(created.avatarId)
    setJob(current)
    // Poll until terminal.
    while (current.status === "processing" || current.status === "queued") {
      current = await jobService.get(current.jobId)
      setJob({ ...current })
    }
    if (current.status === "completed") {
      const refreshed = await avatarService.get(created.avatarId)
      if (refreshed) setAvatar(refreshed)
      setStep("preview")
    }
  }, [name, faceFile, selectedLangs, consent])

  const canProceed: Record<Step, boolean> = {
    consent: consent && name.trim().length > 0,
    identity: faceStatus === "done",
    voice: voiceStatus === "done" && selectedLangs.length > 0,
    processing: job?.status === "completed",
    preview: true,
  }

  const goNext = useCallback(() => {
    setStep((s) => {
      const i = STEP_ORDER.indexOf(s)
      return STEP_ORDER[Math.min(STEP_ORDER.length - 1, i + 1)]
    })
  }, [])
  const goBack = useCallback(() => {
    setStep((s) => {
      const i = STEP_ORDER.indexOf(s)
      return STEP_ORDER[Math.max(0, i - 1)]
    })
  }, [])

  return {
    step, setStep, goNext, goBack, canProceed,
    name, setName, consent, setConsent,
    faceFile, facePreviewUrl, faceStatus, faceAnalysis, analyzeFace, clearFace,
    voiceUrl, voiceDuration, voiceStatus, voiceAnalysis, setVoice, clearVoice,
    languages, selectedLangs, toggleLang,
    job, avatar, startProcessing,
  }
}
