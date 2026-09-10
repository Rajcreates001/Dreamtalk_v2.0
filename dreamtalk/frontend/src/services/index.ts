// ═══════════════════════════════════════════════════════════════════
// Service facade — the ONLY import surface for feature components.
//
//   import { avatarService, USE_MOCK } from "@/services"
//
// Mock mode is the default so the app is fully walkable with no backend.
// Set NEXT_PUBLIC_USE_MOCK_API="false" to hit the live backend contract
// (see docs/FRONTEND_API_CONTRACT.md).
// ═══════════════════════════════════════════════════════════════════
import {
  mockAvatarService,
  mockFaceService,
  mockJobService,
  mockSpeechService,
  mockSystemService,
  mockVoiceService,
} from "./mock"
import {
  liveAvatarService,
  liveFaceService,
  liveJobService,
  liveSpeechService,
  liveSystemService,
  liveVoiceService,
} from "./live"

export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK_API !== "false"

export const avatarService = USE_MOCK ? mockAvatarService : liveAvatarService
export const faceService = USE_MOCK ? mockFaceService : liveFaceService
export const voiceService = USE_MOCK ? mockVoiceService : liveVoiceService
export const jobService = USE_MOCK ? mockJobService : liveJobService
export const speechService = USE_MOCK ? mockSpeechService : liveSpeechService
export const systemService = USE_MOCK ? mockSystemService : liveSystemService

export * from "./types"
