// ═══════════════════════════════════════════════════════════════════
// Mock data — ISOLATED. Only used when NEXT_PUBLIC_USE_MOCK_API !== "false".
// Never import this from production components directly; go through the
// service facade in src/services/index.ts.
// ═══════════════════════════════════════════════════════════════════
import type { Avatar, Language, ModelStatus, SystemStatus } from "../types"

export const MOCK_LANGUAGES: Language[] = [
  { code: "en-IN", name: "English (India)", native: "English" },
  { code: "hi-IN", name: "Hindi", native: "हिन्दी" },
  { code: "kn-IN", name: "Kannada", native: "ಕನ್ನಡ" },
  { code: "ta-IN", name: "Tamil", native: "தமிழ்" },
  { code: "te-IN", name: "Telugu", native: "తెలుగు" },
  { code: "ml-IN", name: "Malayalam", native: "മലയാളം" },
  { code: "mr-IN", name: "Marathi", native: "मराठी" },
  { code: "bn-IN", name: "Bengali", native: "বাংলা" },
  { code: "gu-IN", name: "Gujarati", native: "ગુજરાતી" },
  { code: "pa-IN", name: "Punjabi", native: "ਪੰਜਾਬੀ" },
  { code: "or-IN", name: "Odia", native: "ଓଡ଼ିଆ" },
  { code: "as-IN", name: "Assamese", native: "অসমীয়া" },
]

export const MOCK_MODELS: ModelStatus[] = [
  { key: "face", name: "Face Reconstruction", state: "ready", sizeMb: 512 },
  { key: "voice", name: "Voice Encoder", state: "ready", sizeMb: 340 },
  { key: "tts", name: "IndicF5 TTS", state: "ready", sizeMb: 1240 },
  { key: "lipsync", name: "Lip Sync", state: "installed", sizeMb: 210 },
]

export const MOCK_SYSTEM: SystemStatus = {
  backend: "mock",
  gpu: "NVIDIA RTX (mock)",
  vramGb: 16,
  cuda: true,
  models: MOCK_MODELS,
}

export const MOCK_AVATARS: Avatar[] = [
  {
    avatarId: "astra-demo-1",
    name: "Aarav",
    languages: ["en-IN", "hi-IN"],
    status: "ready",
    createdAt: "2026-08-21T10:00:00Z",
    visualIdentity: true,
    voiceIdentity: true,
    thumbnailUrl: "/images/avatar-1.jpg",
  },
  {
    avatarId: "astra-demo-2",
    name: "Meera",
    languages: ["en-IN", "ta-IN", "ml-IN"],
    status: "ready",
    createdAt: "2026-08-29T14:30:00Z",
    visualIdentity: true,
    voiceIdentity: true,
    thumbnailUrl: "/images/avatar-2.jpg",
  },
]

export const delay = (ms: number) => new Promise<void>((r) => setTimeout(r, ms))
