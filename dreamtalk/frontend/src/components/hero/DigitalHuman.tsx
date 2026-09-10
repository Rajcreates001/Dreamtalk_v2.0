"use client"

import { useRef, useMemo } from "react"
import { useFrame } from "@react-three/fiber"
import * as THREE from "three"

// ─── Eye Component ───
function Eye({ position, blinkPhase }: { position: [number, number, number]; blinkPhase: number }) {
  const lidRef = useRef<THREE.Mesh>(null)
  const pupilRef = useRef<THREE.Mesh>(null)
  const blinkTimer = useRef(0)
  const isBlinking = useRef(false)

  useFrame(({ clock, mouse }) => {
    // Blink randomly
    blinkTimer.current += 0.016
    if (!isBlinking.current && blinkTimer.current > 2 + blinkPhase + Math.random() * 3) {
      isBlinking.current = true
      blinkTimer.current = 0
    }
    if (isBlinking.current && blinkTimer.current > 0.1) {
      isBlinking.current = false
    }

    if (lidRef.current) {
      const blink = isBlinking.current
        ? Math.abs(Math.sin(blinkTimer.current * Math.PI / 0.1))
        : 1
      lidRef.current.scale.y = blink
    }

    // Pupil follows mouse subtly
    if (pupilRef.current) {
      const targetX = (mouse.x * 0.08) * 0.5
      const targetY = (mouse.y * 0.08) * 0.3
      pupilRef.current.position.x += (targetX - pupilRef.current.position.x) * 0.05
      pupilRef.current.position.y += (targetY - pupilRef.current.position.y) * 0.05
    }
  })

  return (
    <group position={position}>
      {/* Eye white */}
      <mesh>
        <sphereGeometry args={[0.08, 16, 16]} />
        <meshBasicMaterial color="#2C2829" />
      </mesh>
      {/* Iris */}
      <mesh position={[0, 0, 0.04]}>
        <sphereGeometry args={[0.045, 12, 12]} />
        <meshBasicMaterial color="#CC3A63" />
      </mesh>
      {/* Pupil */}
      <mesh ref={pupilRef} position={[0, 0, 0.06]}>
        <sphereGeometry args={[0.02, 8, 8]} />
        <meshBasicMaterial color="#000" />
      </mesh>
      {/* Eyelid */}
      <mesh ref={lidRef} position={[0, 0, 0.07]}>
        <sphereGeometry args={[0.09, 16, 16, 0, Math.PI * 2, 0, Math.PI * 0.4]} />
        <meshBasicMaterial color="#2a1a3e" />
      </mesh>
      {/* Upper lid */}
      <mesh position={[0, 0.04, 0.06]}>
        <sphereGeometry args={[0.09, 16, 16, 0, Math.PI * 2, 0, Math.PI * 0.3]} />
        <meshBasicMaterial color="#2a1a3e" />
      </mesh>
    </group>
  )
}

// ─── Mouth ───
function Mouth() {
  const ref = useRef<THREE.Mesh>(null)
  const time = useRef(0)

  useFrame((_, delta) => {
    time.current += delta
    if (ref.current) {
      // Subtle micro-movements
      const open = Math.abs(Math.sin(time.current * 1.5)) * 0.02 + 0.01
      ref.current.scale.y = open * 5 + 0.3
    }
  })

  return (
    <mesh ref={ref} position={[0, 0.7, 0.32]}>
      <sphereGeometry args={[0.04, 0.02, 0.02]} />
      <meshBasicMaterial color="#1a0a2e" />
    </mesh>
  )
}

// ─── Digital Human ───
export function DigitalHuman() {
  const groupRef = useRef<THREE.Group>(null)
  const headRef = useRef<THREE.Group>(null)
  const bodyRef = useRef<THREE.Mesh>(null)
  const breatheRef = useRef(0)
  const glowRef = useRef<THREE.Mesh>(null)

  useFrame(({ clock, mouse }) => {
    if (!groupRef.current || !headRef.current || !bodyRef.current) return

    breatheRef.current += 0.012
    const breathe = Math.sin(breatheRef.current) * 0.04
    const slowWave = Math.sin(clock.elapsedTime * 0.08) * 0.02

    // Full body breathing
    groupRef.current.position.y = breathe + slowWave
    if (bodyRef.current) {
      bodyRef.current.scale.y = 1 + Math.sin(breatheRef.current) * 0.008
    }

    // Head micro-movements
    const headTilt = Math.sin(clock.elapsedTime * 0.12) * 0.04
    const headTurn = Math.sin(clock.elapsedTime * 0.08) * 0.06
    const headBob = Math.sin(clock.elapsedTime * 0.15) * 0.02

    headRef.current.rotation.x = headTilt
    headRef.current.rotation.y = headTurn + (mouse.x * 0.1)
    headRef.current.rotation.z = headBob
    headRef.current.position.y = headBob * 0.5

    // Glow pulse
    if (glowRef.current) {
      const intensity = 0.3 + Math.sin(clock.elapsedTime * 0.5) * 0.1
      ;(glowRef.current.material as THREE.MeshBasicMaterial).opacity = intensity * 0.15
    }
  })

  return (
    <group ref={groupRef} position={[0, -0.3, 0]}>
      {/* Body / Torso */}
      <group>
        {/* Main torso */}
        <mesh ref={bodyRef} position={[0, 0.2, 0]}>
          <capsuleGeometry args={[0.18, 0.4, 8, 16]} />
          <meshBasicMaterial color="#CC3A63" transparent opacity={0.12} />
        </mesh>

        {/* Chest glow */}
        <mesh position={[0, 0.35, 0.15]}>
          <circleGeometry args={[0.08, 16]} />
          <meshBasicMaterial color="#A2AB73" transparent opacity={0.15} depthWrite={false} blending={THREE.AdditiveBlending} />
        </mesh>

        {/* Shoulders */}
        <mesh position={[-0.22, 0.4, 0]} rotation={[0, 0, 0.3]}>
          <capsuleGeometry args={[0.04, 0.15, 6, 8]} />
          <meshBasicMaterial color="#CC3A63" transparent opacity={0.08} />
        </mesh>
        <mesh position={[0.22, 0.4, 0]} rotation={[0, 0, -0.3]}>
          <capsuleGeometry args={[0.04, 0.15, 6, 8]} />
          <meshBasicMaterial color="#CC3A63" transparent opacity={0.08} />
        </mesh>

        {/* Neck */}
        <mesh position={[0, 0.55, 0]}>
          <capsuleGeometry args={[0.05, 0.06, 6, 8]} />
          <meshBasicMaterial color="#CC3A63" transparent opacity={0.1} />
        </mesh>
      </group>

      {/* Head */}
      <group ref={headRef} position={[0, 0.65, 0]}>
        {/* Head mesh */}
        <mesh>
          <sphereGeometry args={[0.2, 24, 24]} />
          <meshBasicMaterial color="#CC3A63" transparent opacity={0.15} />
        </mesh>

        {/* Wireframe overlay */}
        <mesh>
          <sphereGeometry args={[0.19, 16, 16]} />
          <meshBasicMaterial color="#CC3A63" transparent opacity={0.06} wireframe />
        </mesh>

        {/* Glow ring behind head */}
        <mesh ref={glowRef} position={[0, 0, -0.15]}>
          <circleGeometry args={[0.3, 24]} />
          <meshBasicMaterial color="#CC3A63" transparent opacity={0.08} depthWrite={false} blending={THREE.AdditiveBlending} />
        </mesh>

        {/* Eyes */}
        <Eye position={[-0.07, 0.05, 0.18]} blinkPhase={0} />
        <Eye position={[0.07, 0.05, 0.18]} blinkPhase={0.5} />

        {/* Eyebrows */}
        <mesh position={[-0.07, 0.09, 0.18]}>
          <boxGeometry args={[0.04, 0.005, 0.005]} />
          <meshBasicMaterial color="#CC3A63" transparent opacity={0.2} />
        </mesh>
        <mesh position={[0.07, 0.09, 0.18]}>
          <boxGeometry args={[0.04, 0.005, 0.005]} />
          <meshBasicMaterial color="#CC3A63" transparent opacity={0.2} />
        </mesh>

        {/* Nose */}
        <mesh position={[0, 0.02, 0.2]}>
          <coneGeometry args={[0.01, 0.02, 6]} />
          <meshBasicMaterial color="#CC3A63" transparent opacity={0.1} />
        </mesh>

        {/* Mouth */}
        <Mouth />

        {/* Inner glow */}
        <mesh position={[0, 0, 0]}>
          <sphereGeometry args={[0.1, 16, 16]} />
          <meshBasicMaterial color="#A2AB73" transparent opacity={0.04} depthWrite={false} blending={THREE.AdditiveBlending} />
        </mesh>
      </group>

      {/* Point light emanating from the being */}
      <pointLight position={[0, 0.5, 0.5]} color="#CC3A63" intensity={0.15} distance={3} decay={2} />
    </group>
  )
}
