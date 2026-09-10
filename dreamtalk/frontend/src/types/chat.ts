export interface Message {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  timestamp: number
  audioUrl?: string
  videoUrl?: string
  emotion?: string
}

export interface PipelineResult {
  status: "idle" | "processing" | "done" | "error"
  pipelineId?: string
  videoUrl?: string
  audioUrl?: string
  progress?: number
  error?: string
}

export interface ChatSession {
  id: string
  messages: Message[]
  createdAt: number
  updatedAt: number
}

export interface AvatarState {
  expression: string
  gesture: string
  speaking: boolean
  blinkRate: number
}

export interface EmotionState {
  valence: number
  arousal: number
  dominance: number
  primary: string
  secondary?: string
}

export interface TTSConfig {
  model: string
  voice: string
  speed: number
  pitch: number
}

export interface LLMConfig {
  model: string
  temperature: number
  maxTokens: number
  systemPrompt: string
}

export interface PersonaConfig {
  name: string
  title: string
  description: string
  avatar: string
  llm: LLMConfig
  tts: TTSConfig
  emotion: {
    empathyLevel: number
    expressiveness: number
  }
}
