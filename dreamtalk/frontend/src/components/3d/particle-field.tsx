"use client"

import { useRef, useMemo } from "react"
import { useFrame } from "@react-three/fiber"
import * as THREE from "three"

interface ParticleFieldProps {
  count?: number
  color?: string
  speed?: number
  size?: number
  spread?: number
  opacity?: number
}

export function ParticleField({
  count = 2000,
  color = "#10b981",
  speed = 0.3,
  size = 0.02,
  spread = 15,
  opacity = 0.6,
}: ParticleFieldProps) {
  const ref = useRef<THREE.Points>(null)

  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3)
    for (let i = 0; i < count * 3; i++) {
      pos[i] = (Math.random() - 0.5) * spread
    }
    return pos
  }, [count, spread])

  useFrame((_, delta) => {
    if (ref.current) {
      ref.current.rotation.y += delta * speed * 0.05
      ref.current.rotation.x += delta * speed * 0.02
    }
  })

  const c = new THREE.Color(color)

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute
          args={[positions, 3]}
          attach="attributes-position"
          count={count}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={size}
        color={c}
        transparent
        opacity={opacity}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  )
}
