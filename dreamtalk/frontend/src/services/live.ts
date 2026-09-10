// ═══════════════════════════════════════════════════════════════════
// Live service implementations — hit the backend contract endpoints
// (see docs/FRONTEND_API_CONTRACT.md). Used when NEXT_PUBLIC_USE_MOCK_API
// === "false". Backend (Codex) owns these routes; the frontend only maps
// the wire shape onto the typed contracts.
// ═══════════════════════════════════════════════════════════════════
import type {
  Avatar,
  CreateAvatarInput,
  FaceAnalysis,
  Job,
  Language,
  SpeakRequest,
  SpeakResult,
  SystemStatus,
  VoiceAnalysis,
} from "./types"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5001"

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
async function upload<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, { method: "POST", body: form })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

/* eslint-disable @typescript-eslint/no-explicit-any */
const mapAvatar = (a: any): Avatar => ({
  avatarId: a.avatar_id ?? a.id,
  name: a.name,
  modelUrl: a.model_url,
  textureUrl: a.texture_url,
  thumbnailUrl: a.thumbnail_url,
  voiceId: a.voice_id,
  languages: a.languages ?? [],
  status: a.status ?? "draft",
  createdAt: a.created_at ?? new Date().toISOString(),
  visualIdentity: !!a.visual_identity,
  voiceIdentity: !!a.voice_identity,
})

const mapJob = (j: any): Job => ({
  jobId: j.job_id ?? j.id,
  status: j.status,
  progress: j.progress ?? 0,
  stage: j.stage ?? "queued",
  error: j.error,
  avatarId: j.avatar_id,
  meta: j.meta,
})

export const liveSystemService = {
  status: () => get<any>("/api/system/status").then((s): SystemStatus => ({
    backend: "online",
    gpu: s.gpu,
    vramGb: s.vram_gb,
    cuda: s.cuda,
    models: (s.models ?? []).map((m: any) => ({
      key: m.key, name: m.name, state: m.state, sizeMb: m.size_mb,
    })),
  })),
  languages: () => get<any[]>("/api/languages").then((rows) =>
    rows.map((l): Language => ({ code: l.code, name: l.name, native: l.native }))),
}

export const liveAvatarService = {
  list: () => get<any[]>("/api/avatars").then((r) => r.map(mapAvatar)),
  get: (id: string) => get<any>(`/api/avatars/${id}`).then(mapAvatar),
  create: (input: CreateAvatarInput) =>
    post<any>("/api/avatars", {
      name: input.name,
      languages: input.languages,
      consent: input.consent,
    }).then(mapAvatar),
  remove: (id: string) => fetch(`${API_BASE_URL}/api/avatars/${id}`, { method: "DELETE" }).then(() => undefined),
}

export const liveFaceService = {
  analyze: (file: File) => {
    const form = new FormData()
    form.append("file", file)
    return upload<any>("/api/analyze/face", form).then((f): FaceAnalysis => ({
      status: f.status, confidence: f.confidence, faces: f.faces,
      quality: f.quality, resolution: f.resolution, pose: f.pose,
      lighting: f.lighting, message: f.message,
    }))
  },
}

export const liveVoiceService = {
  analyze: (blob: Blob, durationSec: number) => {
    const form = new FormData()
    form.append("file", blob)
    form.append("duration", String(durationSec))
    return upload<any>("/api/analyze/voice", form).then((v): VoiceAnalysis => ({
      status: v.status, durationSec: v.duration_sec ?? durationSec,
      clarity: v.clarity, quality: v.quality, sampleRate: v.sample_rate, message: v.message,
    }))
  },
}

export const liveJobService = {
  create: (avatarId: string) => post<any>("/api/jobs", { avatar_id: avatarId }).then(mapJob),
  get: (jobId: string) => get<any>(`/api/jobs/${jobId}`).then(mapJob),
}

export const liveSpeechService = {
  speak: (avatarId: string, req: SpeakRequest) =>
    post<any>(`/api/avatars/${avatarId}/speak`, {
      text: req.text,
      language: req.language,
      emotion: req.emotion,
      emotion_intensity: req.emotionIntensity,
    }).then((r): SpeakResult => ({
      audioUrl: r.audio_url, animationUrl: r.animation_url,
      durationSec: r.duration ?? r.duration_sec ?? 0, visemes: r.visemes,
    })),
}
/* eslint-enable @typescript-eslint/no-explicit-any */
