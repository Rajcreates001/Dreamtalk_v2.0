// Dreamtalk - Live2D Emotion Mapping
// Based on PersonaEngine EmotionAnimationService (MIT License)
// Source: handcrafted-persona-engine

export interface EmotionMapping {
  expressionId: string | null
  motionGroup: string | null
}

export const EMOTION_MAP: Record<string, EmotionMapping> = {
  "😊": { expressionId: "happy", motionGroup: "Happy" },
  "🤩": { expressionId: "excited_star", motionGroup: "Excited" },
  "😎": { expressionId: "cool", motionGroup: "Confident" },
  "😏": { expressionId: "smug", motionGroup: "Confident" },
  "💪": { expressionId: "determined", motionGroup: "Confident" },
  "😳": { expressionId: "embarrassed", motionGroup: "Nervous" },
  "😲": { expressionId: "shocked", motionGroup: "Surprised" },
  "🤔": { expressionId: "thinking", motionGroup: "Thinking" },
  "👀": { expressionId: "suspicious", motionGroup: "Thinking" },
  "😤": { expressionId: "frustrated", motionGroup: "Angry" },
  "😢": { expressionId: "sad", motionGroup: "Sad" },
  "😅": { expressionId: "awkward", motionGroup: "Nervous" },
  "🙄": { expressionId: "dismissive", motionGroup: "Annoyed" },
  "💕": { expressionId: "adoring", motionGroup: "Happy" },
  "😂": { expressionId: "laughing", motionGroup: "Happy" },
  "🔥": { expressionId: "passionate", motionGroup: "Excited" },
  "✨": { expressionId: "sparkle", motionGroup: "Happy" },
}
