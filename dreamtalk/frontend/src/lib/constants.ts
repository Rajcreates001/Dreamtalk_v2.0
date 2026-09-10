export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5001"
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:5001/ws/chat"

// Auth token management
let _authToken: string | null = null
export function setAuthToken(token: string | null) { _authToken = token }export function getAuthToken(): string | null {
    if (typeof window !== "undefined") {
      return _authToken || localStorage.getItem("access_token") || localStorage.getItem("dreamtalk_token")
    }
    return _authToken
  }

export const AVATAR_MODES = ["3d", "video", "image"] as const
export type AvatarMode = (typeof AVATAR_MODES)[number]

export const VOICE_MODELS = ["gpt-sovits", "openvoice", "chattts", "fish-speech"] as const
export type VoiceModel = (typeof VOICE_MODELS)[number]

export const LLM_MODELS = [
  { id: "qwen3.6-27b", name: "Qwen 3.6 27B", provider: "GPU Server" },
  { id: "gpt-4o", name: "GPT-4o", provider: "OpenAI" },
  { id: "claude-3.5-sonnet", name: "Claude 3.5 Sonnet", provider: "Anthropic" },
] as const
