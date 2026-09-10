// ═══════════════════════════════════════════════════════════════════
// DreamTalk Astra — Frontend API contracts (typed)
// These interfaces are the boundary the backend (Codex) implements.
// See docs/FRONTEND_API_CONTRACT.md.
// ═══════════════════════════════════════════════════════════════════

// ── Languages ──────────────────────────────────────────────────────
export interface Language {
  /** BCP-47 code, e.g. "en-IN", "hi-IN" */
  code: string
  /** English name, e.g. "Hindi" */
  name: string
  /** Native script name, e.g. "हिन्दी" */
  native: string
}

// ── Face / identity analysis ───────────────────────────────────────
export type FaceQuality = "low" | "fair" | "good" | "excellent"

export type FaceStatus =
  | "idle"
  | "scanning"
  | "detected"
  | "multiple_faces"
  | "no_face"
  | "low_quality"
  | "ready"

export interface FaceAnalysis {
  status: FaceStatus
  /** 0..1 detection confidence */
  confidence: number
  faces: number
  quality: FaceQuality
  resolution?: { width: number; height: number }
  pose?: { yaw: number; pitch: number; roll: number }
  lighting?: "poor" | "uneven" | "good"
  message?: string
}

// ── Voice analysis ─────────────────────────────────────────────────
export type VoiceStatus = "idle" | "analyzing" | "too_short" | "low_quality" | "ready"

export interface VoiceAnalysis {
  status: VoiceStatus
  durationSec: number
  /** 0..1 signal clarity */
  clarity: number
  quality: FaceQuality
  sampleRate?: number
  message?: string
}

// ── Processing job (§46) ───────────────────────────────────────────
export type JobStage =
  | "queued"
  | "face_analysis"
  | "reconstruction"
  | "voice_processing"
  | "speaker_profile"
  | "avatar_preparation"
  | "done"

export type JobStatus = "queued" | "processing" | "completed" | "failed"

export interface Job {
  jobId: string
  status: JobStatus
  /** 0..100 */
  progress: number
  stage: JobStage
  error?: string
  /** technical transparency panel (§24) */
  meta?: {
    device?: string
    gpu?: string
    model?: string
    inferenceMs?: number
    resolution?: string
  }
  avatarId?: string
}

// ── Avatar (§44) ───────────────────────────────────────────────────
export type AvatarStatus = "draft" | "processing" | "ready" | "failed"

export interface Avatar {
  avatarId: string
  name: string
  modelUrl?: string
  textureUrl?: string
  thumbnailUrl?: string
  voiceId?: string
  languages: string[]
  status: AvatarStatus
  createdAt: string
  visualIdentity: boolean
  voiceIdentity: boolean
}

export interface CreateAvatarInput {
  name: string
  faceFileName?: string
  voiceFileName?: string
  languages: string[]
  consent: boolean
}

// ── Speech (§45) ───────────────────────────────────────────────────
export type Emotion =
  | "neutral"
  | "happy"
  | "sad"
  | "excited"
  | "thoughtful"
  | "surprised"

export interface SpeakRequest {
  text: string
  language: string
  emotion: Emotion
  emotionIntensity: number // 0..1
}

export interface SpeakResult {
  audioUrl: string
  animationUrl?: string
  durationSec: number
  /** optional viseme track for lip sync (§69) */
  visemes?: Array<{ time: number; viseme: string; weight: number }>
}

// ── Model / system status (§38, §39) ───────────────────────────────
export type ModelState = "installed" | "missing" | "loading" | "ready"

export interface ModelStatus {
  key: string
  name: string
  state: ModelState
  sizeMb?: number
}

export interface SystemStatus {
  backend: "online" | "offline" | "mock"
  gpu?: string
  vramGb?: number
  cuda?: boolean
  models: ModelStatus[]
}
