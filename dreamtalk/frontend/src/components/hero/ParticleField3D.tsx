"use client"

import { useRef, useMemo } from "react"
import { useFrame } from "@react-three/fiber"
import * as THREE from "three"

// Local mouse tracker (component is no longer connected to HeroContainer)
const mouseRef = { x: 0.5, y: 0.5 }

interface ParticleField3DProps {
  count?: number
  color?: string
  speed?: number
  size?: number
  spread?: number
  mouseReactive?: boolean
}

/**
 * GPU-accelerated particle field using custom ShaderMaterial.
 *
 * PERFORMANCE FIX (Phase 12 — Particle System Rewrite):
 * Previous code used useFrame to mutate a Float32Array of positions and
 * flagged needsUpdate=true every frame. This caused a CPU→GPU vertex buffer
 * upload every 16ms — the #1 sin in Three.js optimization.
 *
 * FIX: Custom ShaderMaterial with vertex shader animation.
 * - All particle positions are computed on the GPU (zero CPU cost).
 * - Only one uniform (uTime) is updated per frame (8 bytes vs 2.4KB).
 * - No buffer uploads, no geometry.needsUpdate = true.
 * - Mouse reactivity via mouseRef — used in CPU to slowly rotate the group,
 *   which triggers a single matrix update (negligible cost).
 */
export function ParticleField3D({
  count: requestedCount,
  color = "#CC3A63",
  speed = 0.12,
  size = 0.015,
  spread = 12,
  mouseReactive = true,
}: ParticleField3DProps) {
  const ref = useRef<THREE.Points>(null)
  const count = requestedCount ?? 120

  // Generate initial positions + colors once (GPU-resident, never updated)
  const [positions, colors] = useMemo(() => {
    const pos = new Float32Array(count * 3)
    const col = new Float32Array(count * 3)
    const baseColor = new THREE.Color(color)
    const secondaryColor = new THREE.Color("#A2AB73")

    for (let i = 0; i < count; i++) {
      const i3 = i * 3
      const radius = Math.random() * spread
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      pos[i3] = radius * Math.sin(phi) * Math.cos(theta)
      pos[i3 + 1] = radius * Math.sin(phi) * Math.sin(theta)
      pos[i3 + 2] = radius * Math.cos(phi)

      const mix = Math.random()
      const c = baseColor.clone().lerp(secondaryColor, mix)
      col[i3] = c.r
      col[i3 + 1] = c.g
      col[i3 + 2] = c.b
    }
    return [pos, col]
  }, [count, spread, color])

  // Custom ShaderMaterial — particle animation runs entirely on GPU
  const material = useMemo(() => {
    const uTime = { value: 0 }
    const speedUniform = speed

    return new THREE.ShaderMaterial({
      uniforms: { uTime },
      vertexShader: `
        uniform float uTime;
        attribute vec3 customColor;
        varying vec3 vColor;

        void main() {
          vColor = customColor;

          vec3 pos = position;
          float phase = pos.x * 0.015;
          float t = uTime * ${speedUniform.toFixed(3)};

          // Animate on GPU — zero CPU cost, no buffer upload
          pos.x += sin(t + phase) * 0.2;
          pos.y += cos(t * 0.7 + phase) * 0.2;
          pos.z += sin(t * 0.5 + phase) * 0.05;

          vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
          gl_PointSize = ${size.toFixed(4)} * (300.0 / -mvPosition.z);
          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        varying vec3 vColor;

        void main() {
          // Soft circular point
          vec2 center = gl_PointCoord - vec2(0.5);
          float dist = length(center);
          if (dist > 0.5) discard;

          float alpha = smoothstep(0.5, 0.0, dist) * 0.6;
          gl_FragColor = vec4(vColor, alpha);
        }
      `,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    })
  }, [size, speed])

  // Only update ONE uniform (8 bytes) per frame — no buffer uploads
  useFrame(({ clock }) => {
    material.uniforms.uTime.value = clock.elapsedTime

    // Mouse-reactive rotation on CPU — cheap matrix update, no buffer upload
    if (ref.current && mouseReactive) {
      const mx = mouseRef.x - 0.5
      const my = mouseRef.y - 0.5
      ref.current.rotation.y += (mx * 0.15 - ref.current.rotation.y) * 0.02
      ref.current.rotation.x += (my * -0.1 - ref.current.rotation.x) * 0.02
    }
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute
          args={[positions, 3]}
          attach="attributes-position"
          count={count}
          itemSize={3}
        />
        <bufferAttribute
          args={[colors, 3]}
          attach="attributes-customColor"
          count={count}
          itemSize={3}
        />
      </bufferGeometry>
      <primitive object={material} attach="material" />
    </points>
  )
}
