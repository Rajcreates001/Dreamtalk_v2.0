// Dreamtalk - Live2D Animation
// Based on PersonaEngine ILive2DModel (MIT License)
// Source: handcrafted-persona-engine

import { type PhonemePose } from "./phoneme-pose"
import { type EmotionMapping } from "./emotion-map"

export interface Live2DModel {
  modelId: string
  setParameter(paramName: string, value: number): void
  setExpression(expressionId: string): void
  startRandomMotion(motionGroup: string): boolean
  update(deltaTime: number): void
  draw(): void
  setPosition(x: number, y: number): void
  setScale(scale: number): void
  setRotation(rotation: number): void
  getAvailableExpressions(): string[]
  getAvailableMotionGroups(): string[]
}

export class CubismLive2DModel implements Live2DModel {
  modelId: string
  private coreModel: any = null
  private expressions: string[] = []
  private motionGroups: string[] = []

  constructor(modelId: string) {
    this.modelId = modelId
  }

  async load(url: string): Promise<void> {
    const { Live2DCubismFramework } = await import("@live2d/cubism")
    this.coreModel = new Live2DCubismFramework.Model()
    await this.coreModel.load(url)
    this.expressions = this.coreModel.getExpressions() ?? []
    this.motionGroups = this.coreModel.getMotionGroups() ?? []
  }

  setParameter(paramName: string, value: number): void {
    this.coreModel?.setParameterValue(paramName, value)
  }

  setExpression(expressionId: string): void {
    this.coreModel?.setExpression(expressionId)
  }

  startRandomMotion(motionGroup: string): boolean {
    return this.coreModel?.startRandomMotion(motionGroup, 2) ?? false
  }

  update(deltaTime: number): void {
    this.coreModel?.update(deltaTime)
  }

  draw(): void {
    this.coreModel?.draw()
  }

  setPosition(x: number, y: number): void {
    this.coreModel?.setPosition(x, y)
  }

  setScale(scale: number): void {
    this.coreModel?.setScale(scale)
  }

  setRotation(rotation: number): void {
    this.coreModel?.setRotation(rotation)
  }

  getAvailableExpressions(): string[] {
    return this.expressions
  }

  getAvailableMotionGroups(): string[] {
    return this.motionGroups
  }

  dispose(): void {
    this.coreModel?.release()
    this.coreModel = null
  }
}

export interface TimedPhoneme {
  phoneme: string
  startTime: number
  endTime: number
}

export interface EmotionTiming {
  emoji: string
  timestamp: number
}
