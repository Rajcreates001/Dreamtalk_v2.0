"use client"

import { useMemo, useRef } from "react"
import { Canvas, useFrame, useThree } from "@react-three/fiber"
import { Float, MeshDistortMaterial, Sparkles } from "@react-three/drei"
import * as THREE from "three"

export interface AvatarColors {
  primary: string   // identity / mouth / accents
  secondary: string // organic green / eyes
  base: string      // head material
  glow: string      // shell / halo
}

interface RigProps {
  colors: AvatarColors
  speaking: boolean
  autoSpeak: boolean
  interactive: boolean
  reduced: boolean
}

/** The head + eyes + mouth + energy shell, animated every frame. */
function HeadRig({ colors, speaking, autoSpeak, interactive, reduced }: RigProps) {
  const group = useRef<THREE.Group>(null)
  const head = useRef<THREE.Mesh>(null)
  const leftEye = useRef<THREE.Mesh>(null)
  const rightEye = useRef<THREE.Mesh>(null)
  const mouth = useRef<THREE.Mesh>(null)
  const { pointer } = useThree()

  // Blink + talk state kept in refs (no re-render).
  const blink = useRef({ next: 2, closing: 0 })
  const talk = useRef({ open: 0, burstUntil: 0, next: 1 })

  const c = useMemo(() => ({
    primary: new THREE.Color(colors.primary),
    secondary: new THREE.Color(colors.secondary),
    base: new THREE.Color(colors.base),
    glow: new THREE.Color(colors.glow),
  }), [colors])

  useFrame((state, delta) => {
    const t = state.clock.elapsedTime
    const g = group.current
    if (!g) return

    // Idle breathing + bob
    const breathe = reduced ? 1 : 1 + Math.sin(t * 1.1) * 0.012
    g.scale.setScalar(breathe)
    g.position.y = reduced ? 0 : Math.sin(t * 0.6) * 0.04

    // Cursor / idle look-around
    const targetY = interactive ? pointer.x * 0.5 : Math.sin(t * 0.35) * 0.28
    const targetX = interactive ? -pointer.y * 0.35 : Math.sin(t * 0.5) * 0.12
    g.rotation.y += (targetY - g.rotation.y) * Math.min(1, delta * 3)
    g.rotation.x += (targetX - g.rotation.x) * Math.min(1, delta * 3)

    // Blink
    const b = blink.current
    if (!reduced && t > b.next && b.closing <= 0) {
      b.closing = 0.16
      b.next = t + 2.4 + Math.random() * 3.2
    }
    let eyeScaleY = 1
    if (b.closing > 0) {
      b.closing -= delta
      eyeScaleY = Math.max(0.08, Math.abs(Math.sin((b.closing / 0.16) * Math.PI)))
    }
    leftEye.current?.scale.set(1, eyeScaleY, 1)
    rightEye.current?.scale.set(1, eyeScaleY, 1)

    // Talk — driven by `speaking`, or ambient bursts when autoSpeak
    const k = talk.current
    let wantOpen = 0
    const isSpeaking = speaking || (autoSpeak && t < k.burstUntil)
    if (autoSpeak && !speaking && t > k.next) {
      k.burstUntil = t + 1.4 + Math.random() * 2.2
      k.next = k.burstUntil + 1.8 + Math.random() * 3
    }
    if (isSpeaking && !reduced) {
      wantOpen = 0.5 + 0.5 * Math.abs(Math.sin(t * 18) * 0.6 + Math.sin(t * 27) * 0.4)
      wantOpen = Math.min(1, wantOpen)
    }
    k.open += (wantOpen - k.open) * Math.min(1, delta * 22)
    if (mouth.current) {
      mouth.current.scale.set(0.34 + k.open * 0.08, 0.05 + k.open * 0.42, 0.12)
    }
  })

  return (
    <group ref={group}>
      {/* Energy shell */}
      <mesh scale={1.28}>
        <sphereGeometry args={[1, 64, 64]} />
        <MeshDistortMaterial
          color={c.glow}
          transparent
          opacity={0.14}
          distort={reduced ? 0.15 : 0.35}
          speed={1.6}
          roughness={0.1}
          metalness={0.2}
          side={THREE.BackSide}
        />
      </mesh>

      {/* Head */}
      <mesh ref={head} scale={[0.92, 1.06, 0.96]}>
        <sphereGeometry args={[1, 96, 96]} />
        <meshStandardMaterial
          color={c.base}
          roughness={0.35}
          metalness={0.15}
          emissive={c.primary}
          emissiveIntensity={0.06}
        />
      </mesh>

      {/* Rim accent band */}
      <mesh scale={[0.93, 1.07, 0.97]}>
        <sphereGeometry args={[1.001, 64, 64]} />
        <meshBasicMaterial color={c.glow} transparent opacity={0.05} wireframe />
      </mesh>

      {/* Eyes */}
      <mesh ref={leftEye} position={[-0.32, 0.12, 0.9]}>
        <sphereGeometry args={[0.12, 32, 32]} />
        <meshStandardMaterial color={c.secondary} emissive={c.secondary} emissiveIntensity={1.4} toneMapped={false} />
      </mesh>
      <mesh ref={rightEye} position={[0.32, 0.12, 0.9]}>
        <sphereGeometry args={[0.12, 32, 32]} />
        <meshStandardMaterial color={c.secondary} emissive={c.secondary} emissiveIntensity={1.4} toneMapped={false} />
      </mesh>

      {/* Mouth */}
      <mesh ref={mouth} position={[0, -0.42, 0.9]} scale={[0.34, 0.06, 0.12]}>
        <sphereGeometry args={[1, 32, 16]} />
        <meshStandardMaterial color={c.primary} emissive={c.primary} emissiveIntensity={1.1} toneMapped={false} />
      </mesh>

      {/* Orbit rings */}
      <OrbitRing radius={1.7} color={colors.primary} speed={0.25} tilt={1.2} />
      <OrbitRing radius={2.05} color={colors.secondary} speed={-0.18} tilt={-0.6} />

      {!reduced && (
        <Sparkles count={40} scale={4} size={2} speed={0.3} opacity={0.5} color={colors.glow} />
      )}
    </group>
  )
}

function OrbitRing({ radius, color, speed, tilt }: { radius: number; color: string; speed: number; tilt: number }) {
  const ref = useRef<THREE.Group>(null)
  useFrame((_, delta) => { if (ref.current) ref.current.rotation.z += delta * speed })
  return (
    <group ref={ref} rotation={[tilt, 0.3, 0]}>
      <mesh>
        <torusGeometry args={[radius, 0.006, 12, 128]} />
        <meshBasicMaterial color={color} transparent opacity={0.35} toneMapped={false} />
      </mesh>
      <mesh position={[radius, 0, 0]}>
        <sphereGeometry args={[0.05, 16, 16]} />
        <meshBasicMaterial color={color} toneMapped={false} />
      </mesh>
    </group>
  )
}

export interface DigitalHuman3DProps {
  colors?: Partial<AvatarColors>
  speaking?: boolean
  autoSpeak?: boolean
  interactive?: boolean
  className?: string
}

const DEFAULT: AvatarColors = {
  primary: "#CC3A63",
  secondary: "#A2AB73",
  base: "#3a2f33",
  glow: "#CC3A63",
}

/**
 * Self-contained 3D digital human. No external model — procedural, themed,
 * and animated (idle, blink, cursor-track, talk). Lazy-import with ssr:false.
 */
export function DigitalHuman3D({
  colors,
  speaking = false,
  autoSpeak = true,
  interactive = true,
  className = "",
}: DigitalHuman3DProps) {
  const merged = { ...DEFAULT, ...colors }
  const reduced = typeof window !== "undefined"
    && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches

  return (
    <div className={className}>
      <Canvas
        dpr={[1, 2]}
        camera={{ position: [0, 0, 5], fov: 42 }}
        gl={{ antialias: true, alpha: true }}
        style={{ background: "transparent" }}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[3, 4, 5]} intensity={1.1} color={merged.primary} />
        <directionalLight position={[-4, -2, 2]} intensity={0.5} color={merged.secondary} />
        <pointLight position={[0, 0, 3]} intensity={0.8} color={merged.glow} />
        <Float speed={reduced ? 0 : 1.4} rotationIntensity={0.15} floatIntensity={0.4}>
          <HeadRig
            colors={merged}
            speaking={speaking}
            autoSpeak={autoSpeak}
            interactive={interactive}
            reduced={!!reduced}
          />
        </Float>
      </Canvas>
    </div>
  )
}

export default DigitalHuman3D
