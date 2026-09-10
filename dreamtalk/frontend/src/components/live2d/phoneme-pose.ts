// Dreamtalk - Live2D Animation
// Based on PersonaEngine (MIT License)
// Source: handcrafted-persona-engine

export interface PhonemePose {
  mouthOpenY: number
  jawOpen: number
  mouthForm: number
  mouthShrug: number
  mouthFunnel: number
  mouthPuckerWiden: number
  mouthPressLipOpen: number
  mouthX: number
  cheekPuffC: number
}

export const NEUTRAL_POSE: PhonemePose = {
  mouthOpenY: 0,
  jawOpen: 0,
  mouthForm: 0,
  mouthShrug: 0,
  mouthFunnel: 0,
  mouthPuckerWiden: 0,
  mouthPressLipOpen: 0,
  mouthX: 0,
  cheekPuffC: 0,
}

export function lerpPose(a: PhonemePose, b: PhonemePose, t: number): PhonemePose {
  const clamp = Math.max(0, Math.min(1, t))
  return {
    mouthOpenY: a.mouthOpenY + (b.mouthOpenY - a.mouthOpenY) * clamp,
    jawOpen: a.jawOpen + (b.jawOpen - a.jawOpen) * clamp,
    mouthForm: a.mouthForm + (b.mouthForm - a.mouthForm) * clamp,
    mouthShrug: a.mouthShrug + (b.mouthShrug - a.mouthShrug) * clamp,
    mouthFunnel: a.mouthFunnel + (b.mouthFunnel - a.mouthFunnel) * clamp,
    mouthPuckerWiden: a.mouthPuckerWiden + (b.mouthPuckerWiden - a.mouthPuckerWiden) * clamp,
    mouthPressLipOpen: a.mouthPressLipOpen + (b.mouthPressLipOpen - a.mouthPressLipOpen) * clamp,
    mouthX: a.mouthX + (b.mouthX - a.mouthX) * clamp,
    cheekPuffC: a.cheekPuffC + (b.cheekPuffC - a.cheekPuffC) * clamp,
  }
}

export function isPoseNeutral(pose: PhonemePose, threshold = 0.02): boolean {
  return (
    Math.abs(pose.mouthOpenY) < threshold &&
    Math.abs(pose.jawOpen) < threshold &&
    Math.abs(pose.mouthForm) < threshold &&
    Math.abs(pose.mouthShrug) < threshold &&
    Math.abs(pose.mouthFunnel) < threshold &&
    Math.abs(pose.mouthPuckerWiden) < threshold &&
    Math.abs(pose.mouthPressLipOpen) < threshold &&
    Math.abs(pose.mouthX) < threshold &&
    Math.abs(pose.cheekPuffC) < threshold
  )
}
