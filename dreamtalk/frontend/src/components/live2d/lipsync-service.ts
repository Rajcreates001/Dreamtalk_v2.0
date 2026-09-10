// Dreamtalk - Live2D Animation
// Based on PersonaEngine VBridgerLipSyncService (MIT License)
// Source: handcrafted-persona-engine

import { createPhonemeMap } from "./phoneme-map"
import { NEUTRAL_POSE, lerpPose, type PhonemePose } from "./phoneme-pose"

export class VBridgerLipSyncService {
  private model: any = null
  private phonemeMap: Map<string, PhonemePose>
  private currentPose: PhonemePose = { ...NEUTRAL_POSE }
  private currentTarget: PhonemePose = { ...NEUTRAL_POSE }
  private nextTarget: PhonemePose = { ...NEUTRAL_POSE }
  private interpolationT = 0
  private isPlaying = false
  private phonemes: Array<{ phoneme: string; start: number; end: number }> = []
  private currentPhonemeIndex = -1
  private cumulativeTimeOffset = 0

  constructor() {
    this.phonemeMap = createPhonemeMap()
  }

  setModel(model: any): void {
    this.model = model
  }

  startPhonemes(phonemes: Array<{ phoneme: string; start: number; end: number }>): void {
    this.phonemes = phonemes
    this.currentPhonemeIndex = -1
    this.isPlaying = true
    this.cumulativeTimeOffset = 0
    this.interpolationT = 0
  }

  updateTime(currentTime: number): void {
    if (!this.model || !this.isPlaying) return
    this.updateTargetPoses(currentTime)
  }

  updateNeutral(deltaTime: number): void {
    if (!this.model) return
    const factor = 15 * deltaTime
    this.currentPose = lerpPose(this.currentPose, NEUTRAL_POSE, Math.min(1, factor))
    this.applyPose()
  }

  private updateTargetPoses(currentTime: number): void {
    if (this.phonemes.length === 0) {
      this.currentTarget = NEUTRAL_POSE
      this.nextTarget = NEUTRAL_POSE
      return
    }

    let foundIndex = -1
    for (let i = 0; i < this.phonemes.length; i++) {
      const ph = this.phonemes[i]
      if (currentTime >= ph.start && currentTime < ph.end + 0.001) {
        foundIndex = i
        break
      }
    }

    if (foundIndex !== -1) {
      if (foundIndex !== this.currentPhonemeIndex) {
        this.currentTarget = this.currentPhonemeIndex >= 0
          ? this.getPose(this.phonemes[this.currentPhonemeIndex].phoneme)
          : { ...this.currentPose }
        this.nextTarget = this.getPose(this.phonemes[foundIndex].phoneme)
        this.currentPhonemeIndex = foundIndex
      }

      const ph = this.phonemes[this.currentPhonemeIndex]
      const duration = ph.end - ph.start
      this.interpolationT = duration > 0.001
        ? Math.max(0, Math.min(1, (currentTime - ph.start) / duration))
        : 1

      const easedT = easeInOutQuad(this.interpolationT)
      const framePose = lerpPose(this.currentTarget, this.nextTarget, easedT)
      this.smoothToTarget(framePose, 0.016)
    } else {
      if (this.currentTarget !== NEUTRAL_POSE || this.nextTarget !== NEUTRAL_POSE) {
        this.currentTarget = { ...this.currentPose }
        this.nextTarget = { ...NEUTRAL_POSE }
        this.interpolationT = 0
      }
    }
  }

  private getPose(phoneme: string): PhonemePose {
    return this.phonemeMap.get(phoneme) ?? { ...NEUTRAL_POSE }
  }

  private smoothToTarget(target: PhonemePose, deltaTime: number): void {
    const factor = 35 * deltaTime
    const clamp = Math.min(1, factor)
    this.currentPose = lerpPose(this.currentPose, target, clamp)
    this.applyPose()
  }

  private applyPose(): void {
    if (!this.model) return
    this.model.setParameter("ParamMouthOpenY", this.currentPose.mouthOpenY)
    this.model.setParameter("ParamJawOpen", this.currentPose.jawOpen)
    this.model.setParameter("ParamMouthForm", this.currentPose.mouthForm)
    this.model.setParameter("ParamMouthShrug", this.currentPose.mouthShrug)
    this.model.setParameter("ParamMouthFunnel", this.currentPose.mouthFunnel)
    this.model.setParameter("ParamMouthPuckerWiden", this.currentPose.mouthPuckerWiden)
    this.model.setParameter("ParamMouthPressLipOpen", this.currentPose.mouthPressLipOpen)
    this.model.setParameter("ParamMouthX", this.currentPose.mouthX)
    this.model.setParameter("ParamCheekPuffC", this.currentPose.cheekPuffC)
  }

  reset(): void {
    this.isPlaying = false
    this.phonemes = []
    this.currentPhonemeIndex = -1
    this.currentTarget = { ...NEUTRAL_POSE }
    this.nextTarget = { ...NEUTRAL_POSE }
    this.interpolationT = 0
  }
}

function easeInOutQuad(t: number): number {
  return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t
}
