"use client"

import { useRef, useMemo, useEffect, useState } from "react"
import { Canvas, useFrame, useThree } from "@react-three/fiber"
import * as THREE from "three"
import { cn } from "@/lib/utils"

const DARK_COLORS = ["#CC3A63", "#C77B54", "#640D5F", "#0D1164", "#FF8F8F", "#B7A3E3"]
const LIGHT_COLORS = ["#FF8F8F", "#B7A3E3", "#C2E2FA", "#FFF1CB", "#CC3A63", "#C77B54"]

interface SpatialSceneProps {
  className?: string
  intensity?: number
  isDark?: boolean
  interactive?: boolean
  reduced?: boolean
}

function Field({ intensity, isDark, mousePos, reduced }: {
  intensity: number; isDark: boolean
  mousePos: React.MutableRefObject<{ x: number; y: number }>
  reduced: boolean
}) {
  const groupRef = useRef<THREE.Group>(null)
  const pointsRef = useRef<THREE.Points>(null)
  const { camera } = useThree()
  const clockRef = useRef(0)
  const colors = isDark ? DARK_COLORS : LIGHT_COLORS
  const objCount = reduced ? 8 : 16

  const objects = useMemo(() => {
    const types = ["box", "sphere", "torus"] as const
    return Array.from({ length: objCount }, (_, i) => ({
      pos: [(Math.random() - 0.5) * 16, (Math.random() - 0.5) * 10, (Math.random() - 0.5) * 10 - 2] as [number, number, number],
      scale: 0.1 + Math.random() * 0.3,
      speed: 0.05 + Math.random() * 0.15,
      color: colors[i % colors.length],
      phase: Math.random() * Math.PI * 2,
    }))
  }, [isDark])

  const count = reduced ? 400 : 800
  const particleData = useMemo(() => {
    const pos = new Float32Array(count * 3)
    const col = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 25
      pos[i * 3 + 1] = (Math.random() - 0.5) * 16
      pos[i * 3 + 2] = (Math.random() - 0.5) * 16 - 3
      const c = new THREE.Color(colors[i % colors.length])
      col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b
    }
    return { pos, col }
  }, [isDark])

  const geometries = useMemo(() => ({
    box: new THREE.BoxGeometry(0.8, 0.8, 0.8),
    sphere: new THREE.SphereGeometry(0.4, 6, 6),
    torus: new THREE.TorusGeometry(0.35, 0.12, 6, 12),
  }), [])

  useFrame((state, delta) => {
    clockRef.current += delta
    const t = clockRef.current
    const mx = mousePos.current.x
    const my = mousePos.current.y
    const camTargetX = mx * 0.3
    const camTargetY = my * 0.2 + 0.2
    camera.position.x += (camTargetX - camera.position.x) * 0.01
    camera.position.y += (camTargetY - camera.position.y) * 0.01
    camera.lookAt(0, 0, 0)

    if (groupRef.current) {
      groupRef.current.children.forEach((child, i) => {
        const o = objects[i]
        child.rotation.x += delta * 0.5
        child.rotation.y += delta * 0.8 * o.speed
        child.position.y = o.pos[1] + Math.sin(t * 1.5 * o.speed + o.phase) * 0.2
      })
    }
    if (pointsRef.current) {
      const arr = pointsRef.current.geometry.attributes.position.array as Float32Array
      for (let i = 0; i < count; i++) {
        arr[i * 3 + 1] += Math.sin(t + i * 0.5) * 0.003
        arr[i * 3] += Math.cos(t * 1.5 + i * 0.3) * 0.002
        arr[i * 3 + 2] += Math.sin(t * 0.8 + i * 0.2) * 0.0015
      }
      pointsRef.current.geometry.attributes.position.needsUpdate = true
    }
  })

  return (
    <>
      <ambientLight intensity={isDark ? 0.15 : 0.3} />
      <pointLight position={[3, 3, 3]} intensity={intensity * 0.6} color="#CC3A63" />
      <pointLight position={[-3, -2, 2]} intensity={intensity * 0.4} color="#C77B54" />

      <group ref={groupRef}>
        {objects.map((o, i) => (
          <mesh key={i} geometry={geometries[["box", "sphere", "torus"][i % 3] as "box" | "sphere" | "torus"]} position={o.pos} scale={o.scale}>
            <meshPhysicalMaterial color={o.color} transparent opacity={isDark ? 0.3 : 0.2} emissive={o.color} emissiveIntensity={isDark ? 0.12 : 0.04} />
          </mesh>
        ))}
      </group>

      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute args={[particleData.pos, 3]} attach="attributes-position" count={count} array={particleData.pos} itemSize={3} />
          <bufferAttribute args={[particleData.col, 3]} attach="attributes-color" count={count} array={particleData.col} itemSize={3} />
        </bufferGeometry>
        <pointsMaterial size={0.055} vertexColors transparent opacity={0.8} blending={THREE.AdditiveBlending} depthWrite={false} sizeAttenuation />
      </points>
    </>
  )
}

export function SpatialScene({ className, intensity = 0.5, isDark = true, interactive = true, reduced = false }: SpatialSceneProps) {
  const [mounted, setMounted] = useState(false)
  const mousePos = useRef({ x: 0, y: 0 })

  useEffect(() => {
    setMounted(true)
    if (!interactive) return
    const handleMove = (e: MouseEvent) => {
      mousePos.current = {
        x: (e.clientX / window.innerWidth - 0.5) * 2,
        y: -(e.clientY / window.innerHeight - 0.5) * 2,
      }
    }
    window.addEventListener("mousemove", handleMove)
    return () => window.removeEventListener("mousemove", handleMove)
  }, [interactive])

  if (!mounted) return <div className={cn("fixed inset-0", className)} style={{ zIndex: 0 }} />

  return (
    <div className={cn("fixed inset-0 pointer-events-none", className)} style={{ zIndex: 0 }}>
      <Canvas
        camera={{ position: [0, 0.2, 6], fov: 60, near: 0.1, far: 30 }}
        gl={{ antialias: false, alpha: true, powerPreference: "high-performance" }}
        dpr={0.6}
        style={{ background: "transparent", pointerEvents: "none" as const }}
      >
        <Field intensity={intensity} isDark={isDark} mousePos={mousePos} reduced={reduced} />
      </Canvas>
    </div>
  )
}
