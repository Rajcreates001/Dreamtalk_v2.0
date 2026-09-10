declare module "@live2d/cubism" {
  export class Live2DCubismFramework {
    static Model: typeof CubismModel
    static MotionPriority: {
      PriorityIdle: number
      PriorityNormal: number
      PriorityForce: number
    }
  }

  export class CubismModel {
    load(url: string): Promise<void>
    setParameterValue(paramName: string, value: number): void
    setExpression(expressionId: string): void
    startRandomMotion(motionGroup: string, priority: number): boolean
    update(deltaTime: number): void
    draw(): void
    setPosition(x: number, y: number): void
    setScale(scale: number): void
    setRotation(rotation: number): void
    getExpressions(): string[]
    getMotionGroups(): string[]
    release(): void
  }
}
