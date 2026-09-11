"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { Canvas, useFrame } from "@react-three/fiber"
import { useGLTF, OrbitControls, Bounds } from "@react-three/drei"
import * as THREE from "three"

export interface GLBAvatarProps {
  url?: string
  speaking?: boolean
  autoSpeak?: boolean
  interactive?: boolean
  className?: string
  glow?: string
  /** apply a skin tone to any material that has no colour texture (raw heads) */
  skinColor?: string
  /** slow auto-rotate so the whole avatar is visible from all sides */
  autoRotate?: boolean
}

const DEFAULT_URL = "/models/angelica.glb"

/* eslint-disable @typescript-eslint/no-explicit-any */
function Model({ url, speaking, autoSpeak, skinColor, reduced }: {
  url: string; speaking: boolean; autoSpeak: boolean; skinColor?: string; reduced: boolean
}) {
  const { scene } = useGLTF(url, true) as any
  const mouth = useRef<THREE.Object3D | null>(null)
  const eyes = useRef<THREE.Object3D[]>([])
  const mouthBase = useRef({ y: 0, sy: 1 })
  const talk = useRef({ open: 0, burstUntil: 0, next: 1 })
  const blink = useRef({ next: 2.5, closing: 0 })

  const model = useMemo(() => {
    const c = scene.clone(true)
    eyes.current = []
    const strip: any[] = []
    c.traverse((o: any) => {
      if (o.isCamera || o.isLight || /camera|sun|light/i.test(o.name)) { strip.push(o); return }
      o.frustumCulled = false
      if (o.name === "Mouth" || o.name === "Mouth_Mouth_0") mouth.current = o
      if (/^(Eye|Eyelashes|EyeScleraReflect|MeniscusEye)/.test(o.name)) eyes.current.push(o)
      if (o.isMesh) {
        o.castShadow = false; o.receiveShadow = false
        const mats = Array.isArray(o.material) ? o.material : [o.material]
        mats.forEach((m: any) => {
          if (!m) return
          if (m.map) m.map.colorSpace = THREE.SRGBColorSpace
          if (skinColor && !m.map) m.color = new THREE.Color(skinColor)
          m.needsUpdate = true
        })
      }
    })
    strip.forEach((o) => o.removeFromParent())
    if (mouth.current) mouthBase.current = { y: mouth.current.position.y, sy: mouth.current.scale.y }
    return c
  }, [scene, skinColor])

  useFrame((state, delta) => {
    if (reduced) return
    const t = state.clock.elapsedTime

    // Lip-sync — drive the separate Mouth mesh
    const k = talk.current
    const isSpeaking = speaking || (autoSpeak && t < k.burstUntil)
    if (autoSpeak && !speaking && t > k.next) { k.burstUntil = t + 1.6 + Math.random() * 2.0; k.next = k.burstUntil + 1.6 + Math.random() * 3 }
    let want = 0
    if (isSpeaking) want = Math.min(1, 0.5 + 0.5 * Math.abs(Math.sin(t * 16) * 0.6 + Math.sin(t * 25) * 0.4))
    k.open += (want - k.open) * Math.min(1, delta * 18)
    if (mouth.current) {
      mouth.current.scale.y = mouthBase.current.sy * (1 + k.open * 0.9)
      mouth.current.position.y = mouthBase.current.y - k.open * 0.012
    }

    // Blink — briefly flatten the eye group (no eyelid rig on this mesh)
    const b = blink.current
    if (t > b.next && b.closing <= 0) { b.closing = 0.13; b.next = t + 2.8 + Math.random() * 3.5 }
    let eyeSy = 1
    if (b.closing > 0) { b.closing -= delta; eyeSy = Math.max(0.06, Math.abs(Math.sin((b.closing / 0.13) * Math.PI))) }
    eyes.current.forEach((e) => { e.scale.y = eyeSy })
  })

  return <primitive object={model} />
}
/* eslint-enable @typescript-eslint/no-explicit-any */

/**
 * Realistic GLB avatar — auto-framed to fit (never cropped) via <Bounds>,
 * drag-to-rotate + slow 360° auto-rotate, mouth lip-sync + blink. PERF: the
 * render loop pauses when the avatar is off-screen or the tab is hidden.
 */
export function GLBAvatar({
  url = DEFAULT_URL, speaking = false, autoSpeak = true, interactive = true,
  className = "", glow = "#CC3A63", skinColor, autoRotate = true,
}: GLBAvatarProps) {
  const wrap = useRef<HTMLDivElement>(null)
  const [onScreen, setOnScreen] = useState(true)
  const [docVisible, setDocVisible] = useState(true)
  const reduced = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches

  useEffect(() => {
    const el = wrap.current
    if (!el) return
    const io = new IntersectionObserver(([e]) => setOnScreen(e.isIntersecting), { rootMargin: "120px" })
    io.observe(el)
    const onVis = () => setDocVisible(!document.hidden)
    document.addEventListener("visibilitychange", onVis)
    return () => { io.disconnect(); document.removeEventListener("visibilitychange", onVis) }
  }, [])

  const active = onScreen && docVisible

  return (
    <div ref={wrap} className={className} style={{ position: "relative" }}>
      <div className="pointer-events-none absolute inset-0" style={{ background: `radial-gradient(48% 48% at 50% 46%, ${glow}26, transparent 72%)` }} />
      <Canvas
        frameloop={active ? "always" : "never"}
        dpr={[1, 1.6]}
        camera={{ position: [0, 0, 3], fov: 30, near: 0.01, far: 1000 }}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        style={{ background: "transparent" }}
      >
        <ambientLight intensity={1.05} />
        <directionalLight position={[2, 3, 4]} intensity={1.7} color="#fff5ea" />
        <directionalLight position={[-3, 1, 2]} intensity={0.7} color={glow} />
        <directionalLight position={[0, 1, -4]} intensity={0.5} color="#ffffff" />
        <Bounds fit clip observe margin={1.1}>
          <Model url={url} speaking={speaking} autoSpeak={autoSpeak} skinColor={skinColor} reduced={!!reduced} />
        </Bounds>
        <OrbitControls
          makeDefault
          enablePan={false}
          enableZoom={false}
          autoRotate={autoRotate && !reduced}
          autoRotateSpeed={0.7}
          enabled={interactive}
          minPolarAngle={Math.PI * 0.36}
          maxPolarAngle={Math.PI * 0.6}
          rotateSpeed={0.6}
        />
      </Canvas>
    </div>
  )
}

useGLTF.preload(DEFAULT_URL)

export default GLBAvatar
