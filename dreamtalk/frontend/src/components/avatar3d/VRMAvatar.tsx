"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { Canvas, useFrame, useLoader, useThree } from "@react-three/fiber"
import { OrbitControls } from "@react-three/drei"
import { GLTFLoader } from "three-stdlib"
import * as THREE from "three"
import { VRMLoaderPlugin, VRMUtils, type VRM } from "@pixiv/three-vrm"
import { assetUrl } from "@/services/avatar/client"
import { sampleLipsync, mouthToVisemes } from "@/services/avatar/lipsync"
import type { RespondResult } from "@/services/avatar/types"

export interface VRMAvatarProps {
  url?: string
  speech?: RespondResult | null
  className?: string
  glow?: string
  interactive?: boolean
  onEnded?: () => void
}

const DEFAULT_URL = "/models/utsuwa.vrm"

/** Map the backend's coarse emotion label to a VRM expression preset. */
function emotionPreset(emotion?: string): string | null {
  switch ((emotion || "").toLowerCase()) {
    case "happy": case "joy": case "excited": return "happy"
    case "sad": case "sorrow": return "sad"
    case "angry": case "anger": return "angry"
    case "surprised": case "surprise": return "surprised"
    case "calm": case "neutral": case "relaxed": return "relaxed"
    default: return null
  }
}

/* eslint-disable @typescript-eslint/no-explicit-any */
function VRMModel({ url, audioRef, keyframesRef, emotionRef, reduced, onFit }: {
  url: string
  audioRef: React.RefObject<HTMLAudioElement | null>
  keyframesRef: React.MutableRefObject<RespondResult["lipsync"] | undefined>
  emotionRef: React.MutableRefObject<string | undefined>
  reduced: boolean
  onFit: (center: THREE.Vector3, dist: number) => void
}) {
  const gltf = useLoader(GLTFLoader, url, (loader) => {
    // three-stdlib and three-vrm carry slightly different GLTFParser types.
    ;(loader as any).register((parser: any) => new VRMLoaderPlugin(parser))
  }) as any

  const vrm: VRM | undefined = gltf.userData?.vrm
  const blink = useRef({ next: 2, closing: 0 })
  const cur = useRef({ aa: 0, ih: 0, ou: 0, ee: 0, oh: 0, emo: 0 })

  const scene = useMemo(() => {
    if (!vrm) return null
    // VRM0 faces -Z; rotate so it looks at the camera (+Z).
    VRMUtils.rotateVRM0(vrm)
    try { VRMUtils.removeUnnecessaryJoints(vrm.scene) } catch { /* v3 optional */ }
    vrm.scene.traverse((o: any) => { o.frustumCulled = false })
    // Relax the spring bones a touch so idle hair/cloth doesn't jitter.
    if (vrm.springBoneManager) { try { vrm.springBoneManager.reset() } catch { /* noop */ } }
    return vrm.scene
  }, [vrm])

  // Frame the camera on the head bone (fallback: bounding box).
  useEffect(() => {
    if (!vrm || !scene) return
    scene.updateWorldMatrix(true, true)
    const head = vrm.humanoid?.getNormalizedBoneNode?.("head") as THREE.Object3D | null
    const center = new THREE.Vector3()
    if (head) head.getWorldPosition(center)
    else new THREE.Box3().setFromObject(scene).getCenter(center)
    center.y += 0.06 // aim slightly above the head bone → eye line
    const box = new THREE.Box3().setFromObject(scene)
    const headSize = Math.max(0.18, (box.max.y - center.y) * 1.4)
    onFit(center, headSize)
  }, [vrm, scene, onFit])

  useFrame((_state, delta) => {
    if (!vrm) return
    const em = vrm.expressionManager
    if (em && !reduced) {
      const audio = audioRef.current
      const playing = !!audio && !audio.paused && !audio.ended
      const target = playing
        ? mouthToVisemes(sampleLipsync(keyframesRef.current, audio!.currentTime))
        : { aa: 0, ih: 0, ou: 0, ee: 0, oh: 0 }
      // Smooth toward the target so mouth motion reads natural, not steppy.
      const k = Math.min(1, delta * 18)
      const c = cur.current
      c.aa += (target.aa - c.aa) * k; c.ih += (target.ih - c.ih) * k
      c.ou += (target.ou - c.ou) * k; c.ee += (target.ee - c.ee) * k
      c.oh += (target.oh - c.oh) * k
      em.setValue("aa", c.aa); em.setValue("ih", c.ih)
      em.setValue("ou", c.ou); em.setValue("ee", c.ee); em.setValue("oh", c.oh)

      // Emotion overlay (eases in while an utterance is active).
      const preset = emotionPreset(emotionRef.current)
      const emoTarget = playing && preset ? 0.55 : 0
      c.emo += (emoTarget - c.emo) * Math.min(1, delta * 4)
      for (const p of ["happy", "sad", "angry", "surprised", "relaxed"]) {
        try { em.setValue(p, p === preset ? c.emo : 0) } catch { /* preset may be absent */ }
      }

      // Blink.
      const b = blink.current
      b.next -= delta
      if (b.next <= 0 && b.closing <= 0) { b.closing = 0.12; b.next = 2.5 + Math.random() * 3.5 }
      let blinkV = 0
      if (b.closing > 0) { b.closing -= delta; blinkV = Math.sin(Math.max(0, b.closing / 0.12) * Math.PI) }
      try { em.setValue("blink", blinkV) } catch { /* noop */ }

      // Breathing + micro-sway on the spine so idle isn't a mannequin.
      const t = _state.clock.elapsedTime
      const spine = vrm.humanoid?.getNormalizedBoneNode?.("spine") as THREE.Object3D | null
      if (spine) {
        spine.rotation.x = Math.sin(t * 0.9) * 0.012
        spine.rotation.y = Math.sin(t * 0.4) * 0.02
      }
    }
    vrm.update(delta)
  })

  if (!scene) return null
  return <primitive object={scene} />
}

function Rig({ center, dist, interactive }: {
  center: THREE.Vector3 | null; dist: number; interactive: boolean
}) {
  const { camera } = useThree()
  const controls = useRef<any>(null)
  useEffect(() => {
    if (!center || dist <= 0) return
    const cam = camera as THREE.PerspectiveCamera
    const fov = (cam.fov * Math.PI) / 180
    const d = (dist / Math.sin(fov / 2)) * 1.15
    cam.position.set(center.x, center.y, center.z + d)
    cam.near = d * 0.05; cam.far = d * 12
    cam.updateProjectionMatrix(); cam.lookAt(center)
    if (controls.current) { controls.current.target.copy(center); controls.current.update() }
  }, [center, dist, camera])

  if (!center) return null
  return (
    <OrbitControls
      ref={controls}
      target={[center.x, center.y, center.z]}
      makeDefault enablePan={false} enableZoom={false} autoRotate={false}
      enabled={interactive}
      minPolarAngle={Math.PI / 2} maxPolarAngle={Math.PI / 2} rotateSpeed={0.7}
    />
  )
}
/* eslint-enable @typescript-eslint/no-explicit-any */

/**
 * Rigged 3D digital human (VRM). Drives the five standard mouth visemes from
 * the backend's `lipsync` track, sampled off the cloned-voice audio clock —
 * real lip-sync, not a scaled mesh. Idle blink, breathing and an emotion
 * overlay keep it alive between utterances. Horizontal-only orbit; the render
 * loop pauses when off-screen or the tab is hidden.
 */
export function VRMAvatar({
  url = DEFAULT_URL, speech, className = "", glow = "#CC3A63", interactive = true, onEnded,
}: VRMAvatarProps) {
  const wrap = useRef<HTMLDivElement>(null)
  const audioRef = useRef<HTMLAudioElement>(null)
  const keyframesRef = useRef(speech?.lipsync)
  const emotionRef = useRef(speech?.response_emotion ?? speech?.emotion)
  const [onScreen, setOnScreen] = useState(true)
  const [docVisible, setDocVisible] = useState(true)
  const [fit, setFit] = useState<{ center: THREE.Vector3; dist: number } | null>(null)
  const reduced = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches

  const audioUrl = assetUrl(speech?.audio_url ?? speech?.audio?.audio_url)

  useEffect(() => { keyframesRef.current = speech?.lipsync }, [speech?.lipsync])
  useEffect(() => { emotionRef.current = speech?.response_emotion ?? speech?.emotion }, [speech])

  // Play each new utterance; the useFrame loop reads this element's clock.
  useEffect(() => {
    const a = audioRef.current
    if (a && audioUrl) { a.currentTime = 0; a.play().catch(() => {}) }
  }, [audioUrl])

  useEffect(() => {
    const el = wrap.current
    if (!el) return
    const io = new IntersectionObserver(([e]) => setOnScreen(e.isIntersecting), { rootMargin: "80px" })
    io.observe(el)
    const onVis = () => setDocVisible(!document.hidden)
    document.addEventListener("visibilitychange", onVis)
    const fire = () => window.dispatchEvent(new Event("resize"))
    const ro = new ResizeObserver(fire); ro.observe(el)
    const t1 = setTimeout(fire, 80); const t2 = setTimeout(fire, 400)
    return () => {
      io.disconnect(); ro.disconnect()
      document.removeEventListener("visibilitychange", onVis)
      clearTimeout(t1); clearTimeout(t2)
    }
  }, [])

  const active = onScreen && docVisible

  return (
    <div ref={wrap} className={className} style={{ position: "relative" }}>
      <div className="pointer-events-none absolute inset-0"
        style={{ background: `radial-gradient(50% 50% at 50% 42%, ${glow}20, transparent 72%)` }} />
      <Canvas
        frameloop={active ? "always" : "never"}
        dpr={[1, 1.5]}
        camera={{ position: [0, 1.3, 1.2], fov: 26, near: 0.01, far: 1000 }}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        style={{ background: "transparent" }}
      >
        <ambientLight intensity={1.4} />
        <directionalLight position={[1.5, 2.5, 3]} intensity={2.0} color="#fff5ea" />
        <hemisphereLight args={["#ffffff", "#5a4a44", 0.7]} />
        <VRMModel
          url={url} audioRef={audioRef} keyframesRef={keyframesRef} emotionRef={emotionRef}
          reduced={!!reduced} onFit={(center, dist) => setFit({ center, dist })}
        />
        <Rig center={fit?.center ?? null} dist={fit?.dist ?? 0} interactive={interactive} />
      </Canvas>
      {audioUrl && <audio ref={audioRef} src={audioUrl} onEnded={onEnded} hidden />}
    </div>
  )
}

export default VRMAvatar
