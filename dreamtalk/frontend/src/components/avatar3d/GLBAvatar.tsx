"use client"

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react"
import { Canvas, useFrame, useThree } from "@react-three/fiber"
import { useGLTF, OrbitControls } from "@react-three/drei"
import * as THREE from "three"

export interface GLBAvatarProps {
  url?: string
  speaking?: boolean
  autoSpeak?: boolean
  interactive?: boolean
  className?: string
  glow?: string
  skinColor?: string
  autoRotate?: boolean
}

const DEFAULT_URL = "/models/angelica.glb"

/* eslint-disable @typescript-eslint/no-explicit-any */
function Model({ url, skinColor, reduced, onFit }: {
  url: string; skinColor?: string; reduced: boolean
  onFit: (center: THREE.Vector3, radius: number) => void
}) {
  const { scene } = useGLTF(url, true) as any
  const root = useRef<THREE.Group>(null)
  const headMesh = useRef<THREE.Object3D | null>(null)
  const eyes = useRef<THREE.Object3D[]>([])
  const blink = useRef({ next: 3, closing: 0 })

  const model = useMemo(() => {
    const c = scene.clone(true)
    eyes.current = []; headMesh.current = null
    const strip: any[] = []
    c.traverse((o: any) => {
      if (o.isCamera || o.isLight || /camera|sun|light/i.test(o.name)) { strip.push(o); return }
      o.frustumCulled = false
      if (/Head/.test(o.name) && o.isMesh && !headMesh.current) headMesh.current = o
      // Wet-eye reflection layers render as a white film over the iris — hide them.
      if (/^(EyeScleraReflect|MeniscusEye)/.test(o.name) && o.isMesh) { o.visible = false; return }
      if (/^Eye($|_|lashes)/.test(o.name)) eyes.current.push(o)
      if (o.isMesh) {
        o.castShadow = false; o.receiveShadow = false
        const mats = Array.isArray(o.material) ? o.material : [o.material]
        mats.forEach((m: any) => {
          if (!m) return
          if (m.map) m.map.colorSpace = THREE.SRGBColorSpace
          if (skinColor && !m.map) m.color = new THREE.Color(skinColor)
          if ("metalness" in m) m.metalness = 0
          if ("roughness" in m && (m.roughness === undefined || m.roughness > 0.9)) m.roughness = 0.7
          m.needsUpdate = true
        })
      }
    })
    strip.forEach((o) => o.removeFromParent())
    return c
  }, [scene, skinColor])

  useLayoutEffect(() => {
    if (!root.current) return
    root.current.updateWorldMatrix(true, true)
    const target = headMesh.current || model
    const box = new THREE.Box3().setFromObject(target)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    const radius = Math.max(size.x, size.y) * 0.5
    onFit(center, radius)
  }, [model, onFit])

  useFrame((state, delta) => {
    if (reduced) return
    const t = state.clock.elapsedTime
    const g = root.current
    if (g) {
      // Gentle, natural idle sway (not a mechanical spin)
      g.rotation.y = Math.sin(t * 0.45) * 0.05 + Math.sin(t * 0.2) * 0.025
      g.rotation.x = Math.sin(t * 0.37) * 0.018
    }
    // Subtle blink — never fully collapses the eye
    const b = blink.current
    if (t > b.next && b.closing <= 0) { b.closing = 0.14; b.next = t + 3 + Math.random() * 3.5 }
    let eyeSy = 1
    if (b.closing > 0) { b.closing -= delta; eyeSy = 1 - 0.72 * Math.abs(Math.sin((b.closing / 0.14) * Math.PI)) }
    eyes.current.forEach((e) => { e.scale.y = eyeSy })
  })

  return <group ref={root}><primitive object={model} /></group>
}

function Rig({ center, radius, interactive }: {
  center: THREE.Vector3 | null; radius: number; interactive: boolean
}) {
  const { camera } = useThree()
  const controls = useRef<any>(null)
  useEffect(() => {
    if (!center || radius <= 0) return
    const cam = camera as THREE.PerspectiveCamera
    const fov = (cam.fov * Math.PI) / 180
    const dist = (radius / Math.sin(fov / 2)) * 1.35
    cam.position.set(center.x, center.y, center.z + dist)
    cam.near = dist * 0.05
    cam.far = dist * 8
    cam.updateProjectionMatrix()
    cam.lookAt(center)
    if (controls.current) { controls.current.target.copy(center); controls.current.update() }
  }, [center, radius, camera])

  if (!center) return null
  return (
    <OrbitControls
      ref={controls}
      target={[center.x, center.y, center.z]}
      makeDefault
      enablePan={false}
      enableZoom={false}
      autoRotate={false}
      enabled={interactive}
      minPolarAngle={Math.PI / 2}
      maxPolarAngle={Math.PI / 2}
      rotateSpeed={0.7}
    />
  )
}
/* eslint-enable @typescript-eslint/no-explicit-any */

/**
 * Realistic GLB avatar — head-framed (large, upright), horizontal 360° drag
 * (vertical locked), subtle natural sway + blink. PERF: low dpr, few lights,
 * and the render loop pauses when off-screen or the tab is hidden.
 */
export function GLBAvatar({
  url = DEFAULT_URL, interactive = true, className = "", glow = "#CC3A63", skinColor,
}: GLBAvatarProps) {
  const wrap = useRef<HTMLDivElement>(null)
  const [onScreen, setOnScreen] = useState(true)
  const [docVisible, setDocVisible] = useState(true)
  const [fit, setFit] = useState<{ center: THREE.Vector3; radius: number } | null>(null)
  const reduced = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches

  useEffect(() => {
    const el = wrap.current
    if (!el) return
    const io = new IntersectionObserver(([e]) => setOnScreen(e.isIntersecting), { rootMargin: "80px" })
    io.observe(el)
    const onVis = () => setDocVisible(!document.hidden)
    document.addEventListener("visibilitychange", onVis)
    const fire = () => window.dispatchEvent(new Event("resize"))
    const ro = new ResizeObserver(fire)
    ro.observe(el)
    const t1 = setTimeout(fire, 80)
    const t2 = setTimeout(fire, 400)
    return () => {
      io.disconnect(); ro.disconnect()
      document.removeEventListener("visibilitychange", onVis)
      clearTimeout(t1); clearTimeout(t2)
    }
  }, [])

  const active = onScreen && docVisible

  return (
    <div ref={wrap} className={className} style={{ position: "relative" }}>
      <div className="pointer-events-none absolute inset-0" style={{ background: `radial-gradient(50% 50% at 50% 46%, ${glow}20, transparent 72%)` }} />
      <Canvas
        frameloop={active ? "always" : "never"}
        dpr={[1, 1.25]}
        camera={{ position: [0, 0, 3], fov: 28, near: 0.01, far: 1000 }}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        style={{ background: "transparent" }}
      >
        <ambientLight intensity={1.75} />
        <directionalLight position={[2, 3, 4]} intensity={2.3} color="#fff5ea" />
        <hemisphereLight args={["#ffffff", "#5a4a44", 0.9]} />
        <Model url={url} skinColor={skinColor} reduced={!!reduced}
          onFit={(center, radius) => setFit({ center, radius })} />
        <Rig center={fit?.center ?? null} radius={fit?.radius ?? 0} interactive={interactive} />
      </Canvas>
    </div>
  )
}

useGLTF.preload(DEFAULT_URL)

export default GLBAvatar
