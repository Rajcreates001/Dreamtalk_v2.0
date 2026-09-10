"use client"

import { useRef, useMemo } from "react"
import { useFrame } from "@react-three/fiber"
import * as THREE from "three"
import { DigitalHuman } from "./DigitalHuman"

/* ─── Chamber Rings (Outer → Middle → Inner) ─── */
function ChamberRings() {
  const outerRef = useRef<THREE.Mesh>(null)
  const midRef = useRef<THREE.Mesh>(null)
  const innerRef = useRef<THREE.Mesh>(null)

  useFrame(({ clock }) => {
    const t = clock.elapsedTime

    if (outerRef.current) {
      outerRef.current.rotation.x = Math.sin(t * 0.08) * 0.1
      outerRef.current.rotation.y = t * 0.1
    }

    if (midRef.current) {
      midRef.current.rotation.x = Math.sin(t * 0.12 + 1) * 0.15
      midRef.current.rotation.y = -t * 0.15
    }

    if (innerRef.current) {
      innerRef.current.rotation.x = Math.sin(t * 0.15 + 2) * 0.2
      innerRef.current.rotation.y = t * 0.2
    }
  })

  return (
    <group>
      {/* Outer ring - Energy */}
      <mesh ref={outerRef}>
        <torusGeometry args={[2.8, 0.015, 16, 64]} />
        <meshBasicMaterial color="#CC3A63" transparent opacity={0.15} />
      </mesh>

      {/* Middle ring - Knowledge */}
      <mesh ref={midRef}>
        <torusGeometry args={[2.0, 0.012, 12, 48]} />
        <meshBasicMaterial color="#A2AB73" transparent opacity={0.2} />
      </mesh>

      {/* Inner ring - Voice */}
      <mesh ref={innerRef}>
        <torusGeometry args={[1.3, 0.01, 12, 48]} />
        <meshBasicMaterial color="#CC3A63" transparent opacity={0.15} />
      </mesh>
    </group>
  )
}

/* ─── Energy Pulse Core ─── */
function EnergyPulse() {
  const ref = useRef<THREE.Mesh>(null)
  const ref2 = useRef<THREE.Mesh>(null)
  const phase = useRef(Math.random() * Math.PI * 2)

  useFrame(({ clock }) => {
    const t = clock.elapsedTime * 0.6 + phase.current
    if (ref.current) {
      const scale = 1 + Math.sin(t) * 0.08
      ref.current.scale.set(scale, scale, scale)
      ;(ref.current.material as THREE.MeshBasicMaterial).opacity = 0.06 + Math.sin(t) * 0.04
    }
    if (ref2.current) {
      const scale = 1 + Math.sin(t * 0.7 + 1) * 0.15
      ref2.current.scale.set(scale, scale, scale)
      ;(ref2.current.material as THREE.MeshBasicMaterial).opacity = 0.04 + Math.sin(t * 0.7 + 1) * 0.03
    }
  })

  return (
    <group>
      <mesh ref={ref}>
        <sphereGeometry args={[1.6, 32, 32]} />
        <meshBasicMaterial color="#CC3A63" transparent opacity={0.08} wireframe depthWrite={false} />
      </mesh>
      <mesh ref={ref2}>
        <sphereGeometry args={[1.8, 24, 24]} />
        <meshBasicMaterial color="#A2AB73" transparent opacity={0.04} depthWrite={false} blending={THREE.AdditiveBlending} />
      </mesh>
    </group>
  )
}

/* ─── Orbiting Knowledge Nodes ─── */
function KnowledgeOrbit() {
  const count = 12
  const refs = useRef<(THREE.Mesh | null)[]>([])
  const trailRefs = useRef<(THREE.Mesh | null)[]>([])

  const nodeData = useMemo(() => {
    const data: { radius: number; speed: number; phase: number; yOffset: number; color: string; size: number }[] = []
    for (let i = 0; i < count; i++) {
      const ring = Math.random()
      data.push({
        radius: ring < 0.33 ? 2.0 + Math.random() * 0.4 : ring < 0.66 ? 1.5 + Math.random() * 0.3 : 0.8 + Math.random() * 0.3,
        speed: 0.08 + Math.random() * 0.25,
        phase: (i / count) * Math.PI * 2 + Math.random() * 0.5,
        yOffset: (Math.random() - 0.5) * 0.6,
        color: i % 3 === 0 ? "#CC3A63" : i % 3 === 1 ? "#A2AB73" : "#A2AB73",
        size: 0.025 + Math.random() * 0.04,
      })
    }
    return data
  }, [])

  const colorObjects = useMemo(() =>
    nodeData.map(n => new THREE.Color(n.color)), [nodeData])

  useFrame(({ clock }) => {
    const t = clock.elapsedTime
    for (let i = 0; i < count; i++) {
      const mesh = refs.current[i]
      const trail = trailRefs.current[i]
      if (!mesh) return
      const node = nodeData[i]
      const angle = t * node.speed + node.phase
      const x = Math.cos(angle) * node.radius
      const z = Math.sin(angle) * node.radius * 0.6
      const y = Math.sin(angle * 0.5 + node.phase) * node.yOffset
      mesh.position.set(x, y, z)
      if (trail) {
        trail.position.set(x * 0.9, y * 0.9, z * 0.9)
      }
    }
  })

  return (
    <group>
      {nodeData.map((node, i) => (
        <group key={i}>
          <mesh
            ref={(el) => { refs.current[i] = el }}
          >
            <sphereGeometry args={[node.size, 8, 8]} />
            <meshBasicMaterial color={colorObjects[i]} transparent opacity={0.5} />
          </mesh>
          <mesh
            ref={(el) => { trailRefs.current[i] = el }}
          >
            <sphereGeometry args={[node.size * 2, 8, 8]} />
            <meshBasicMaterial color={colorObjects[i]} transparent opacity={0.08} depthWrite={false} blending={THREE.AdditiveBlending} />
          </mesh>
        </group>
      ))}
    </group>
  )
}

/* ─── Neural Connections Between Nodes ─── */
function NeuralConnections() {
  const count = 15
  const lineRef = useRef<THREE.LineSegments>(null)

  const positions = useMemo(() => {
    const points: THREE.Vector3[] = []
    for (let i = 0; i < count; i++) {
      const radius = 1.0 + Math.random() * 1.8
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      points.push(new THREE.Vector3(
        radius * Math.sin(phi) * Math.cos(theta),
        radius * Math.sin(phi) * Math.sin(theta) * 0.6,
        radius * Math.cos(phi) * 0.5,
      ))
    }

    const pos: number[] = []
    const cols: number[] = []
    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        const dist = points[i].distanceTo(points[j])
        if (dist < 1.2 && dist > 0.2) {
          pos.push(points[i].x, points[i].y, points[i].z)
          pos.push(points[j].x, points[j].y, points[j].z)
          const alpha = 0.06 + Math.random() * 0.1
          cols.push(0.48, 0.36, 1.0, alpha, 0.48, 0.36, 1.0, alpha)
        }
      }
    }
    return new Float32Array(pos)
  }, [])

  useFrame(({ clock }) => {
    if (lineRef.current) {
      lineRef.current.rotation.y = clock.elapsedTime * 0.01
    }
  })

  if (positions.length === 0) return null

  return (
    <lineSegments ref={lineRef}>
      <bufferGeometry>
        <bufferAttribute
          args={[positions, 3]}
          attach="attributes-position"
          count={positions.length / 3}
          itemSize={3}
        />
      </bufferGeometry>
      <lineBasicMaterial color="#CC3A63" transparent opacity={0.08} />
    </lineSegments>
  )
}

/* ─── Data Flow Particles — GPU shader (eliminates needsUpdate=true) ─── */
function DataFlow() {
  const ref = useRef<THREE.Points>(null)
  const count = 8

  // Store start/end positions as vertex attributes for the shader
  const [startPos, endPos, speeds, phases] = useMemo(() => {
    const start = new Float32Array(count * 3)
    const end = new Float32Array(count * 3)
    const spd = new Float32Array(count)
    const ph = new Float32Array(count)
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2
      const startR = 1.0 + Math.random() * 0.3
      const endR = 2.2 + Math.random() * 0.4
      const i3 = i * 3
      start[i3] = Math.cos(angle) * startR
      start[i3 + 1] = (Math.random() - 0.5) * 0.3
      start[i3 + 2] = Math.sin(angle) * startR * 0.5
      end[i3] = Math.cos(angle + 0.3) * endR
      end[i3 + 1] = (Math.random() - 0.5) * 0.5
      end[i3 + 2] = Math.sin(angle + 0.3) * endR * 0.6
      spd[i] = 0.12 + Math.random() * 0.15
      ph[i] = Math.random()
    }
    return [start, end, spd, ph]
  }, [])

  // Custom shader — GPU-accelerated particle animation
  const material = useMemo(() => new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 } },
    vertexShader: `
      uniform float uTime;
      attribute vec3 endPosition;
      attribute float speed;
      attribute float phase;

      void main() {
        float t = mod(uTime * speed * 0.15 + phase, 1.0);
        vec3 pos = mix(position, endPosition, t);
        pos.y += sin(t * 3.14159 * 2.0) * 0.05;

        vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
        gl_PointSize = 0.02 * (300.0 / -mvPosition.z);
        gl_Position = projectionMatrix * mvPosition;
      }
    `,
    fragmentShader: `
      void main() {
        float d = length(gl_PointCoord - vec2(0.5));
        if (d > 0.5) discard;
        float alpha = smoothstep(0.5, 0.0, d) * 0.4;
        gl_FragColor = vec4(0.0, 0.898, 1.0, alpha);
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  }), [])

  useFrame(({ clock }) => {
    material.uniforms.uTime.value = clock.elapsedTime
    if (ref.current) {
      ref.current.rotation.y += 0.002
    }
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute args={[startPos, 3]} attach="attributes-position" count={count} itemSize={3} />
        <bufferAttribute args={[endPos, 3]} attach="attributes-endPosition" count={count} itemSize={3} />
        <bufferAttribute args={[speeds, 1]} attach="attributes-speed" count={count} itemSize={1} />
        <bufferAttribute args={[phases, 1]} attach="attributes-phase" count={count} itemSize={1} />
      </bufferGeometry>
      <primitive object={material} attach="material" />
    </points>
  )
}

/* ─── Main DigitalChamber ─── */
interface DigitalChamberProps {
  mouseReactive?: boolean
}

export function DigitalChamber({ mouseReactive = true }: DigitalChamberProps) {
  return (
    <group>
      {/* Neural connections (back layer) */}
      <NeuralConnections />
      {/* Energy pulse sphere */}
      <EnergyPulse />
      {/* Chamber rings */}
      <ChamberRings />
      {/* Orbiting knowledge nodes */}
      <KnowledgeOrbit />
      {/* Data flow particles */}
      <DataFlow />
      {/* Digital Human at center */}
      <DigitalHuman />
    </group>
  )
}
