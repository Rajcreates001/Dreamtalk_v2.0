"use client"

import { useRef, useMemo } from "react"
import { useFrame } from "@react-three/fiber"
import * as THREE from "three"

interface FloatingShape {
  position: [number, number, number]
  rotation: [number, number, number]
  scale: number
  speed: number
  type: "box" | "sphere" | "torus" | "icosahedron"
  color: string
}

const COLORS = ["#10b981", "#3b82f6", "#8b5cf6", "#ec4899", "#f59e0b", "#06b6d4"]

function ShapeGeometry({ type }: { type: FloatingShape["type"] }) {
  switch (type) {
    case "box":
      return <boxGeometry args={[1, 1, 1]} />
    case "sphere":
      return <sphereGeometry args={[0.6, 24, 24]} />
    case "torus":
      return <torusGeometry args={[0.5, 0.2, 16, 32]} />
    case "icosahedron":
      return <icosahedronGeometry args={[0.6, 0]} />
  }
}

function Shape({ shape, index }: { shape: FloatingShape; index: number }) {
  const ref = useRef<THREE.Mesh>(null)
  const startOffset = useMemo(() => Math.random() * Math.PI * 2, [])

  useFrame(({ clock }) => {
    if (ref.current) {
      const t = clock.getElapsedTime() * shape.speed + startOffset
      ref.current.position.y = shape.position[1] + Math.sin(t) * 0.3
      ref.current.rotation.x += 0.005 * shape.speed
      ref.current.rotation.y += 0.01 * shape.speed
      ref.current.rotation.z += 0.003 * shape.speed
      const breath = 1 + Math.sin(t * 0.5) * 0.05
      ref.current.scale.setScalar(shape.scale * breath)
    }
  })

  return (
    <mesh
      ref={ref}
      position={shape.position}
      rotation={shape.rotation}
    >
      <ShapeGeometry type={shape.type} />
      <meshPhysicalMaterial
        color={shape.color}
        transparent
        opacity={0.25}
        wireframe={index % 3 === 0}
        metalness={0.2}
        roughness={0.8}
        envMapIntensity={0.5}
        side={THREE.DoubleSide}
      />
    </mesh>
  )
}

interface FloatingShapesProps {
  count?: number
}

export function FloatingShapes({ count = 12 }: FloatingShapesProps) {
  const shapes = useMemo(() => {
    const types: FloatingShape["type"][] = ["box", "sphere", "torus", "icosahedron"]
    return Array.from({ length: count }, (_, i) => ({
      position: [
        (Math.random() - 0.5) * 12,
        (Math.random() - 0.5) * 8,
        (Math.random() - 0.5) * 6 - 2,
      ] as [number, number, number],
      rotation: [
        Math.random() * Math.PI * 2,
        Math.random() * Math.PI * 2,
        Math.random() * Math.PI * 2,
      ] as [number, number, number],
      scale: 0.2 + Math.random() * 0.4,
      speed: 0.2 + Math.random() * 0.4,
      type: types[i % types.length],
      color: COLORS[i % COLORS.length],
    }))
  }, [count])

  return (
    <group>
      {shapes.map((s, i) => (
        <Shape key={i} shape={s} index={i} />
      ))}
    </group>
  )
}
