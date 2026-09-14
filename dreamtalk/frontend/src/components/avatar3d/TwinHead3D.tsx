"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { Canvas, useFrame, useThree } from "@react-three/fiber"
import { useGLTF, OrbitControls } from "@react-three/drei"
import * as THREE from "three"
import { assetUrl } from "@/services/avatar/client"
import { sampleLipsync, mouthToVisemes } from "@/services/avatar/lipsync"
import type { AvatarProfile, RespondResult } from "@/services/avatar/types"

export interface TwinHead3DProps {
  profile?: AvatarProfile | null
  speech?: RespondResult | null
  className?: string
  glow?: string
  interactive?: boolean
  onEnded?: () => void
}

/** Backend emotion label → the emotion morph target baked into the GLB.
 *
 *  The emotion field is NOT reliably a string: the pipeline returns a richer
 *  object ({ primary_mood, valence, intensity, ... }) on some paths. Calling
 *  .toLowerCase() on that threw "(A || '').toLowerCase is not a function" on
 *  every single frame inside the render loop, so the 3D head never drew at all
 *  — the canvas mounted, the GLB downloaded 200 OK, and the viewport stayed
 *  empty. Normalise before matching. */
function emotionLabel(emotion: unknown): string {
  if (typeof emotion === "string") return emotion
  if (emotion && typeof emotion === "object") {
    const o = emotion as Record<string, unknown>
    const v = o.primary_mood ?? o.mood ?? o.label ?? o.emotion ?? o.name
    if (typeof v === "string") return v
  }
  return ""
}

function emotionTarget(emotion?: unknown): string | null {
  switch (emotionLabel(emotion).toLowerCase()) {
    case "happy": case "joy": case "excited": case "loving": return "happy"
    case "sad": case "sorrow": return "sad"
    case "angry": case "frustrated": return "angry"
    case "surprised": case "fearful": return "surprised"
    default: return null
  }
}

/* eslint-disable @typescript-eslint/no-explicit-any */
function HeadModel({ url, audioRef, keyframesRef, emotionRef, reduced, onFit }: {
  url: string
  audioRef: React.RefObject<HTMLAudioElement | null>
  keyframesRef: React.MutableRefObject<RespondResult["lipsync"] | undefined>
  // `unknown` on purpose: the backend sends a string on some paths and an
  // object on others. emotionLabel() normalises it.
  emotionRef: React.MutableRefObject<unknown>
  reduced: boolean
  onFit: (center: THREE.Vector3, radius: number) => void
}) {
  const { scene } = useGLTF(url) as any
  const meshes = useRef<THREE.Mesh[]>([])
  const blink = useRef({ next: 2.5, closing: 0 })
  const cur = useRef<Record<string, number>>({})

  const model = useMemo(() => {
    const c = scene.clone(true)
    meshes.current = []
    c.traverse((o: any) => {
      o.frustumCulled = false
      if (o.isMesh) {
        o.castShadow = false
        o.receiveShadow = false
        // The generated head is a single closed surface whose triangle winding
        // does not reliably match glTF's CCW convention, so front-face culling
        // showed the inside of the skull. Recompute normals from the geometry
        // (the exported ones lit it from behind) and render both sides.
        if (o.geometry) {
          o.geometry.computeVertexNormals()
          o.geometry.computeBoundingBox()
          o.geometry.computeBoundingSphere()
        }
        const isMouthPart = /teeth|tongue/i.test(o.name || "")
        const mats = Array.isArray(o.material) ? o.material : [o.material]
        mats.forEach((m: any) => {
          if (!m) return
          if (m.map) m.map.colorSpace = THREE.SRGBColorSpace
          if ("metalness" in m) m.metalness = 0
          if ("roughness" in m) {
            // Enamel is glossier than skin; the tongue is wetter still.
            m.roughness = isMouthPart
              ? Math.min(0.6, m.roughness ?? 0.45)
              : Math.min(0.9, Math.max(0.55, m.roughness ?? 0.75))
          }
          // The mouth interior is a closed shell — keep backface culling so we
          // don't see through it; only the head needs DoubleSide for its
          // inconsistent winding.
          m.side = isMouthPart ? THREE.FrontSide : THREE.DoubleSide
          m.flatShading = false
          m.needsUpdate = true
        })
        if (o.morphTargetDictionary && o.morphTargetInfluences) meshes.current.push(o)
      }
    })
    return c
  }, [scene])

  useEffect(() => {
    const box = new THREE.Box3().setFromObject(model)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    onFit(center, Math.max(size.x, size.y) * 0.5)
  }, [model, onFit])

  /** Write a morph influence by name onto every mesh that has it. */
  const setTarget = (name: string, value: number) => {
    for (const mesh of meshes.current) {
      const i = (mesh.morphTargetDictionary as any)?.[name]
      if (i !== undefined && mesh.morphTargetInfluences) mesh.morphTargetInfluences[i] = value
    }
  }

  /* Debug handle, opt-in via ?debug3d.
   *
   * R3F v9 no longer hangs a `__r3f` store off the canvas element, and walking
   * the React fiber tree to reach the scene is fragile enough that it failed
   * outright while diagnosing "the eye blinking is not working". Without a way
   * to read the live morph influences, that question can only be answered by
   * staring at the render, which is exactly how a subtle-but-working blink and
   * a broken one become indistinguishable. `hold` pins a morph so a still
   * screenshot can prove the geometry moves. */
  useEffect(() => {
    if (typeof window === "undefined") return
    if (!new URLSearchParams(window.location.search).has("debug3d")) return
    ;(window as any).__dtTwin = {
      meshes: meshes.current,
      names: () => meshes.current.map((m) => m.name),
      targets: () => Object.keys(meshes.current[0]?.morphTargetDictionary ?? {}),
      read: (name: string) => {
        const m = meshes.current[0]
        const i = (m?.morphTargetDictionary as any)?.[name]
        return i === undefined ? null : m.morphTargetInfluences?.[i]
      },
      /** Pin a morph at `value` (or release with null) despite the frame loop. */
      hold: (name: string | null, value = 1) => {
        ;(window as any).__dtHold = name ? { name, value } : null
      },
    }
  }, [model])

  useFrame((state, delta) => {
    if (reduced || meshes.current.length === 0) return
    const audio = audioRef.current
    const playing = !!audio && !audio.paused && !audio.ended

    // Visemes straight off the audio clock — the same track the 2D renderer uses.
    const target = playing
      ? mouthToVisemes(sampleLipsync(keyframesRef.current, audio!.currentTime))
      : { aa: 0, ih: 0, ou: 0, ee: 0, oh: 0 }

    const k = Math.min(1, delta * 18)   // smoothing: steppy visemes read as robotic
    const c = cur.current
    for (const name of ["aa", "ih", "ou", "ee", "oh"] as const) {
      c[name] = (c[name] ?? 0) + ((target as any)[name] - (c[name] ?? 0)) * k
      setTarget(name, c[name])
    }

    // Emotion overlay while speaking.
    const emo = emotionTarget(emotionRef.current)
    const emoK = Math.min(1, delta * 4)
    for (const name of ["happy", "sad", "angry", "surprised"] as const) {
      const want = playing && emo === name ? 0.6 : 0
      c[name] = (c[name] ?? 0) + (want - (c[name] ?? 0)) * emoK
      setTarget(name, c[name])
    }

    // Blink.
    const b = blink.current
    b.next -= delta
    if (b.next <= 0 && b.closing <= 0) { b.closing = 0.12; b.next = 2.5 + Math.random() * 3.5 }
    let v = 0
    if (b.closing > 0) { b.closing -= delta; v = Math.sin(Math.max(0, b.closing / 0.12) * Math.PI) }
    setTarget("blink", v)

    // Applied last so it wins over this frame's computed influences.
    const hold = typeof window !== "undefined" ? (window as any).__dtHold : null
    if (hold?.name) setTarget(hold.name, hold.value)

    // Gentle idle sway so the head reads alive between utterances.
    const t = state.clock.elapsedTime
    model.rotation.y = Math.sin(t * 0.4) * 0.045 + Math.sin(t * 0.19) * 0.02
    model.rotation.x = Math.sin(t * 0.33) * 0.015
    model.position.y = Math.sin(t * 0.8) * 0.004
  })

  return <primitive object={model} />
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
    const dist = (radius / Math.sin(fov / 2)) * 1.3
    cam.position.set(center.x, center.y, center.z + dist)
    cam.near = dist * 0.05; cam.far = dist * 10
    cam.updateProjectionMatrix(); cam.lookAt(center)
    if (controls.current) { controls.current.target.copy(center); controls.current.update() }
  }, [center, radius, camera])

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
 * The user's own reconstructed head (FLAME GLB from the avatar runtime),
 * animated in-browser via the morph targets the backend bakes in — visemes
 * driven off the cloned-voice audio clock, plus blink and an emotion overlay.
 * This is the real twin, not a stand-in model.
 */
export function TwinHead3D({
  profile, speech, className = "", glow = "var(--primary)", interactive = true, onEnded,
}: TwinHead3DProps) {
  const wrap = useRef<HTMLDivElement>(null)
  const audioRef = useRef<HTMLAudioElement>(null)
  const keyframesRef = useRef(speech?.lipsync)
  const emotionRef = useRef(speech?.response_emotion ?? speech?.emotion)
  const [onScreen, setOnScreen] = useState(true)
  const [docVisible, setDocVisible] = useState(true)
  const [fit, setFit] = useState<{ center: THREE.Vector3; radius: number } | null>(null)
  const reduced = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches

  const headUrl = assetUrl(profile?.appearance?.glb_url)
  const audioUrl = assetUrl(speech?.audio_url ?? speech?.audio?.audio_url)

  useEffect(() => { keyframesRef.current = speech?.lipsync }, [speech?.lipsync])
  useEffect(() => { emotionRef.current = speech?.response_emotion ?? speech?.emotion }, [speech])

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

  if (!headUrl) {
    return (
      <div className={className} style={{ position: "relative" }}>
        <div className="grid h-full w-full place-items-center px-6 text-center text-sm text-foreground-muted">
          This twin has no 3D head yet — recreate it from a clear, front-facing photo.
        </div>
      </div>
    )
  }

  const active = onScreen && docVisible

  return (
    <div ref={wrap} className={className} style={{ position: "relative", touchAction: "none" }}>
      <div className="pointer-events-none absolute inset-0 z-0"
        style={{ background: `radial-gradient(50% 50% at 50% 44%, color-mix(in srgb, ${glow} 9%, transparent), transparent 70%)` }} />
      <Canvas
        frameloop={active ? "always" : "never"}
        dpr={[1, 1.5]}
        camera={{ position: [0, 0, 2.4], fov: 28, near: 0.01, far: 1000 }}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        style={{
          background: "transparent",
          touchAction: "none",
          // Fade to transparent, not to a colour — see GLBAvatar.
          maskImage: "linear-gradient(to bottom, #000 78%, transparent 98%)",
          WebkitMaskImage: "linear-gradient(to bottom, #000 78%, transparent 98%)",
        }}
      >
        <ambientLight intensity={0.9} />
        <directionalLight position={[2, 3, 4]} intensity={1.15} color="#fff3e6" />
        <directionalLight position={[-3, 1, 2]} intensity={0.35} color="#e9f0ff" />
        <hemisphereLight args={["#ffffff", "#4a3d38", 0.55]} />
        <HeadModel
          url={headUrl} audioRef={audioRef} keyframesRef={keyframesRef}
          emotionRef={emotionRef} reduced={!!reduced}
          onFit={(center, radius) => setFit({ center, radius })}
        />
        <Rig center={fit?.center ?? null} radius={fit?.radius ?? 0} interactive={interactive} />
      </Canvas>
      {audioUrl && <audio ref={audioRef} src={audioUrl} onEnded={onEnded} hidden />}
    </div>
  )
}

export default TwinHead3D
