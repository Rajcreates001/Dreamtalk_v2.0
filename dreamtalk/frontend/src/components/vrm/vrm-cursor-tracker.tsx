"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import { Canvas, useFrame, useThree } from "@react-three/fiber"
import * as THREE from "three"
import { cn } from "@/lib/utils"

interface CursorTrackerProps {
  modelUrl: string
  className?: string
  height?: number | string
  overlay?: boolean
}

function VRMCursorScene({ modelUrl, overlay }: { modelUrl: string; overlay: boolean }) {
  const { camera, gl, scene } = useThree()
  const vrmRef = useRef<any>(null)
  const mouseRef = useRef({ x: 0, y: 0 })
  const targetHeadRot = useRef({ yaw: 0, pitch: 0 })
  const currentHeadRot = useRef({ yaw: 0, pitch: 0 })
  const targetEyeRot = useRef({ x: 0, y: 0 })
  const currentEyeRot = useRef({ x: 0, y: 0 })
  const loaded = useRef(false)
  const breathPhase = useRef(0)

  useEffect(() => {
    if (!modelUrl) return
    let mounted = true

    async function loadVRM() {
      try {
        const { GLTFLoader } = await import("three/examples/jsm/loaders/GLTFLoader.js")
        const { VRMLoaderPlugin, VRMUtils } = await import("@pixiv/three-vrm")

        const loader = new GLTFLoader()
        loader.crossOrigin = "anonymous"
        loader.register((parser: any) => new VRMLoaderPlugin(parser))

        loader.load(
          modelUrl,
          (gltf: any) => {
            if (!mounted) return
            const loadedVrm = gltf.userData.vrm

            VRMUtils.removeUnnecessaryVertices(loadedVrm.scene)
            VRMUtils.removeUnnecessaryJoints(loadedVrm.scene)

            loadedVrm.scene.traverse((obj: THREE.Object3D) => {
              obj.frustumCulled = false
            })

            const box = new THREE.Box3().setFromObject(loadedVrm.scene)
            loadedVrm.scene.position.x = -box.getCenter(new THREE.Vector3()).x
            loadedVrm.scene.position.z = -box.getCenter(new THREE.Vector3()).z
            loadedVrm.scene.position.y = -box.min.y

            scene.add(loadedVrm.scene)
            vrmRef.current = loadedVrm
            loaded.current = true
          },
          undefined,
          (error: any) => console.error("VRM load error:", error)
        )
      } catch (err) {
        console.warn("VRM import error:", err)
      }
    }

    loadVRM()
    return () => { mounted = false; if (vrmRef.current) { scene.remove(vrmRef.current.scene); vrmRef.current = null; loaded.current = false } }
  }, [modelUrl])

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current = {
        x: (e.clientX / window.innerWidth) * 2 - 1,
        y: -(e.clientY / window.innerHeight) * 2 + 1,
      }
    }
    window.addEventListener("mousemove", handleMouseMove)
    return () => window.removeEventListener("mousemove", handleMouseMove)
  }, [])

  useFrame((_, delta) => {
    const vrm = vrmRef.current
    if (!vrm || !loaded.current) return

    vrm.update(delta)

    const humanoid = vrm.humanoid
    if (!humanoid) return

    const head = humanoid.getNormalizedBoneNode("head")
    const neck = humanoid.getNormalizedBoneNode("neck")
    const leftEye = humanoid.getNormalizedBoneNode("leftEye")
    const rightEye = humanoid.getNormalizedBoneNode("rightEye")

    const mx = mouseRef.current.x
    const my = mouseRef.current.y

    // Map mouse to head rotation (limited range for natural look)
    targetHeadRot.current.yaw = mx * 0.35
    targetHeadRot.current.pitch = my * 0.2

    // Smooth interpolation for head
    const headLerp = Math.min(1, delta * 6)
    currentHeadRot.current.yaw += (targetHeadRot.current.yaw - currentHeadRot.current.yaw) * headLerp
    currentHeadRot.current.pitch += (targetHeadRot.current.pitch - currentHeadRot.current.pitch) * headLerp

    if (head) {
      head.rotation.y = currentHeadRot.current.yaw
      head.rotation.x = currentHeadRot.current.pitch
    }
    if (neck) {
      neck.rotation.y = currentHeadRot.current.yaw * 0.3
      neck.rotation.x = currentHeadRot.current.pitch * 0.3
    }

    // Eye tracking (faster, wider range for alert look)
    targetEyeRot.current.x = mx * 0.08
    targetEyeRot.current.y = my * 0.06

    const eyeLerp = Math.min(1, delta * 12)
    currentEyeRot.current.x += (targetEyeRot.current.x - currentEyeRot.current.x) * eyeLerp
    currentEyeRot.current.y += (targetEyeRot.current.y - currentEyeRot.current.y) * eyeLerp

    if (leftEye) leftEye.rotation.y = currentEyeRot.current.x
    if (rightEye) rightEye.rotation.y = currentEyeRot.current.x
    if (leftEye) leftEye.rotation.x = currentEyeRot.current.y
    if (rightEye) rightEye.rotation.x = currentEyeRot.current.y

    // Subtle idle breathing
    breathPhase.current += delta * 1.2
    const breathOffset = Math.sin(breathPhase.current) * 0.003
    if (head) head.position.y = breathOffset
  })

  return <color attach="background" args={[overlay ? "#00000000" : "#ffffff"]} />
}

export function VrmCursorTracker({ modelUrl, className, height = 400, overlay = false }: CursorTrackerProps) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => { setMounted(true) }, [])

  if (!mounted) {
    return <div className={cn("flex items-center justify-center bg-muted/20 rounded-2xl", className)} style={{ height }}>
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-primary" />
    </div>
  }

  return (
    <div className={cn("relative overflow-hidden rounded-2xl", className)} style={{ height }}>
      <Canvas
        camera={{ position: [0, 1.2, 3.8], fov: 28, near: 0.1, far: 20 }}
        gl={{ antialias: true, alpha: overlay }}
        style={{ width: "100%", height: "100%" }}
      >
        {!overlay && (
          <>
            <ambientLight intensity={0.6} />
            <hemisphereLight args={[0xea2264, 0xf78d60, 1.2]} position={[0, 50, 0]} />
            <directionalLight position={[-30, 52.5, 30]} intensity={2.5} castShadow color="#EA2264" />
            <pointLight position={[2, 1, 2]} intensity={0.8} color="#F78D60" />
            <pointLight position={[-2, 0.5, -1]} intensity={0.5} color="#640D5F" />
            <mesh rotation-x={-Math.PI / 2} position-y={0} receiveShadow>
              <circleGeometry args={[1.8, 64]} />
              <shadowMaterial opacity={0.12} />
            </mesh>
          </>
        )}
        <VRMCursorScene modelUrl={modelUrl} overlay={overlay} />
      </Canvas>
    </div>
  )
}
