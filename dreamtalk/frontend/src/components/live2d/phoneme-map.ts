// Dreamtalk - Live2D Animation
// Based on PersonaEngine VBridgerLipSyncService (MIT License)
// Source: handcrafted-persona-engine

import { type PhonemePose } from "./phoneme-pose"

export function createPhonemeMap(): Map<string, PhonemePose> {
  const map = new Map<string, PhonemePose>()

  const p = (overrides: Partial<PhonemePose> = {}): PhonemePose => ({
    mouthOpenY: 0,
    jawOpen: 0,
    mouthForm: 0,
    mouthShrug: 0,
    mouthFunnel: 0,
    mouthPuckerWiden: 0,
    mouthPressLipOpen: 0,
    mouthX: 0,
    cheekPuffC: 0,
    ...overrides,
  })

  map.set("SIL", p())

  map.set("b", p({ mouthPressLipOpen: -1, cheekPuffC: 0.6 }))
  map.set("p", p({ mouthPressLipOpen: -1, cheekPuffC: 0.8 }))
  map.set("d", p({ mouthOpenY: 0.05, jawOpen: 0.05, mouthPressLipOpen: 0, cheekPuffC: 0.2 }))
  map.set("t", p({ mouthOpenY: 0.05, jawOpen: 0.05, mouthPressLipOpen: 0, cheekPuffC: 0.3 }))
  map.set("ɡ", p({ mouthOpenY: 0.1, jawOpen: 0.15, mouthPressLipOpen: 0.2, cheekPuffC: 0.5 }))
  map.set("k", p({ mouthOpenY: 0.1, jawOpen: 0.15, mouthPressLipOpen: 0.2, cheekPuffC: 0.4 }))

  map.set("f", p({ mouthOpenY: 0.05, mouthPressLipOpen: -0.2, mouthForm: -0.2, mouthPuckerWiden: -0.1 }))
  map.set("v", p({ mouthOpenY: 0.05, mouthPressLipOpen: -0.1, mouthForm: -0.2, mouthPuckerWiden: -0.1 }))
  map.set("s", p({ jawOpen: 0, mouthPressLipOpen: 0.9, mouthForm: 0.3, mouthPuckerWiden: -0.6 }))
  map.set("z", p({ jawOpen: 0, mouthPressLipOpen: 0.8, mouthForm: 0.2, mouthPuckerWiden: -0.5 }))
  map.set("h", p({ mouthOpenY: 0.2, jawOpen: 0.2, mouthPressLipOpen: 0.5 }))
  map.set("ʃ", p({ mouthOpenY: 0.1, mouthFunnel: 0.9, mouthPuckerWiden: 0.6, mouthPressLipOpen: 0.2 }))
  map.set("ʒ", p({ mouthOpenY: 0.1, mouthFunnel: 0.8, mouthPuckerWiden: 0.5, mouthPressLipOpen: 0.2 }))
  map.set("ð", p({ mouthOpenY: 0.05, mouthPressLipOpen: 0.1, mouthPuckerWiden: -0.2 }))
  map.set("θ", p({ mouthOpenY: 0.05, mouthPressLipOpen: 0.2, mouthPuckerWiden: -0.3 }))

  map.set("m", p({ mouthPressLipOpen: -1 }))
  map.set("n", p({ mouthOpenY: 0.05, jawOpen: 0.05, mouthPressLipOpen: 0 }))
  map.set("ŋ", p({ mouthOpenY: 0.15, jawOpen: 0.2, mouthPressLipOpen: 0.4 }))

  map.set("l", p({ mouthOpenY: 0.2, jawOpen: 0.2, mouthPuckerWiden: -0.3, mouthPressLipOpen: 0.6 }))
  map.set("ɹ", p({ mouthOpenY: 0.15, jawOpen: 0.15, mouthFunnel: 0.4, mouthPuckerWiden: 0.2, mouthPressLipOpen: 0.3 }))
  map.set("w", p({ mouthOpenY: 0.1, jawOpen: 0.1, mouthFunnel: 1, mouthPuckerWiden: 0.9, mouthPressLipOpen: -0.3 }))
  map.set("j", p({ mouthOpenY: 0.1, jawOpen: 0.1, mouthForm: 0.6, mouthShrug: 0.3, mouthPuckerWiden: -0.8, mouthPressLipOpen: 0.8 }))

  map.set("ʤ", p({ mouthOpenY: 0.1, mouthFunnel: 0.8, mouthPuckerWiden: 0.5, mouthPressLipOpen: 0.2, cheekPuffC: 0.3 }))
  map.set("ʧ", p({ mouthOpenY: 0.1, mouthFunnel: 0.9, mouthPuckerWiden: 0.6, mouthPressLipOpen: 0.2, cheekPuffC: 0.4 }))

  map.set("ə", p({ mouthOpenY: 0.3, jawOpen: 0.3, mouthPressLipOpen: 0.5 }))
  map.set("i", p({ mouthOpenY: 0.1, jawOpen: 0.1, mouthForm: 0.7, mouthShrug: 0.4, mouthPuckerWiden: -0.9, mouthPressLipOpen: 0.9 }))
  map.set("u", p({ mouthOpenY: 0.15, jawOpen: 0.15, mouthFunnel: 1, mouthPuckerWiden: 1, mouthPressLipOpen: -0.2 }))
  map.set("ɑ", p({ mouthOpenY: 0.9, jawOpen: 1, mouthPressLipOpen: 0.8 }))
  map.set("ɔ", p({ mouthOpenY: 0.6, jawOpen: 0.7, mouthFunnel: 0.5, mouthPuckerWiden: 0.3, mouthPressLipOpen: 0.7 }))
  map.set("ɛ", p({ mouthOpenY: 0.5, jawOpen: 0.5, mouthPuckerWiden: -0.5, mouthPressLipOpen: 0.7 }))
  map.set("ɜ", p({ mouthOpenY: 0.4, jawOpen: 0.4, mouthPressLipOpen: 0.6 }))
  map.set("ɪ", p({ mouthOpenY: 0.2, jawOpen: 0.2, mouthForm: 0.2, mouthPuckerWiden: -0.6, mouthPressLipOpen: 0.8 }))
  map.set("ʊ", p({ mouthOpenY: 0.2, jawOpen: 0.2, mouthFunnel: 0.8, mouthPuckerWiden: 0.7, mouthPressLipOpen: 0.1 }))
  map.set("ʌ", p({ mouthOpenY: 0.6, jawOpen: 0.6, mouthPressLipOpen: 0.7 }))

  map.set("A", p({ mouthOpenY: 0.3, jawOpen: 0.3, mouthForm: 0.4, mouthPuckerWiden: -0.7, mouthPressLipOpen: 0.8 }))
  map.set("I", p({ mouthOpenY: 0.4, jawOpen: 0.4, mouthForm: 0.3, mouthPuckerWiden: -0.6, mouthPressLipOpen: 0.8 }))
  map.set("W", p({ mouthOpenY: 0.3, jawOpen: 0.3, mouthFunnel: 0.9, mouthPuckerWiden: 0.8, mouthPressLipOpen: 0 }))
  map.set("Y", p({ mouthOpenY: 0.3, jawOpen: 0.3, mouthForm: 0.2, mouthPuckerWiden: -0.5, mouthPressLipOpen: 0.8 }))

  map.set("ᵊ", p({ mouthOpenY: 0.1, jawOpen: 0.1, mouthPressLipOpen: 0.2 }))
  map.set("æ", p({ mouthOpenY: 0.7, jawOpen: 0.7, mouthForm: 0.3, mouthPuckerWiden: -0.8, mouthPressLipOpen: 0.9 }))
  map.set("O", p({ mouthOpenY: 0.3, jawOpen: 0.3, mouthFunnel: 0.8, mouthPuckerWiden: 0.6, mouthPressLipOpen: 0.1 }))
  map.set("ᵻ", p({ mouthOpenY: 0.15, jawOpen: 0.15, mouthPuckerWiden: -0.2, mouthPressLipOpen: 0.6 }))
  map.set("ɾ", p({ mouthOpenY: 0.05, jawOpen: 0.05, mouthPressLipOpen: 0.3 }))
  map.set("a", p({ mouthOpenY: 0.7, jawOpen: 0.7, mouthPuckerWiden: -0.4, mouthPressLipOpen: 0.8 }))
  map.set("Q", p({ mouthOpenY: 0.3, jawOpen: 0.3, mouthFunnel: 0.7, mouthPuckerWiden: 0.5, mouthPressLipOpen: 0.1 }))
  map.set("ɒ", p({ mouthOpenY: 0.8, jawOpen: 0.9, mouthFunnel: 0.2, mouthPuckerWiden: 0.1, mouthPressLipOpen: 0.8 }))

  return map
}
