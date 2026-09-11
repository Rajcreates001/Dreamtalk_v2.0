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
  const eyeball = useRef<THREE.Object3D | null>(null)
  const eyes = useRef<THREE.Object3D[]>([])
  const blink = useRef({ next: 3, closing: 0 })
  const saccade = useRef({ next: 1.5, x: 0, y: 0, tx: 0, ty: 0 })

  const model = useMemo(() => {
    const c = scene.clone(true)
    eyes.current = []; headMesh.current = null; eyeball.current = null
    const strip: any[] = []
    c.traverse((o: any) => {
      if (o.isCamera || o.isLight || /camera|sun|light/i.test(o.name)) { strip.push(o); return }
      o.frustumCulled = false
      if (/Head/.test(o.name) && o.isMesh && !headMesh.current) headMesh.current = o
      // The eyeball node (holds the iris) — rotated for subtle life (saccades).
      if (o.name === "Eye") eyeball.current = o
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
          // Hair ships with a grey emissive + a harsh alpha cutoff → plastic
          // wash and a bald crown. Kill the emissive and soften the cutoff.
          if (m.name === "Hair") {
            if (m.emissive) m.emissive.setScalar(0)
            m.emissiveIntensity = 0
            m.emissiveMap = null
            if ("alphaTest" in m && m.alphaTest > 0) m.alphaTest = 0.22
            m.transparent = false
            m.depthWrite = true
            if ("roughness" in m) m.roughness = 0.55
          } else if ("roughness" in m && (m.roughness === undefined || m.roughness > 0.9)) {
            m.roughness = 0.7
          }
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
      // Gentle, natural idle sway + a slow breath (not a mechanical spin)
      g.rotation.y = Math.sin(t * 0.45) * 0.05 + Math.sin(t * 0.2) * 0.025
      g.rotation.x = Math.sin(t * 0.37) * 0.018
      g.position.y = Math.sin(t * 0.8) * 0.004
    }
    // Eye saccades — the eyeball flicks to a new point every ~2s, giving life
    // without blendshapes (this mesh has none).
    const s = saccade.current
    s.next -= delta
    if (s.next <= 0) { s.tx = (Math.random() - 0.5) * 0.14; s.ty = (Math.random() - 0.5) * 0.08; s.next = 1.2 + Math.random() * 2.5 }
    s.x += (s.tx - s.x) * Math.min(1, delta * 10)
    s.y += (s.ty - s.y) * Math.min(1, delta * 10)
    if (eyeball.current) { eyeball.current.rotation.y = s.x; eyeball.current.rotation.x = s.y }
    // Subtle blink — never fully collapses the eye
    const b = blink.current
    if (t > b.next && b.closing <= 0) { b.closing = 0.14; b.next = t + 3 + Math.random() * 3.5 }
    let eyeSy = 1
    if (b.closing > 0) { b.closing -= delta; eyeSy = 1 - 0.62 * Math.abs(Math.sin((b.closing / 0.14) * Math.PI)) }
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
    <div ref={wrap} className={className} style={{ position: "relative", touchAction: "none" }}>
      <div className="pointer-events-none absolute inset-0 z-0" style={{ background: `radial-gradient(50% 50% at 50% 44%, ${glow}18, transparent 70%)` }} />
      <Canvas
        frameloop={active ? "always" : "never"}
        dpr={[1, 1.25]}
        camera={{ position: [0, 0, 3], fov: 28, near: 0.01, far: 1000 }}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        style={{ background: "transparent", touchAction: "none" }}
      >
        {/* Balanced portrait lighting — bright enough to read the face, low
            enough that the iris and skin textures don't blow out to white. */}
        <ambientLight intensity={0.85} />
        <directionalLight position={[2, 3, 4]} intensity={1.15} color="#fff3e6" />
        <directionalLight position={[-3, 1, 2]} intensity={0.35} color="#e9f0ff" />
        <hemisphereLight args={["#ffffff", "#4a3d38", 0.55]} />
        <Model url={url} skinColor={skinColor} reduced={!!reduced}
          onFit={(center, radius) => setFit({ center, radius })} />
        <Rig center={fit?.center ?? null} radius={fit?.radius ?? 0} interactive={interactive} />
      </Canvas>
      {/* Blend the base of the avatar into the page background (no hard edge). */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 h-1/4"
        style={{ background: "linear-gradient(to top, var(--background), transparent)" }} />
    </div>
  )
}

useGLTF.preload(DEFAULT_URL)

export default GLBAvatar
