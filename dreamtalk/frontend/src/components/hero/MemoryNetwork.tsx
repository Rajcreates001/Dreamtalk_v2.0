"use client"

import { useRef, useMemo } from "react"
import { useFrame } from "@react-three/fiber"
import * as THREE from "three"

export function MemoryNetwork() {
  const ref = useRef<THREE.Points>(null)
  const lineRef = useRef<THREE.LineSegments>(null)

  const [positions, colors, connections] = useMemo(() => {
    const count = 40
    const pos = new Float32Array(count * 3)
    const col = new Float32Array(count * 3)
    const baseColors = [new THREE.Color("#42FFC6"), new THREE.Color("#7C5CFF"), new THREE.Color("#00E5FF")]
    const points: THREE.Vector3[] = []

    for (let i = 0; i < count; i++) {
      const i3 = i * 3
      const radius = 0.3 + Math.random() * 1.5
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      const x = radius * Math.sin(phi) * Math.cos(theta)
      const y = radius * Math.sin(phi) * Math.sin(theta) * 0.6
      const z = radius * Math.cos(phi) * 0.5
      pos[i3] = x
      pos[i3 + 1] = y
      pos[i3 + 2] = z
      points.push(new THREE.Vector3(x, y, z))

      const c = baseColors[i % 3]
      col[i3] = c.r
      col[i3 + 1] = c.g
      col[i3 + 2] = c.b
    }

    const conns: number[] = []
    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        const dist = points[i].distanceTo(points[j])
        if (dist < 1.0 && dist > 0.1) {
          conns.push(points[i].x, points[i].y, points[i].z)
          conns.push(points[j].x, points[j].y, points[j].z)
        }
      }
    }

    return [pos, col, new Float32Array(conns)]
  }, [])

  useFrame(({ clock }) => {
    if (lineRef.current) {
      lineRef.current.rotation.y = clock.elapsedTime * 0.005
    }
  })

  return (
    <group position={[0, 0, -1.5]}>
      {connections.length > 0 && (
        <lineSegments ref={lineRef}>
          <bufferGeometry>
            <bufferAttribute
              args={[connections, 3]}
              attach="attributes-position"
              count={connections.length / 3}
              itemSize={3}
            />
          </bufferGeometry>
          <lineBasicMaterial color="#42FFC6" transparent opacity={0.04} />
        </lineSegments>
      )}
      <points ref={ref}>
        <bufferGeometry>
          <bufferAttribute
            args={[positions, 3]}
            attach="attributes-position"
            count={40}
            itemSize={3}
          />
          <bufferAttribute
            args={[colors, 3]}
            attach="attributes-color"
            count={40}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.02}
          vertexColors
          transparent
          opacity={0.3}
          sizeAttenuation
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>
    </group>
  )
}
