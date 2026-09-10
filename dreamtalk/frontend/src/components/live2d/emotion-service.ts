// Dreamtalk - Live2D Animation
// Based on PersonaEngine EmotionAnimationService (MIT License)
// Source: handcrafted-persona-engine

import { EMOTION_MAP, type EmotionMapping } from "./emotion-map"

export const NEUTRAL_EXPRESSION_ID = "neutral"
export const NEUTRAL_TALKING_MOTION_GROUP = "Talking"
export const EXPRESSION_HOLD_DURATION = 3.0

export class EmotionAnimationService {
  private model: any = null
  private activeEmotions: Array<{ emoji: string; timestamp: number }> = []
  private availableExpressions = new Set<string>()
  private availableMotionGroups = new Set<string>()
  private currentEmotionIndex = -1
  private triggeredEmotion: string | null = null
  private activeExpression: string | null = null
  private timeSinceExpressionSet = 0
  private isPlaying = false

  setModel(model: any): void {
    this.model = model
    this.validateModelAssets()
  }

  startPlayback(emotions: Array<{ emoji: string; timestamp: number }>): void {
    this.isPlaying = true
    this.activeEmotions = [...emotions].sort((a, b) => a.timestamp - b.timestamp)
    this.currentEmotionIndex = -1
    this.updateEmotionAtTime(0)
  }

  stopPlayback(): void {
    this.isPlaying = false
    this.activeEmotions = []
    this.currentEmotionIndex = -1
  }

  update(deltaTime: number): void {
    if (!this.model || deltaTime <= 0) return
    this.timeSinceExpressionSet += deltaTime
    this.checkExpressionTimeout()
  }

  updateEmotionAtTime(currentTime: number): void {
    if (this.activeEmotions.length === 0 || !this.isPlaying) return

    let targetIndex = -1
    for (let i = 0; i < this.activeEmotions.length; i++) {
      if (this.activeEmotions[i].timestamp <= currentTime) {
        targetIndex = i
      } else break
    }

    if (targetIndex !== -1 && targetIndex !== this.currentEmotionIndex) {
      this.currentEmotionIndex = targetIndex
      this.applyEmotion(this.activeEmotions[targetIndex].emoji)
    }
  }

  private checkExpressionTimeout(): void {
    if (
      !this.activeExpression ||
      this.activeExpression === NEUTRAL_EXPRESSION_ID ||
      this.timeSinceExpressionSet < EXPRESSION_HOLD_DURATION
    ) return
    this.applyNeutralExpression()
  }

  private applyEmotion(emoji: string): void {
    if (!this.model || emoji === this.triggeredEmotion) return

    this.triggeredEmotion = emoji
    const mapping = EMOTION_MAP[emoji]
    const targetExpression = mapping?.expressionId ?? NEUTRAL_EXPRESSION_ID
    this.setExpression(targetExpression)

    if (mapping?.motionGroup && this.availableMotionGroups.has(mapping.motionGroup)) {
      this.model.startRandomMotion(mapping.motionGroup)
    }
  }

  private setExpression(expressionId: string): void {
    if (!this.model) return
    const id = expressionId || NEUTRAL_EXPRESSION_ID
    if (id === this.activeExpression) return

    if (id === NEUTRAL_EXPRESSION_ID) {
      this.applyNeutralExpression()
    } else if (this.availableExpressions.has(id)) {
      this.model.setExpression(id)
      this.activeExpression = id
      this.timeSinceExpressionSet = 0
    } else {
      this.applyNeutralExpression()
    }
  }

  private applyNeutralExpression(): void {
    if (!this.model) return
    if (this.availableExpressions.has(NEUTRAL_EXPRESSION_ID)) {
      this.model.setExpression(NEUTRAL_EXPRESSION_ID)
    }
    this.activeExpression = NEUTRAL_EXPRESSION_ID
    this.timeSinceExpressionSet = 0
  }

  private validateModelAssets(): void {
    if (!this.model) return
    this.availableExpressions = new Set(this.model.getAvailableExpressions?.() ?? [])
    this.availableMotionGroups = new Set(this.model.getAvailableMotionGroups?.() ?? [])

    if (this.availableExpressions.has(NEUTRAL_EXPRESSION_ID)) {
      this.applyNeutralExpression()
    }
  }
}
