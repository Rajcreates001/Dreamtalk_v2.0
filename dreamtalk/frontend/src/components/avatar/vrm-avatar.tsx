"use client"

import { useRef, useEffect, useState, useMemo, Suspense } from "react"
import { Canvas, useFrame, useThree } from "@react-three/fiber"
import { OrbitControls, Html } from "@react-three/drei"
import * as THREE from "three"

// ── Types ──────────────────────────────────────────────────────────────────

interface VisemeKeyframe {
  timestamp: number
  duration: number
  viseme: string
  mouth_open: number
  mouth_width: number
  lip_round: number
  jaw_drop: number
}

interface VRMAvatarProps {
  emotion?: string
  isSpeaking?: boolean
  lipSyncValue?: number
  lipsyncKeyframes?: VisemeKeyframe[]
  audioStartTime?: number
  className?: string
}

// ── Emotion → Expression Mapping ───────────────────────────────────────────

const EMOTION_EXPRESSIONS: Record<string, Record<string, number>> = {
  happy:    { smile: 0.8, mouthOpen: 0.1, eyeSquint: 0.3, browUp: 0.6 },
  sad:      { frown: 0.7, mouthOpen: 0, eyeSquint: 0.1, browDown: 0.5 },
  angry:    { frown: 0.5, mouthOpen: 0.15, eyeSquint: 0.4, browDown: 0.8 },
  fear:     { mouthOpen: 0.3, eyeSquint: 0, browUp: 0.8 },
  surprise: { mouthOpen: 0.6, eyeSquint: 0, browUp: 0.9 },
  neutral:  { smile: 0.05, mouthOpen: 0, eyeSquint: 0, browUp: 0.1 },
  disgust:  { frown: 0.3, mouthOpen: 0.1, eyeSquint: 0.5, browDown: 0.6 },
  contempt: { smile: 0.3, mouthOpen: 0, eyeSquint: 0.2, browDown: 0.3 },
}

function lerp(a: number, b: number, speed: number, delta: number): number {
  return a + (b - a) * Math.min(1 - Math.exp(-speed * delta), 1)
}

// ── Fallback Sphere Head (always works, no dependencies) ────────────────────

function SphereHead({ emotion, isSpeaking, lipSyncValue }: {
  emotion: string; isSpeaking: boolean; lipSyncValue: number
}) {
  const headRef = useRef<THREE.Group>(null)
  const leftEyeRef = useRef<THREE.Mesh>(null)
  const rightEyeRef = useRef<THREE.Mesh>(null)
  const mouthRef = useRef<THREE.Mesh>(null)
  const leftBrowRef = useRef<THREE.Mesh>(null)
  const rightBrowRef = useRef<THREE.Mesh>(null)
  const ringRef = useRef<THREE.Mesh>(null)

  const s = useRef({
    smile: 0, mouthOpen: 0, eyeOpen: 1, browUp: 0, browDown: 0,
    idlePhase: 0, blinkTimer: 0, blinkPhase: 0, nextBlink: 3,
  })

  const targetColor = useRef(new THREE.Color("#A2AB73"))

  const EMOTION_COLORS: Record<string, string> = {
    happy: "#D6A44C", sad: "#4169E1", angry: "#FF4444", fear: "#9932CC",
    surprise: "#FF8C00", neutral: "#A2AB73", disgust: "#556B2F", contempt: "#8B4513",
  }

  useEffect(() => {
    targetColor.current.set(EMOTION_COLORS[emotion] || EMOTION_COLORS.neutral)
  }, [emotion])

  useFrame((_, delta) => {
    const v = s.current
    const d = Math.min(delta, 0.1)
    const exp = EMOTION_EXPRESSIONS[emotion] || EMOTION_EXPRESSIONS.neutral

    // Blink
    v.blinkTimer += d
    if (v.blinkTimer >= v.nextBlink && v.blinkPhase === 0) {
      v.blinkPhase = 0.15; v.blinkTimer = 0; v.nextBlink = 2 + Math.random() * 4
    }
    let blinkScale = 1
    if (v.blinkPhase > 0) {
      v.blinkPhase -= d
      if (v.blinkPhase <= 0) { v.blinkPhase = 0; blinkScale = 1 }
      else { const p = 1 - v.blinkPhase / 0.15; blinkScale = p < 0.5 ? 1 - p * 2 : (p - 0.5) * 2 }
    }

    // Idle
    v.idlePhase += d * 0.8
    const idleYaw = Math.sin(v.idlePhase * 0.7) * 0.03
    const idlePitch = Math.sin(v.idlePhase * 0.5) * 0.02

    // Targets
    const tSmile = (exp.smile || 0) + (exp.frown || 0) * -0.5
    const tMouthOpen = isSpeaking ? (lipSyncValue > 0 ? lipSyncValue : 0.4 + Math.sin(Date.now() * 0.01) * 0.3) : (exp.mouthOpen || 0)
    const tBrowUp = exp.browUp || 0
    const tBrowDown = exp.browDown || 0

    v.smile = lerp(v.smile, tSmile, 6, d)
    v.mouthOpen = lerp(v.mouthOpen, tMouthOpen, 12, d)
    v.eyeOpen = lerp(v.eyeOpen, 1 - (exp.eyeSquint || 0) * 0.3, 8, d)
    v.browUp = lerp(v.browUp, tBrowUp, 6, d)
    v.browDown = lerp(v.browDown, tBrowDown, 6, d)

    if (headRef.current) {
      headRef.current.rotation.y = idleYaw
      headRef.current.rotation.x = idlePitch
    }
    if (leftEyeRef.current) leftEyeRef.current.scale.y = v.eyeOpen * blinkScale
    if (rightEyeRef.current) rightEyeRef.current.scale.y = v.eyeOpen * blinkScale
    if (mouthRef.current) {
      mouthRef.current.scale.x = 1 + v.smile * 0.35
      mouthRef.current.scale.y = v.mouthOpen * 0.5 + 0.1
    }
    if (leftBrowRef.current) leftBrowRef.current.position.y = 0.52 + v.browUp * 0.08 - v.browDown * 0.05
    if (rightBrowRef.current) rightBrowRef.current.position.y = 0.52 + v.browUp * 0.08 - v.browDown * 0.05
    if (ringRef.current) {
      const mat = ringRef.current.material as THREE.MeshBasicMaterial
      mat.color.lerp(targetColor.current, d * 3)
      mat.opacity = 0.15 + Math.sin(v.idlePhase * 3) * 0.05
    }
  })

  // Load face texture
  const faceTexture = useMemo(() => {
    const loader = new THREE.TextureLoader()
    const tex = loader.load("/avatar-face.jpg")
    tex.colorSpace = THREE.SRGBColorSpace
    return tex
  }, [])

  const skin = "#F5D0A9"
  return (
    <group ref={headRef}>
      <mesh><sphereGeometry args={[0.55, 48, 48]} /><meshStandardMaterial map={faceTexture} roughness={0.5} metalness={0.05} /></mesh>
      {/* Eyes */}
      <group position={[-0.18, 0.12, 0.48]}>
        <mesh ref={leftEyeRef}><sphereGeometry args={[0.075, 24, 24]} /><meshStandardMaterial color="#F3F4F4" /></mesh>
        <mesh position={[0, 0, 0.04]}><sphereGeometry args={[0.038, 16, 16]} /><meshStandardMaterial color="#5A4A3A" /></mesh>
        <mesh position={[0, 0, 0.06]}><sphereGeometry args={[0.02, 12, 12]} /><meshStandardMaterial color="#201D1D" /></mesh>
        <mesh position={[0.01, 0.01, 0.07]}><sphereGeometry args={[0.006, 8, 8]} /><meshStandardMaterial color="white" emissive="white" emissiveIntensity={0.3} /></mesh>
      </group>
      <group position={[0.18, 0.12, 0.48]}>
        <mesh ref={rightEyeRef}><sphereGeometry args={[0.075, 24, 24]} /><meshStandardMaterial color="#F3F4F4" /></mesh>
        <mesh position={[0, 0, 0.04]}><sphereGeometry args={[0.038, 16, 16]} /><meshStandardMaterial color="#5A4A3A" /></mesh>
        <mesh position={[0, 0, 0.06]}><sphereGeometry args={[0.02, 12, 12]} /><meshStandardMaterial color="#201D1D" /></mesh>
        <mesh position={[0.01, 0.01, 0.07]}><sphereGeometry args={[0.006, 8, 8]} /><meshStandardMaterial color="white" emissive="white" emissiveIntensity={0.3} /></mesh>
      </group>
      {/* Brows */}
      <mesh ref={leftBrowRef} position={[-0.18, 0.52, 0.44]} rotation={[0, 0, 0.15]}>
        <boxGeometry args={[0.14, 0.025, 0.02]} /><meshStandardMaterial color="#3A3535" />
      </mesh>
      <mesh ref={rightBrowRef} position={[0.18, 0.52, 0.44]} rotation={[0, 0, -0.15]}>
        <boxGeometry args={[0.14, 0.025, 0.02]} /><meshStandardMaterial color="#3A3535" />
      </mesh>
      {/* Nose */}
      <mesh position={[0, 0.02, 0.55]}><sphereGeometry args={[0.035, 12, 12]} /><meshStandardMaterial color="#E6D9C4" /></mesh>
      {/* Mouth */}
      <mesh ref={mouthRef} position={[0, -0.14, 0.48]}>
        <boxGeometry args={[0.12, 0.02, 0.015]} /><meshStandardMaterial color="#CC7777" />
      </mesh>
      {/* Ears */}
      <mesh position={[-0.53, 0.05, 0.05]}><sphereGeometry args={[0.06, 12, 12]} /><meshStandardMaterial color="#E6D9C4" /></mesh>
      <mesh position={[0.53, 0.05, 0.05]}><sphereGeometry args={[0.06, 12, 12]} /><meshStandardMaterial color="#E6D9C4" /></mesh>
      {/* Neck */}
      <mesh position={[0, -0.7, 0]}><cylinderGeometry args={[0.12, 0.15, 0.25, 16]} /><meshStandardMaterial color={skin} /></mesh>
      {/* Emotion ring */}
      <mesh ref={ringRef} position={[0, 0, -0.02]}>
        <ringGeometry args={[0.58, 0.62, 48]} />
        <meshBasicMaterial color="#A2AB73" transparent opacity={0.15} side={THREE.DoubleSide} />
      </mesh>
    </group>
  )
}

// ── VRM Model Loader (dynamic import to avoid SSR issues) ──────────────────

function VRMModel({
  emotion, isSpeaking, lipSyncValue, lipsyncKeyframes, audioStartTime,
}: {
  emotion: string; isSpeaking: boolean; lipSyncValue: number
  lipsyncKeyframes: VisemeKeyframe[]; audioStartTime: number
}) {
  const { scene } = useThree()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const vrmRef = useRef<any>(null)

  useEffect(() => {
    let cancelled = false

    async function loadVRM() {
      try {
        // Dynamic imports to avoid SSR issues
        const { GLTFLoader } = await import("three/examples/jsm/loaders/GLTFLoader.js")
        const { VRMLoaderPlugin, VRMUtils } = await import("@pixiv/three-vrm")

        const loader = new GLTFLoader()
        loader.register((parser: any) => new VRMLoaderPlugin(parser))

        loader.load(
          "/models/utsuwa.vrm",
          (gltf: any) => {
            if (cancelled) return
            const vrm = gltf.userData.vrm
            if (!vrm) {
              setError("Failed to parse VRM model")
              setLoading(false)
              return
            }

            try {
              VRMUtils.removeUnnecessaryVertices(gltf.scene)
              VRMUtils.combineSkeletons(gltf.scene)
              VRMUtils.combineMorphs(vrm)
            } catch (e) {
              console.warn("VRM optimization failed:", e)
            }

            vrm.scene.traverse((obj: any) => { obj.frustumCulled = false })
            vrmRef.current = vrm
            scene.add(vrm.scene)
            setLoading(false)
            console.log("VRM model loaded successfully")
          },
          (progress: any) => {
            // Progress callback
          },
          (err: any) => {
            if (cancelled) return
            console.error("VRM load error:", err)
            setError(String(err))
            setLoading(false)
          }
        )
      } catch (e: any) {
        if (cancelled) return
        console.error("VRM import error:", e)
        setError(e.message)
        setLoading(false)
      }
    }

    loadVRM()

    return () => {
      cancelled = true
      if (vrmRef.current) {
        scene.remove(vrmRef.current.scene)
        vrmRef.current = null
      }
    }
  }, [scene])

  // Animation loop
  useFrame((_, delta) => {
    const vrm = vrmRef.current
    if (!vrm || !vrm.expressionManager) return
    const d = Math.min(delta, 0.1)
    const em = vrm.expressionManager

    // Map emotion to VRM expressions
    const exp = EMOTION_EXPRESSIONS[emotion] || EMOTION_EXPRESSIONS.neutral
    em.setValue("happy", lerp(em.getValue("happy") || 0, exp.smile || 0, 6, d))
    em.setValue("angry", lerp(em.getValue("angry") || 0, exp.frown || 0, 6, d))
    em.setValue("sad", lerp(em.getValue("sad") || 0, (exp as any).frown || 0, 6, d))
    em.setValue("relaxed", lerp(em.getValue("relaxed") || 0, 0.2, 6, d))
    em.setValue("surprised", lerp(em.getValue("surprised") || 0, exp.mouthOpen || 0, 6, d))

    // Lip sync
    if (isSpeaking && lipsyncKeyframes.length > 0 && audioStartTime > 0) {
      const elapsed = (performance.now() - audioStartTime) / 1000
      let activeKf: VisemeKeyframe | null = null
      for (const kf of lipsyncKeyframes) {
        if (elapsed >= kf.timestamp && elapsed < kf.timestamp + kf.duration) {
          activeKf = kf; break
        }
      }
      if (activeKf) {
        const open = activeKf.mouth_open * activeKf.jaw_drop * 2
        em.setValue("aa", lerp(em.getValue("aa") || 0, open * 0.8, 14, d))
        em.setValue("ih", lerp(em.getValue("ih") || 0, open * 0.5, 14, d))
        em.setValue("ou", lerp(em.getValue("ou") || 0, open * 0.3, 14, d))
      }
    } else if (isSpeaking) {
      const t = Date.now() * 0.008
      const val = 0.3 + 0.4 * Math.sin(t) * Math.sin(t * 1.7)
      em.setValue("aa", lerp(em.getValue("aa") || 0, val * 0.5, 14, d))
      em.setValue("ih", lerp(em.getValue("ih") || 0, val * 0.3, 14, d))
    } else {
      em.setValue("aa", lerp(em.getValue("aa") || 0, 0, 8, d))
      em.setValue("ih", lerp(em.getValue("ih") || 0, 0, 8, d))
      em.setValue("ou", lerp(em.getValue("ou") || 0, 0, 8, d))
    }

    // Head rotation
    if (vrm.humanoid) {
      const head = vrm.humanoid.getRawBoneNode("head")
      if (head) {
        const t = Date.now() * 0.0008
        head.rotation.y = lerp(head.rotation.y, Math.sin(t * 0.7) * 0.03, 2.5, d)
        head.rotation.x = lerp(head.rotation.x, Math.sin(t * 0.5) * 0.02, 2.5, d)
      }
    }

    vrm.update(d)
  })

  if (loading) {
    return (
      <Html center>
        <div className="text-center text-white/70">
          <div className="animate-spin w-8 h-8 border-2 border-white/30 border-t-white rounded-full mx-auto mb-2" />
          <div className="text-sm">Loading 3D avatar...</div>
          <div className="text-xs text-white/40 mt-1">18MB model</div>
        </div>
      </Html>
    )
  }

  if (error) {
    console.warn("VRM load failed, will use fallback:", error)
    return null // Let the fallback render
  }

  return null
}

// ── Main Export ─────────────────────────────────────────────────────────────

export function VRMAvatar({
  emotion = "neutral",
  isSpeaking = false,
  lipSyncValue = 0,
  lipsyncKeyframes = [],
  audioStartTime = 0,
  className = "",
}: VRMAvatarProps) {
  const [vrmFailed, setVrmFailed] = useState(false)

  return (
    <div className={`w-full h-full ${className}`}>
      <Canvas
        camera={{ position: [0, 0.3, 1.8], fov: 40 }}
        style={{ background: "transparent" }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true }}
        onCreated={() => console.log("Three.js canvas created")}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[2, 3, 5]} intensity={1.2} color="#FFF8F0" />
        <directionalLight position={[-2, 1, 3]} intensity={0.5} color="#E8F0FF" />
        <pointLight position={[0, 0.8, 1.5]} intensity={0.6} color="#FFE8D0" />
        <pointLight position={[0, -0.3, 1]} intensity={0.2} color="#FFE0C0" />

        <Suspense fallback={
          <Html center>
            <div className="text-center text-white/70">
              <div className="animate-spin w-8 h-8 border-2 border-white/30 border-t-white rounded-full mx-auto mb-2" />
              <div className="text-sm">Loading avatar...</div>
            </div>
          </Html>
        }>
          {!vrmFailed && (
            <VRMModel
              emotion={emotion}
              isSpeaking={isSpeaking}
              lipSyncValue={lipSyncValue}
              lipsyncKeyframes={lipsyncKeyframes}
              audioStartTime={audioStartTime}
            />
          )}
          <SphereHead
            emotion={emotion}
            isSpeaking={isSpeaking}
            lipSyncValue={lipSyncValue}
          />
        </Suspense>

        <OrbitControls
          target={[0, 0.2, 0]}
          enableZoom={false}
          enablePan={false}
          minPolarAngle={Math.PI / 4}
          maxPolarAngle={Math.PI / 1.5}
          dampingFactor={0.1}
          enableDamping
        />
      </Canvas>
    </div>
  )
}
