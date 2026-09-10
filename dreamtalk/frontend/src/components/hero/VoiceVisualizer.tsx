"use client"

import { useRef, useMemo } from "react"
import { useFrame } from "@react-three/fiber"
import * as THREE from "three"

interface VoiceVisualizerProps {
  active?: boolean
  color?: string
  bars?: number
}

export function VoiceVisualizer({ active = false, color = "#00E5FF", bars = 12 }: VoiceVisualizerProps) {
  const groupRef = useRef<THREE.Group>(null)
  const barRefs = useRef<(THREE.Mesh | null)[]>([])
  const outerRingRef = useRef<THREE.Mesh>(null)
  const innerRingRef = useRef<THREE.Mesh>(null)

  const [barData, phases] = useMemo(() => {
    const data: { angle: number; idx: number }[] = []
    const ph: number[] = []
    for (let i = 0; i < bars; i++) {
      data.push({ angle: (i / bars) * Math.PI * 2, idx: i })
      ph.push(Math.random() * Math.PI * 2)
    }
    return [data, ph]
  }, [bars])

  useFrame(({ clock }) => {
    const t = clock.elapsedTime

    if (groupRef.current) {
      groupRef.current.rotation.y = t * 0.03
    }

    for (let i = 0; i < bars; i++) {
      const mesh = barRefs.current[i]
      if (!mesh) continue
      const phase = phases[i]
      const height = active
        ? 0.15 + Math.abs(Math.sin(t * 1.5 + phase)) * 0.3
        : 0.04 + Math.sin(t * 0.5 + phase) * 0.02
      mesh.scale.y = Math.max(height * 2, 0.02)
    }

    if (outerRingRef.current) {
      const pulse = active ? 1 + Math.sin(t * 2.5) * 0.02 : 1
      outerRingRef.current.scale.set(pulse, pulse, pulse)
    }

    if (innerRingRef.current) {
      const pulse = active ? 1 + Math.sin(t * 3 + 1) * 0.02 : 1
      innerRingRef.current.scale.set(pulse, pulse, pulse)
    }
  })

  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      {/* Outer frequency ring */}
      <mesh ref={outerRingRef}>
        <torusGeometry args={[2.4, 0.005, 12, 80]} />
        <meshBasicMaterial color={color} transparent opacity={0.08} />
      </mesh>

      {/* Inner frequency ring */}
      <mesh ref={innerRingRef}>
        <torusGeometry args={[1.0, 0.008, 12, 60]} />
        <meshBasicMaterial color={color} transparent opacity={0.12} />
      </mesh>

      {/* Bar visualizers */}
      {barData.map(({ angle }, index) => (
        <mesh
          key={angle}
          ref={(el) => { barRefs.current[index] = el }}
          position={[
            Math.cos(angle) * 1.7,
            0,
            Math.sin(angle) * 1.7,
          ]}
          rotation={[0, -angle, 0]}
        >
          <boxGeometry args={[0.015, 0.05, 0.015]} />
          <meshBasicMaterial color={color} transparent opacity={0.2} />
        </mesh>
      ))}
    </group>
  )
}
