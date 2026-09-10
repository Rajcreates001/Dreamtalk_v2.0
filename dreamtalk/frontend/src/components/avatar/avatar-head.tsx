"use client"

import { useRef, useMemo, useState } from "react"
import { Canvas, useFrame } from "@react-three/fiber"
import { OrbitControls } from "@react-three/drei"
import * as THREE from "three"

// ── Types ──────────────────────────────────────────────────────────────────

interface ExpressionData {
  eyebrows?: {
    brow_inner_up?: number
    brow_outer_up?: number
    brow_lower?: number
  }
  eyes?: {
    eye_open_left?: number
    eye_open_right?: number
    eye_squint_left?: number
    eye_squint_right?: number
    eye_wide_left?: number
    eye_wide_right?: number
  }
  mouth?: {
    mouth_smile?: number
    mouth_frown?: number
    mouth_open?: number
    jaw_open?: number
    lip_pucker?: number
    lip_funnel?: number
  }
  head?: {
    head_yaw?: number
    head_pitch?: number
    head_tilt?: number
  }
}

// ── Emotion → Expression Mapping ───────────────────────────────────────────
// When the backend sends an emotion but no blendshape data, derive blendshapes
// from the emotion so the avatar always reacts.

interface DerivedExpression {
  smile: number
  frown: number
  mouthOpen: number
  eyeOpen: number
  eyeSquint: number
  browUp: number
  browDown: number
  headYaw: number
  headPitch: number
  headTilt: number
}

const EMOTION_EXPRESSIONS: Record<string, DerivedExpression> = {
  happy:    { smile: 0.85, frown: 0, mouthOpen: 0.1, eyeOpen: 1.0, eyeSquint: 0.3, browUp: 0.6, browDown: 0, headYaw: 0, headPitch: 0.05, headTilt: 0.05 },
  sad:      { smile: 0,    frown: 0.7, mouthOpen: 0, eyeOpen: 0.7, eyeSquint: 0.1, browUp: 0.2, browDown: 0.5, headYaw: 0, headPitch: -0.15, headTilt: 0 },
  angry:    { smile: 0,    frown: 0.5, mouthOpen: 0.15, eyeOpen: 0.9, eyeSquint: 0.4, browUp: 0, browDown: 0.8, headYaw: 0, headPitch: -0.05, headTilt: 0 },
  fear:     { smile: 0,    frown: 0.2, mouthOpen: 0.3, eyeOpen: 1.2, eyeSquint: 0, browUp: 0.8, browDown: 0, headYaw: 0.05, headPitch: 0.05, headTilt: 0 },
  surprise: { smile: 0.1,  frown: 0, mouthOpen: 0.6, eyeOpen: 1.3, eyeSquint: 0, browUp: 0.9, browDown: 0, headYaw: 0, headPitch: 0.1, headTilt: 0 },
  neutral:  { smile: 0.05, frown: 0, mouthOpen: 0, eyeOpen: 1.0, eyeSquint: 0, browUp: 0.1, browDown: 0, headYaw: 0, headPitch: 0, headTilt: 0 },
  disgust:  { smile: 0,    frown: 0.3, mouthOpen: 0.1, eyeOpen: 0.8, eyeSquint: 0.5, browUp: 0.1, browDown: 0.6, headYaw: -0.1, headPitch: 0, headTilt: 0.1 },
  contempt: { smile: 0.3,  frown: 0.1, mouthOpen: 0, eyeOpen: 0.9, eyeSquint: 0.2, browUp: 0, browDown: 0.3, headYaw: 0.08, headPitch: 0.05, headTilt: -0.05 },
}

const EMOTION_COLORS: Record<string, string> = {
  happy: "#D6A44C",
  sad: "#4169E1",
  angry: "#FF4444",
  fear: "#9932CC",
  surprise: "#FF8C00",
  neutral: "#A2AB73",
  disgust: "#556B2F",
  contempt: "#8B4513",
}

// Merge raw expression data with emotion-derived defaults
function resolveExpression(raw: ExpressionData, emotion: string): DerivedExpression {
  const defaults = EMOTION_EXPRESSIONS[emotion] || EMOTION_EXPRESSIONS.neutral

  return {
    smile: raw.mouth?.mouth_smile ?? defaults.smile,
    frown: raw.mouth?.mouth_frown ?? defaults.frown,
    mouthOpen: (raw.mouth?.mouth_open ?? 0) + (raw.mouth?.jaw_open ?? 0) * 0.5 || defaults.mouthOpen,
    eyeOpen: 1 - (raw.eyes?.eye_squint_left ?? 0) * 0.5 + (raw.eyes?.eye_wide_left ?? 0) * 0.3 || defaults.eyeOpen,
    eyeSquint: (raw.eyes?.eye_squint_left ?? 0) + (raw.eyes?.eye_squint_right ?? 0) || defaults.eyeSquint,
    browUp: (raw.eyebrows?.brow_inner_up ?? 0) + (raw.eyebrows?.brow_outer_up ?? 0) || defaults.browUp,
    browDown: (raw.eyebrows?.brow_lower ?? 0) || defaults.browDown,
    headYaw: (raw.head?.head_yaw ?? 0) * 0.5 || defaults.headYaw,
    headPitch: (raw.head?.head_pitch ?? 0) * 0.3 || defaults.headPitch,
    headTilt: (raw.head?.head_tilt ?? 0) * 0.3 || defaults.headTilt,
  }
}

// ── Easing ─────────────────────────────────────────────────────────────────

// Exponential ease-in-out for buttery transitions
function smoothDamp(current: number, target: number, speed: number, delta: number): number {
  // Per-parameter adaptive speed: mouth moves fast, head moves slow
  const t = 1 - Math.exp(-speed * delta)
  return current + (target - current) * t
}

// ── Head Component ─────────────────────────────────────────────────────────

function Head({ expression, emotion }: { expression: ExpressionData; emotion: string }) {
  const headRef = useRef<THREE.Group>(null)
  const leftEyeWhiteRef = useRef<THREE.Mesh>(null)
  const rightEyeWhiteRef = useRef<THREE.Mesh>(null)
  const leftPupilRef = useRef<THREE.Group>(null)
  const rightPupilRef = useRef<THREE.Group>(null)
  const leftBrowRef = useRef<THREE.Mesh>(null)
  const rightBrowRef = useRef<THREE.Mesh>(null)
  const mouthRef = useRef<THREE.Group>(null)
  const upperLipRef = useRef<THREE.Mesh>(null)
  const lowerLipRef = useRef<THREE.Mesh>(null)
  const emotionRingRef = useRef<THREE.Mesh>(null)

  const targetColor = useRef(new THREE.Color(EMOTION_COLORS.neutral))

  // Smooth state
  const s = useRef({
    smile: 0, frown: 0, mouthOpen: 0, eyeOpenL: 1, eyeOpenR: 1,
    eyeSquint: 0, browUp: 0, browDown: 0,
    headYaw: 0, headPitch: 0, headTilt: 0,
    // Idle animation offsets
    idlePhase: 0,
    // Blink
    blinkTimer: 0,
    blinkPhase: 0, // 0 = open, >0 = blinking
    nextBlink: 3,  // seconds until next blink
  })

  // Pre-compute derived expression from emotion
  const target = useMemo(() => resolveExpression(expression, emotion), [expression, emotion])

  // Update emotion ring target color
  useMemo(() => {
    targetColor.current.set(EMOTION_COLORS[emotion] || EMOTION_COLORS.neutral)
  }, [emotion])

  useFrame((_, delta) => {
    const v = s.current
    const d = Math.min(delta, 0.1) // clamp delta for tab-away

    // ── Auto-blink ─────────────────────────────────────────────────────
    v.blinkTimer += d
    if (v.blinkTimer >= v.nextBlink && v.blinkPhase === 0) {
      v.blinkPhase = 0.15 // blink takes ~0.15s
      v.blinkTimer = 0
      v.nextBlink = 2 + Math.random() * 4 // next blink in 2-6s
    }
    let blinkScale = 1
    if (v.blinkPhase > 0) {
      v.blinkPhase -= d
      if (v.blinkPhase <= 0) {
        v.blinkPhase = 0
        blinkScale = 1
      } else {
        // Triangle wave: open → closed → open
        const progress = 1 - (v.blinkPhase / 0.15)
        blinkScale = progress < 0.5 ? 1 - progress * 2 : (progress - 0.5) * 2
      }
    }

    // ── Idle animation ─────────────────────────────────────────────────
    v.idlePhase += d * 0.8
    const idleYaw = Math.sin(v.idlePhase * 0.7) * 0.03
    const idlePitch = Math.sin(v.idlePhase * 0.5) * 0.02
    const idleTilt = Math.sin(v.idlePhase * 0.3) * 0.01
    // Subtle breathing: scale head slightly
    const breathe = 1 + Math.sin(v.idlePhase * 1.2) * 0.008

    // ── Smooth target tracking ─────────────────────────────────────────
    const headSpeed = 2.5  // slower = smoother head
    const faceSpeed = 6    // faster = snappier face
    const eyeSpeed = 8     // fastest = responsive eyes

    v.smile = smoothDamp(v.smile, target.smile, faceSpeed, d)
    v.frown = smoothDamp(v.frown, target.frown, faceSpeed, d)
    v.mouthOpen = smoothDamp(v.mouthOpen, target.mouthOpen, faceSpeed, d)
    v.eyeOpenL = smoothDamp(v.eyeOpenL, target.eyeOpen, eyeSpeed, d)
    v.eyeOpenR = smoothDamp(v.eyeOpenR, target.eyeOpen, eyeSpeed, d)
    v.eyeSquint = smoothDamp(v.eyeSquint, target.eyeSquint, faceSpeed, d)
    v.browUp = smoothDamp(v.browUp, target.browUp, faceSpeed, d)
    v.browDown = smoothDamp(v.browDown, target.browDown, faceSpeed, d)
    v.headYaw = smoothDamp(v.headYaw, target.headYaw + idleYaw, headSpeed, d)
    v.headPitch = smoothDamp(v.headPitch, target.headPitch + idlePitch, headSpeed, d)
    v.headTilt = smoothDamp(v.headTilt, target.headTilt + idleTilt, headSpeed, d)

    // ── Apply head rotation + breathing ────────────────────────────────
    if (headRef.current) {
      headRef.current.rotation.y = v.headYaw
      headRef.current.rotation.x = v.headPitch
      headRef.current.rotation.z = v.headTilt
      headRef.current.scale.setScalar(breathe)
    }

    // ── Apply eyes ─────────────────────────────────────────────────────
    // Combined open/squint gives: wide eyes (surprise), squinted (angry/disgust), normal, or blink
    const eyeScale = Math.max(0.05, (v.eyeOpenL - v.eyeSquint * 0.3)) * blinkScale
    if (leftEyeWhiteRef.current) leftEyeWhiteRef.current.scale.y = Math.max(0.05, eyeScale)
    if (rightEyeWhiteRef.current) rightEyeWhiteRef.current.scale.y = Math.max(0.05, eyeScale)

    // Pupils follow the head movement slightly for realism
    const pupilOffsetX = v.headYaw * 0.02
    const pupilOffsetY = -v.headPitch * 0.01
    if (leftPupilRef.current) {
      leftPupilRef.current.position.x = pupilOffsetX
      leftPupilRef.current.position.y = pupilOffsetY
    }
    if (rightPupilRef.current) {
      rightPupilRef.current.position.x = pupilOffsetX
      rightPupilRef.current.position.y = pupilOffsetY
    }

    // ── Apply eyebrows ─────────────────────────────────────────────────
    const browYBase = 0.52
    if (leftBrowRef.current) {
      leftBrowRef.current.position.y = browYBase + v.browUp * 0.08 - v.browDown * 0.05
      leftBrowRef.current.rotation.z = 0.15 - v.browDown * 0.2 + v.browUp * 0.05
    }
    if (rightBrowRef.current) {
      rightBrowRef.current.position.y = browYBase + v.browUp * 0.08 - v.browDown * 0.05
      rightBrowRef.current.rotation.z = -0.15 + v.browDown * 0.2 - v.browUp * 0.05
    }

    // ── Apply mouth ────────────────────────────────────────────────────
    if (upperLipRef.current && lowerLipRef.current) {
      // Smile widens the mouth, frown narrows it
      const mouthWidth = 1 + v.smile * 0.35 - v.frown * 0.15
      const mouthOpenAmount = v.mouthOpen * 0.06
      const smileCurve = v.smile * 0.015 - v.frown * 0.01

      upperLipRef.current.scale.x = mouthWidth
      upperLipRef.current.position.y = 0.01 + smileCurve

      lowerLipRef.current.scale.x = mouthWidth
      lowerLipRef.current.position.y = -0.01 - mouthOpenAmount - smileCurve * 0.5
    }

    // ── Emotion ring pulse + color lerp ────────────────────────────────
    if (emotionRingRef.current) {
      const ringMat = emotionRingRef.current.material as THREE.MeshBasicMaterial
      ringMat.color.lerp(targetColor.current, d * 3)
      // Gentle pulse when there's a strong emotion
      const intensity = Math.abs(v.smile) + Math.abs(v.frown) + Math.abs(v.mouthOpen)
      const pulse = 0.15 + Math.sin(v.idlePhase * 3) * 0.05 * Math.min(intensity, 1)
      ringMat.opacity = pulse
      // Scale ring slightly with emotion intensity
      const ringScale = 1 + Math.sin(v.idlePhase * 2) * 0.01 * Math.min(intensity, 1)
      emotionRingRef.current.scale.setScalar(ringScale)
    }
  })

  const skinColor = "#F5D0A9"
  const lipColor = "#CC7777"

  return (
    <group ref={headRef}>
      {/* ── Head ─────────────────────────────────────────────────────── */}
      <mesh>
        <sphereGeometry args={[0.55, 48, 48]} />
        <meshStandardMaterial color={skinColor} roughness={0.7} metalness={0.05} />
      </mesh>

      {/* ── Left Eye ─────────────────────────────────────────────────── */}
      <group position={[-0.18, 0.12, 0.48]}>
        {/* White */}
        <mesh ref={leftEyeWhiteRef}>
          <sphereGeometry args={[0.075, 24, 24]} />
          <meshStandardMaterial color="#F3F4F4" roughness={0.3} />
        </mesh>
        {/* Iris + Pupil group (moves with gaze) */}
        <group ref={leftPupilRef} position={[0, 0, 0.04]}>
          <mesh>
            <sphereGeometry args={[0.038, 16, 16]} />
            <meshStandardMaterial color="#5A4A3A" roughness={0.5} />
          </mesh>
          <mesh position={[0, 0, 0.015]}>
            <sphereGeometry args={[0.02, 12, 12]} />
            <meshStandardMaterial color="#201D1D" roughness={0.2} />
          </mesh>
          {/* Eye highlight */}
          <mesh position={[0.01, 0.01, 0.025]}>
            <sphereGeometry args={[0.006, 8, 8]} />
            <meshStandardMaterial color="white" emissive="white" emissiveIntensity={0.3} />
          </mesh>
        </group>
      </group>

      {/* ── Right Eye ────────────────────────────────────────────────── */}
      <group position={[0.18, 0.12, 0.48]}>
        <mesh ref={rightEyeWhiteRef}>
          <sphereGeometry args={[0.075, 24, 24]} />
          <meshStandardMaterial color="#F3F4F4" roughness={0.3} />
        </mesh>
        <group ref={rightPupilRef} position={[0, 0, 0.04]}>
          <mesh>
            <sphereGeometry args={[0.038, 16, 16]} />
            <meshStandardMaterial color="#5A4A3A" roughness={0.5} />
          </mesh>
          <mesh position={[0, 0, 0.015]}>
            <sphereGeometry args={[0.02, 12, 12]} />
            <meshStandardMaterial color="#201D1D" roughness={0.2} />
          </mesh>
          <mesh position={[0.01, 0.01, 0.025]}>
            <sphereGeometry args={[0.006, 8, 8]} />
            <meshStandardMaterial color="white" emissive="white" emissiveIntensity={0.3} />
          </mesh>
        </group>
      </group>

      {/* ── Left Eyebrow ─────────────────────────────────────────────── */}
      <mesh ref={leftBrowRef} position={[-0.18, 0.52, 0.44]} rotation={[0, 0, 0.15]}>
        <boxGeometry args={[0.14, 0.025, 0.02]} />
        <meshStandardMaterial color="#3A3535" roughness={0.8} />
      </mesh>

      {/* ── Right Eyebrow ────────────────────────────────────────────── */}
      <mesh ref={rightBrowRef} position={[0.18, 0.52, 0.44]} rotation={[0, 0, -0.15]}>
        <boxGeometry args={[0.14, 0.025, 0.02]} />
        <meshStandardMaterial color="#3A3535" roughness={0.8} />
      </mesh>

      {/* ── Nose ─────────────────────────────────────────────────────── */}
      <mesh position={[0, 0.02, 0.55]}>
        <sphereGeometry args={[0.035, 12, 12]} />
        <meshStandardMaterial color="#E6D9C4" roughness={0.6} />
      </mesh>

      {/* ── Mouth ────────────────────────────────────────────────────── */}
      <group position={[0, -0.14, 0.48]}>
        {/* Upper lip */}
        <mesh ref={upperLipRef} position={[0, 0.01, 0]}>
          <boxGeometry args={[0.12, 0.018, 0.015]} />
          <meshStandardMaterial color={lipColor} roughness={0.5} />
        </mesh>
        {/* Lower lip */}
        <mesh ref={lowerLipRef} position={[0, -0.01, 0]}>
          <boxGeometry args={[0.12, 0.02, 0.015]} />
          <meshStandardMaterial color={lipColor} roughness={0.5} />
        </mesh>
      </group>

      {/* ── Ears ─────────────────────────────────────────────────────── */}
      <mesh position={[-0.53, 0.05, 0.05]}>
        <sphereGeometry args={[0.06, 12, 12]} />
        <meshStandardMaterial color="#E6D9C4" roughness={0.7} />
      </mesh>
      <mesh position={[0.53, 0.05, 0.05]}>
        <sphereGeometry args={[0.06, 12, 12]} />
        <meshStandardMaterial color="#E6D9C4" roughness={0.7} />
      </mesh>

      {/* ── Neck ─────────────────────────────────────────────────────── */}
      <mesh position={[0, -0.7, 0]}>
        <cylinderGeometry args={[0.12, 0.15, 0.25, 16]} />
        <meshStandardMaterial color={skinColor} roughness={0.7} />
      </mesh>

      {/* ── Emotion Glow Ring ────────────────────────────────────────── */}
      <mesh ref={emotionRingRef} position={[0, 0, -0.02]}>
        <ringGeometry args={[0.58, 0.62, 48]} />
        <meshBasicMaterial
          color={EMOTION_COLORS.neutral}
          transparent
          opacity={0.15}
          side={THREE.DoubleSide}
        />
      </mesh>
    </group>
  )
}

// ── Main Export ─────────────────────────────────────────────────────────────

export function AvatarHead({
  expression = {},
  emotion = "neutral",
  className = "",
}: {
  expression?: ExpressionData
  emotion?: string
  className?: string
}) {
  return (
    <div className={`w-full h-full ${className}`}>
      <Canvas
        camera={{ position: [0, 0, 1.8], fov: 45 }}
        style={{ background: "transparent" }}
        dpr={[1, 2]}
      >
        {/* Lighting */}
        <ambientLight intensity={0.5} />
        <directionalLight position={[2, 3, 5]} intensity={0.9} color="#FFF5E6" />
        <directionalLight position={[-1, -1, 3]} intensity={0.3} color="#E6F0FF" />
        <pointLight position={[0, 0.5, 1]} intensity={0.3} color="#FFE4C4" />

        {/* Avatar */}
        <Head expression={expression} emotion={emotion} />

        {/* Controls */}
        <OrbitControls
          enableZoom={false}
          enablePan={false}
          minPolarAngle={Math.PI / 4}
          maxPolarAngle={Math.PI / 1.5}
          dampingFactor={0.1}
          enableDamping
        />
      </Canvas>
    </div>
  )
}
