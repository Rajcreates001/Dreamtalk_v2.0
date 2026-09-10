"use client"

import { useRef } from "react"
import { useFrame } from "@react-three/fiber"
import type * as THREE from "three"

/* ─── Key Light ─── */
function KeyLight() {
  const ref = useRef<THREE.DirectionalLight>(null)
  useFrame(({ mouse }) => {
    if (ref.current) {
      ref.current.position.x = 2 + mouse.x * 0.5
      ref.current.position.y = 3 + mouse.y * -0.3
    }
  })
  return (
    <directionalLight
      ref={ref}
      position={[2, 3, 4]}
      intensity={0.4}
      color="#CC3A63"
    />
  )
}

/* ─── Rim Light ─── */
function RimLight() {
  const ref = useRef<THREE.DirectionalLight>(null)
  useFrame(({ mouse }) => {
    if (ref.current) {
      ref.current.position.x = -3 + mouse.x * -0.3
      ref.current.position.y = 1 + mouse.y * 0.2
    }
  })
  return (
    <directionalLight
      ref={ref}
      position={[-3, 1, -2]}
      intensity={0.3}
      color="#A2AB73"
    />
  )
}

/* ─── Fill Light ─── */
function FillLight() {
  return (
    <directionalLight
      position={[0, -1, -3]}
      intensity={0.15}
      color="#A2AB73"
    />
  )
}

/* ─── Ambient Glow ─── */
function AmbientGlow() {
  return (
    <ambientLight intensity={0.15} color="#CC3A63" />
  )
}

export function HeroLighting() {
  return (
    <>
      <KeyLight />
      <RimLight />
      <FillLight />
      <AmbientGlow />
    </>
  )
}
