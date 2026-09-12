// ═══════════════════════════════════════════════════════════════════
// Avatar Runtime v1 — typed contracts for /api/v1/avatar/*
// Mirrors dreamtalk/backend/api/v1/endpoints/avatar_runtime.py exactly.
// ═══════════════════════════════════════════════════════════════════

/** One mouth-shape keyframe from the lip-sync pipeline (audio-aligned). */
export interface VisemeKeyframe {
  timestamp: number   // seconds from clip start
  duration: number    // seconds
  viseme: string       // e.g. "aa", "OH", "SIL"
  mouth_open: number   // 0..1
  mouth_width: number  // 0..1
  lip_round: number    // 0..1
  jaw_drop: number     // 0..1
}

export interface LanguageInfo {
  input?: Record<string, unknown>
  response: string
  name: string
  response_was_translated: boolean
}

/** Rendered 2D talking-head video (only present when render_video=true). */
export interface AvatarVideo {
  video_url?: string
  duration?: number
  [k: string]: unknown
}

export interface AvatarAudio {
  audio_url?: string
  duration?: number
  /** false when the runtime fell back to a stand-in voice (e.g. the clone
   *  engine does not cover this language yet). Always surface this. */
  cloned?: boolean
  engine?: string
  fallback_reason?: string
  [k: string]: unknown
}

/** Result of POST /profiles/{id}/respond (and /chat, /respond/audio). */
export interface RespondResult {
  response: string
  text: string
  profile_id: string | null
  language: LanguageInfo
  user_emotion?: string
  response_emotion?: string
  emotion: string
  audio: AvatarAudio | null
  audio_url: string | null
  lipsync: VisemeKeyframe[]
  lipsync_duration: number
  animation?: Record<string, unknown>
  video: AvatarVideo | null
  processing_ms?: number
  transcription?: { text: string; language?: string; [k: string]: unknown }
}

export interface AvatarAppearance {
  primary_image_url?: string
  mesh_url?: string
  glb_url?: string
  texture_url?: string
  render_modes?: string[]
  /** Morph targets actually baked into the GLB (visemes + blink + emotions).
   *  Empty means the head is a static bust and must not be driven. */
  blendshape_names?: string[]
  capabilities?: {
    talkinghead_2d?: boolean
    realtime_3d?: boolean
    browser_glb?: boolean
    arkit_blendshapes?: boolean
    vrm_expressions?: boolean
    visemes?: string[]
    animation_driver?: string
    [k: string]: unknown
  }
  [k: string]: unknown
}

export interface AvatarVoice {
  reference_audio_url?: string
  sample_language?: string
  is_cloned?: boolean
  [k: string]: unknown
}

export interface AvatarProfile {
  id: string
  name: string
  appearance?: AvatarAppearance
  voice?: AvatarVoice
  [k: string]: unknown
}

export interface AvatarManifest {
  profile: AvatarProfile
  render: AvatarAppearance
  realtime: { websocket: string; chat: string; audio_chat: string }
}

export interface RuntimeStatus {
  [k: string]: unknown
}

export interface LanguagesResponse {
  languages: Record<string, string>
  automatic_detection: boolean
  voice_clone_engine: string
  voice_clone_languages: Record<string, string>
  [k: string]: unknown
}

/** Request body for text respond / chat. */
export interface RespondRequest {
  message: string
  language?: string
  history?: Array<{ role: string; content: string }>
  synthesize?: boolean
  strict_clone?: boolean
  render_video?: boolean
}

export interface CreateProfileInput {
  name: string
  voiceSample: Blob
  faceImages: Blob[]
  consentConfirmed: boolean
  consentSubjectName?: string
  referenceText?: string
  language?: string
}
