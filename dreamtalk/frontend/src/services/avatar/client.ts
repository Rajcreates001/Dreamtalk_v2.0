// ═══════════════════════════════════════════════════════════════════
// Avatar Runtime v1 client — the frontend's single door to /api/v1/avatar.
// ═══════════════════════════════════════════════════════════════════
import { getAccessToken } from "@/lib/api"
import type {
  AvatarManifest, AvatarProfile, CreateProfileInput, LanguagesResponse,
  RespondRequest, RespondResult, RuntimeStatus,
} from "./types"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5050"
const BASE = `${API_BASE_URL}/api/v1/avatar`

/** Prefix a signed/relative runtime asset path with the API origin. */
export function assetUrl(url?: string | null): string | undefined {
  if (!url) return undefined
  if (/^https?:\/\//.test(url) || url.startsWith("blob:") || url.startsWith("data:")) return url
  return `${API_BASE_URL}${url.startsWith("/") ? "" : "/"}${url}`
}

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = getAccessToken()
  return { ...extra, ...(token ? { Authorization: `Bearer ${token}` } : {}) }
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error((detail as { detail?: string }).detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const avatarRuntime = {
  status: () => fetch(`${BASE}/status`).then((r) => json<RuntimeStatus>(r)),

  languages: () => fetch(`${BASE}/languages`).then((r) => json<LanguagesResponse>(r)),

  listProfiles: () =>
    fetch(`${BASE}/profiles`, { headers: authHeaders() })
      .then((r) => json<{ profiles: AvatarProfile[]; active_profile_id?: string | null }>(r)),

  getProfile: (id: string) =>
    fetch(`${BASE}/profiles/${id}`, { headers: authHeaders() }).then((r) => json<AvatarProfile>(r)),

  getManifest: (id: string) =>
    fetch(`${BASE}/profiles/${id}/manifest`, { headers: authHeaders() }).then((r) => json<AvatarManifest>(r)),

  activate: (id: string) =>
    fetch(`${BASE}/profiles/${id}/activate`, { method: "POST", headers: authHeaders() })
      .then((r) => json<{ active_profile_id: string }>(r)),

  createProfile: (input: CreateProfileInput) => {
    const form = new FormData()
    form.append("name", input.name)
    form.append("consent_confirmed", String(input.consentConfirmed))
    form.append("consent_subject_name", input.consentSubjectName ?? input.name)
    form.append("reference_text", input.referenceText ?? "")
    form.append("language", input.language ?? "auto")
    form.append("voice_sample", input.voiceSample, "voice-sample.webm")
    input.faceImages.forEach((img, i) => form.append("face_images", img, `face-${i}.jpg`))
    return fetch(`${BASE}/profiles`, { method: "POST", headers: authHeaders(), body: form })
      .then((r) => json<AvatarProfile>(r))
  },

  /** Text → spoken reply (+ optional rendered video). */
  respond: (profileId: string, req: RespondRequest) =>
    fetch(`${BASE}/profiles/${profileId}/respond`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ synthesize: true, strict_clone: true, ...req }),
    }).then((r) => json<RespondResult>(r)),

  /** Compatibility chat against the active profile. */
  chat: (req: RespondRequest) =>
    fetch(`${BASE}/chat`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ synthesize: true, strict_clone: true, ...req }),
    }).then((r) => json<RespondResult>(r)),

  /** Audio in → spoken reply (records mic, ASR + reply). */
  respondAudio: (profileId: string, audio: Blob, opts: { language?: string; renderVideo?: boolean } = {}) => {
    const form = new FormData()
    form.append("audio", audio, "input.webm")
    form.append("language", opts.language ?? "auto")
    form.append("render_video", String(opts.renderVideo ?? false))
    return fetch(`${BASE}/profiles/${profileId}/respond/audio`, {
      method: "POST", headers: authHeaders(), body: form,
    }).then((r) => json<RespondResult>(r))
  },
}

export type { RespondResult, AvatarProfile, AvatarManifest } from "./types"
