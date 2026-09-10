// Dreamtalk - Live2D Animation
// Based on PersonaEngine IdleBlinkingAnimationService (MIT License)
// Source: handcrafted-persona-engine

export class IdleBlinkingService {
  private model: any = null
  private eyeParamsValid = false
  private isBlinking = false
  private blinkPhaseTimer = 0
  private timeUntilNextBlink = 0
  private currentBlinkState: "idle" | "closing" | "closed" | "opening" = "idle"
  private random = new Random()

  constructor() {
    this.setNextBlinkInterval()
  }

  setModel(model: any): void {
    this.model = model
    this.validateEyeParams()
  }

  update(deltaTime: number): void {
    if (!this.model || deltaTime <= 0) return
    if (!this.eyeParamsValid) return
    this.updateBlinking(deltaTime)
  }

  private updateBlinking(deltaTime: number): void {
    if (this.isBlinking) {
      this.blinkPhaseTimer += deltaTime

      switch (this.currentBlinkState) {
        case "closing": {
          const progress = this.blinkPhaseTimer / 0.06
          const eyeValue = Math.max(0, 1 - progress)
          if (this.blinkPhaseTimer >= 0.06) {
            this.currentBlinkState = "closed"
            this.blinkPhaseTimer = 0
            this.setEyeParameters(0)
          } else {
            this.setEyeParameters(eyeValue)
          }
          break
        }
        case "closed": {
          if (this.blinkPhaseTimer >= 0.05) {
            this.currentBlinkState = "opening"
            this.blinkPhaseTimer = 0
          } else {
            this.setEyeParameters(0)
          }
          break
        }
        case "opening": {
          const progress = this.blinkPhaseTimer / 0.1
          const eyeValue = Math.min(1, progress)
          if (this.blinkPhaseTimer >= 0.1) {
            this.isBlinking = false
            this.currentBlinkState = "idle"
            this.setNextBlinkInterval()
            this.setEyeParameters(1)
          } else {
            this.setEyeParameters(eyeValue)
          }
          break
        }
      }
    } else {
      this.timeUntilNextBlink -= deltaTime
      if (this.timeUntilNextBlink <= 0) {
        this.isBlinking = true
        this.currentBlinkState = "closing"
        this.blinkPhaseTimer = 0
      }
    }
  }

  private setEyeParameters(value: number): void {
    if (!this.model || !this.eyeParamsValid) return
    try {
      this.model.setParameter("ParamEyeLOpen", value)
      this.model.setParameter("ParamEyeROpen", value)
    } catch {
      this.eyeParamsValid = false
    }
  }

  private validateEyeParams(): void {
    this.eyeParamsValid = true
  }

  private setNextBlinkInterval(): void {
    this.timeUntilNextBlink = 1.5 + this.random.next() * 4.5
  }

  reset(): void {
    this.isBlinking = false
    this.currentBlinkState = "idle"
    this.blinkPhaseTimer = 0
    this.setEyeParameters(1)
    this.setNextBlinkInterval()
  }
}

class Random {
  private seed = Date.now()
  next(): number {
    this.seed = (this.seed * 16807 + 0) % 2147483647
    return this.seed / 2147483647
  }
}
