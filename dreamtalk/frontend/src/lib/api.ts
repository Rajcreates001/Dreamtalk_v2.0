export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5050"

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`))
  return match ? decodeURIComponent(match[2]) : null
}

interface RequestOptions {
  method?: string
  body?: unknown
  headers?: Record<string, string>
  auth?: boolean
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {}, auth = false } = options

  const requestHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...headers,
  }

  if (auth) {
    const token = getAccessToken()
    if (token) {
      requestHeaders["Authorization"] = `Bearer ${token}`
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: requestHeaders,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

// Google OAuth
declare const google: {
  accounts: {
    oauth2: {
      initTokenClient: (config: {
        client_id: string
        scope: string
        callback: (response: { access_token: string }) => void
      }) => { requestAccessToken: () => void }
    }
  }
}

// Auth API
export const authApi = {
  signup: (data: { email: string; password: string; full_name: string; role: string }) =>
    request<{ user: any; tokens: { access_token: string; refresh_token: string } }>("/api/v1/auth/signup", {
      method: "POST",
      body: data,
    }),

  login: (data: { email: string; password: string }) =>
    request<{ user: any; tokens: { access_token: string; refresh_token: string } }>("/api/v1/auth/login", {
      method: "POST",
      body: data,
    }),

  me: () =>
    request<any>("/api/v1/auth/me", { auth: true }),

  refresh: (refreshToken: string) =>
    request<{ access_token: string; refresh_token: string }>("/api/v1/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
    }),

  logout: () =>
    request<{ detail: string }>("/api/v1/auth/logout", { method: "POST", auth: true }),

  forgotPassword: (email: string) =>
    request<{ detail: string }>("/api/v1/auth/forgot-password", {
      method: "POST",
      body: { email },
    }),

  resetPassword: (token: string, newPassword: string) =>
    request<{ detail: string }>("/api/v1/auth/reset-password", {
      method: "POST",
      body: { token, new_password: newPassword },
    }),

  googleLogin: (accessToken: string) =>
    request<{ user: any; tokens: { access_token: string; refresh_token: string } }>("/api/v1/auth/google", {
      method: "POST",
      body: { access_token: accessToken },
    }),

  updateProfile: (data: { full_name?: string; avatar_url?: string | null }) =>
    request<any>("/api/v1/auth/profile", { method: "PUT", auth: true, body: data }),
}

// Digital Humans API
export const digitalHumanApi = {
  list: () =>
    request<any[]>("/api/v1/digital-humans", { auth: true }),

  get: (id: string) =>
    request<any>(`/api/v1/digital-humans/${id}`, { auth: true }),

  create: (data: {
    name: string; description?: string; category?: string;
    personality?: string; style?: string; color_scheme?: string;
    outfit?: string; hair_style?: string; eye_glow?: string;
  }) =>
    request<any>("/api/v1/digital-humans", {
      method: "POST", auth: true, body: data,
    }),

  update: (id: string, data: any) =>
    request<any>(`/api/v1/digital-humans/${id}`, {
      method: "PUT", auth: true, body: data,
    }),

  delete: (id: string) =>
    request<{ detail: string }>(`/api/v1/digital-humans/${id}`, {
      method: "DELETE", auth: true,
    }),
}

// Settings API
export const settingsApi = {
  get: () =>
    request<any>("/api/v1/settings", { auth: true }),

  update: (data: any) =>
    request<any>("/api/v1/settings", { method: "PUT", auth: true, body: data }),
}

// Subscription API
export const subscriptionApi = {
  get: () =>
    request<any>("/api/v1/subscription", { auth: true }),
}

// File upload helper (multipart/form-data)
async function uploadFile<T>(path: string, formData: FormData, auth = false): Promise<T> {
  const headers: Record<string, string> = {}
  if (auth) {
    const token = getAccessToken()
    if (token) {
      headers["Authorization"] = `Bearer ${token}`
    }
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: formData,
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Upload failed" }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

// Digital Twins API
export const digitalTwinApi = {
  list: () =>
    request<any[]>("/api/v1/digital-twins", { auth: true }),

  get: (id: string) =>
    request<any>(`/api/v1/digital-twins/${id}`, { auth: true }),

  getFullStatus: (id: string) =>
    request<any>(`/api/v1/digital-twins/${id}/full-status`, { auth: true }),

  create: (data: {
    name: string
    description?: string
    appearance_model?: string
    voice_model?: string
    personality?: string
  }) =>
    request<any>("/api/v1/digital-twins", {
      method: "POST", auth: true, body: data,
    }),

  update: (id: string, data: Record<string, unknown>) =>
    request<any>(`/api/v1/digital-twins/${id}`, {
      method: "PUT", auth: true, body: data,
    }),

  deleteTwin: (id: string) =>
    request<{ detail: string }>(`/api/v1/digital-twins/${id}`, {
      method: "DELETE", auth: true,
    }),

  // Appearance
  uploadAppearance: (twinId: string, formData: FormData) =>
    uploadFile<any>(`/api/v1/digital-twins/${twinId}/appearance/upload`, formData, true),

  getAppearanceResult: (twinId: string) =>
    request<any>(`/api/v1/digital-twins/${twinId}/appearance/result`, { auth: true }),

  // Voice
  uploadVoice: (twinId: string, formData: FormData) =>
    uploadFile<any>(`/api/v1/digital-twins/${twinId}/voice/upload`, formData, true),

  createSyntheticVoice: (twinId: string, data: { gender: string; age: string; region: string; accent?: string; emotion?: string }) =>
    request<any>(`/api/v1/digital-twins/${twinId}/voice/synthetic`, {
      method: "POST", auth: true, body: data,
    }),

  getVoiceResult: (twinId: string) =>
    request<any>(`/api/v1/digital-twins/${twinId}/voice/result`, { auth: true }),

  // Personality
  setPersonality: (twinId: string, data: { traits: string[]; description?: string }) =>
    request<any>(`/api/v1/digital-twins/${twinId}/personality`, {
      method: "PUT", auth: true, body: data,
    }),

  getPersonality: (twinId: string) =>
    request<any>(`/api/v1/digital-twins/${twinId}/personality`, { auth: true }),

  initializePersonality: (twinId: string) =>
    request<any>(`/api/v1/digital-twins/${twinId}/personality/initialize`, {
      method: "POST", auth: true,
    }),

  // Relationship
  setRelationship: (twinId: string, data: { type: string }) =>
    request<any>(`/api/v1/digital-twins/${twinId}/relationship`, {
      method: "PUT", auth: true, body: data,
    }),

  getRelationship: (twinId: string) =>
    request<any>(`/api/v1/digital-twins/${twinId}/relationship`, { auth: true }),

  // Knowledge
  uploadKnowledge: (twinId: string, formData: FormData) =>
    uploadFile<any>(`/api/v1/digital-twins/${twinId}/knowledge/upload`, formData, true),

  getKnowledgeSources: (twinId: string) =>
    request<any[]>(`/api/v1/digital-twins/${twinId}/knowledge/sources`, { auth: true }),

  deleteKnowledgeSource: (twinId: string, sourceId: string) =>
    request<{ detail: string }>(`/api/v1/digital-twins/${twinId}/knowledge/sources/${sourceId}`, {
      method: "DELETE", auth: true,
    }),

  // Pipeline
  // Runs the pipeline for an EXISTING twin and returns the result
  // synchronously. `/api/v1/digital-twins/pipeline` is a different endpoint —
  // it *creates* a twin and requires `name`, so posting {twin_id} there
  // returned 422 and the build never started.
  runPipeline: (twinId: string, role = "personal") =>
    request<{ pipeline_id: string; status: string; error?: string | null }>(
      `/api/v1/pipeline/run`, {
        method: "POST", auth: true,
        body: {
          twin_id: twinId, role,
          enable_3d_face: true, enable_voice_clone: true, enable_emotion: true,
        },
      },
    ),

  getPipelineStatus: (twinId: string) =>
    request<any>(`/api/v1/digital-twins/${twinId}/pipeline/status`, { auth: true }),

  // Publish
  publish: (id: string) =>
    request<any>(`/api/v1/digital-twins/${id}/publish`, {
      method: "POST", auth: true,
    }),

  // Media
  getMediaReport: (twinId: string) =>
    request<any>(`/api/v1/digital-twins/${twinId}/media/report`, { auth: true }),
}

// Pipeline API
export const pipelineApi = {
  run: (data: {
    model: string
    appearance_url?: string
    audio_url?: string
    text?: string
    twin_id?: string
  }) =>
    request<{ pipeline_id: string; status: string }>("/api/v1/pipeline/run", {
      method: "POST", auth: true, body: data,
    }),

  runWithUploads: (formData: FormData) =>
    uploadFile<{ pipeline_id: string; status: string }>("/api/v1/pipeline/run-with-uploads", formData, true),

  faceAnalysis: (formData: FormData) =>
    uploadFile<any>("/api/v1/pipeline/face", formData, true),

  voiceAnalysis: (formData: FormData) =>
    uploadFile<any>("/api/v1/pipeline/voice", formData, true),

  getResult: (pipelineId: string) =>
    request<{
      status: string
      result?: { video_url?: string; audio_url?: string; duration?: number }
      progress?: number
    }>(`/api/v1/pipeline/results/${pipelineId}`, { auth: true }),

  history: (twinId: string) =>
    request<any[]>(`/api/v1/pipeline/history/${twinId}`, { auth: true }),
}

// Chat API
export const chatApi = {
  send: (message: string, history?: any[], twinId?: string) => {
    const body: any = { message, history: history?.slice(-10) }
    if (twinId) body.twin_id = twinId
    return request<{
      response: string
      emotion?: string
      audio_url?: string
      video_url?: string
    }>("/api/chat", {
      method: "POST",
      body,
      auth: true,
    })
  },
}

// Avatar API
export const avatarApi = {
  status: () =>
    request<{
      online: boolean
      current_emotion?: string
      is_speaking?: boolean
      model_loaded?: boolean
    }>("/api/v1/avatar/status", { auth: true }),

  knowledge: () =>
    request<any[]>("/api/v1/avatar/knowledge", { auth: true }),

  // The runtime returns `{ languages: { "hi": "Hindi", ... }, ... }` — a dict,
  // not an array. Typing it as an array made callers do `.map()` on an object,
  // which threw and blocked the create-twin flow. Normalise with
  // `toLanguageList()` in features/create/useCreateTwin.
  languages: () =>
    request<{ languages: Record<string, string>; [k: string]: unknown }>(
      "/api/v1/avatar/languages", { auth: true },
    ),

  setLanguage: (code: string) =>
    request<any>("/api/v1/avatar/language", {
      method: "POST", auth: true, body: { language: code },
    }),

  chat: (message: string, language?: string) =>
    request<{ response: string; emotion?: string; audio_url?: string }>("/api/v1/avatar/chat", {
      method: "POST", auth: true, body: { text: message, language },
    }),

  generateTTS: (data: { text: string; language?: string; emotion?: string; speed?: number }) =>
    request<{ audio_url: string; duration: number }>("/api/v1/avatar/tts/generate", {
      method: "POST", auth: true, body: data,
    }),

  getTTSAudio: (audioPath: string) =>
    `${API_BASE_URL}/api/v1/avatar/tts/audio?path=${encodeURIComponent(audioPath)}`,

  generateScript: (data: { text: string; language: string; emotion?: string; speed?: number }) =>
    request<{ script_id: string; parts: number; audio_url?: string }>("/api/v1/avatar/script/generate", {
      method: "POST", auth: true, body: data,
    }),

  getSession: () =>
    request<any>("/api/v1/avatar/session", { auth: true }),
}

// Voice API
export const voiceApi = {
  status: () =>
    request<{ available: boolean; engines: string[] }>("/api/v1/voice/status", { auth: false }),

  listVoices: () =>
    request<any[]>("/api/v1/voice/voices", { auth: false }),

  listEngines: () =>
    request<string[]>("/api/v1/voice/engines", { auth: false }),

  cloneVoice: (formData: FormData) =>
    uploadFile<{ voice_id: string; status: string }>("/api/v1/voice/clone-voice", formData, false),  generateVoice: (data: { text: string; voice_id: string; emotion?: string; pitch?: number; speed?: number; tone?: string; engine?: string; language?: string }) =>
    request<{ audio_url: string }>("/api/v1/voice/generate-voice", {
      method: "POST",
      auth: false,
      body: data,
    }),
}

// Identity API
export const identityApi = {
  getByUser: () =>
    request<any[]>("/api/v1/identity/by-user", { auth: true }),

  get: (id: string) =>
    request<any>(`/api/v1/identity/${id}`, { auth: true }),

  create: (data: { digital_human_id?: string; custom_dh_id?: string; name: string }) =>
    request<any>("/api/v1/identity", {
      method: "POST", auth: true, body: data,
    }),

  updateAppearance: (id: string, data: { style?: string; outfit?: string; hair_style?: string; eye_glow?: string }) =>
    request<any>(`/api/v1/identity/${id}/appearance`, {
      method: "PUT", auth: true, body: data,
    }),

  updateVoice: (id: string, data: { model?: string; pitch?: number; speed?: number }) =>
    request<any>(`/api/v1/identity/${id}/voice`, {
      method: "PUT", auth: true, body: data,
    }),

  updatePersonality: (id: string, data: { traits: string[]; description?: string }) =>
    request<any>(`/api/v1/identity/${id}/personality`, {
      method: "PUT", auth: true, body: data,
    }),

  uploadAppearance: (id: string, formData: FormData) =>
    uploadFile<any>(`/api/v1/identity/${id}/appearance/upload`, formData, true),

  analyzeAppearance: (id: string) =>
    request<any>(`/api/v1/identity/${id}/appearance/analyze`, {
      method: "POST", auth: true,
    }),
}

// Social login redirect helpers
export function loginWithGoogle() {
  window.location.href = `${API_BASE_URL}/api/v1/auth/google/login`
}

export function loginWithGitHub() {
  window.location.href = `${API_BASE_URL}/api/v1/auth/github/login`
}

export function loginWithMicrosoft() {
  window.location.href = `${API_BASE_URL}/api/v1/auth/microsoft/login`
}

// Helper to store auth tokens
export function storeAuth(tokens: { access_token: string; refresh_token: string }) {
  localStorage.setItem("access_token", tokens.access_token)
  localStorage.setItem("refresh_token", tokens.refresh_token)
}

export function clearAuth() {
  localStorage.removeItem("access_token")
  localStorage.removeItem("refresh_token")
  localStorage.removeItem("user")
}

export function getAccessToken(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem("access_token") || getCookie("access_token")
  }
  return null
}
