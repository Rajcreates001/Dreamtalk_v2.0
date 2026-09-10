"use client"

import React, { useRef, useEffect, useState, useCallback } from "react"
import { Canvas, useFrame, useThree } from "@react-three/fiber"
import { OrbitControls, ContactShadows, Environment } from "@react-three/drei"
import * as THREE from "three"
import { cn } from "@/lib/utils"

interface AvatarViewer3DProps {
  modelUrl?: string | null
  className?: string
  height?: number | string
  autoRotate?: boolean
  autoRotateSpeed?: number
  showControls?: boolean
  backgroundColor?: string
  fallbackType?: "head" | "bust" | "sphere"
  onLoad?: () => void
  onError?: (error: string) => void
}

function FallbackHead({ type = "head" }: { type: "head" | "bust" | "sphere" }) {
  const meshRef = useRef<THREE.Group>(null)
  const [hovered, setHovered] = useState(false)

  useFrame((_, delta) => {
    if (meshRef.current && !hovered) {
      meshRef.current.rotation.y += delta * 0.3
    }
  })

  const headColor = new THREE.Color("#7C5CFF")
  const darkHeadColor = new THREE.Color("#6366f1")

  if (type === "sphere") {
    return (
      <group ref={meshRef}>
        <mesh
          onPointerEnter={() => setHovered(true)}
          onPointerLeave={() => setHovered(false)}
        >
          <sphereGeometry args={[0.8, 48, 48]} />
          <meshPhysicalMaterial
            color={headColor}
            metalness={0.1}
            roughness={0.3}
            clearcoat={0.1}
            envMapIntensity={0.5}
          />
        </mesh>
      </group>
    )
  }

  return (
    <group ref={meshRef}>
      {/* Head - elongated sphere */}
      <mesh
        onPointerEnter={() => setHovered(true)}
        onPointerLeave={() => setHovered(false)}
      >
        <sphereGeometry args={[0.7, 48, 48]} />
        <meshPhysicalMaterial
          color={headColor}
          metalness={0.05}
          roughness={0.4}
          clearcoat={0.05}
        />
      </mesh>

      {/* Neck */}
      <mesh position={[0, -0.75, 0]}>
        <cylinderGeometry args={[0.35, 0.4, 0.3, 16]} />
        <meshPhysicalMaterial
          color={darkHeadColor}
          metalness={0.05}
          roughness={0.5}
        />
      </mesh>

      {/* Facial features - subtle */}
      {/* Eyes */}
      <group position={[-0.25, 0.1, 0.65]}>
        <mesh>
          <sphereGeometry args={[0.08, 16, 16]} />
          <meshPhysicalMaterial color="#1a1a2e" roughness={0.1} metalness={0} />
        </mesh>
      </group>
      <group position={[0.25, 0.1, 0.65]}>
        <mesh>
          <sphereGeometry args={[0.08, 16, 16]} />
          <meshPhysicalMaterial color="#1a1a2e" roughness={0.1} metalness={0} />
        </mesh>
      </group>

      {/* Nose bump */}
      <mesh position={[0, -0.02, 0.72]}>
        <sphereGeometry args={[0.04, 8, 8]} />
        <meshPhysicalMaterial color={headColor} roughness={0.5} />
      </mesh>

      {/* Mouth line */}
      <mesh position={[0, -0.22, 0.71]}>
        <boxGeometry args={[0.2, 0.02, 0.02]} />
        <meshPhysicalMaterial color="#4a3f5c" roughness={0.5} />
      </mesh>
    </group>
  )
}

function ObjModel({ url, onLoad, onError }: { url: string; onLoad?: () => void; onError?: (error: string) => void }) {
  const { scene } = useThree()
  const groupRef = useRef<THREE.Group>(new THREE.Group())
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    let mounted = true
    let objGroup: THREE.Group | null = null

    async function loadObj() {
      try {
        // Dynamic import of loaders
        const [{ OBJLoader }, { MTLLoader }] = await Promise.all([
          import("three/examples/jsm/loaders/OBJLoader.js"),
          import("three/examples/jsm/loaders/MTLLoader.js"),
        ])

        const objLoader = new OBJLoader()

        // Derive MTL URL from OBJ URL (replace .obj with .mtl)
        const mtlUrl = url.replace(/\.obj$/i, ".mtl")

        // Try loading the MTL — fall back gracefully if it fails
        try {
          const mtlLoader = new MTLLoader()
          const materials = await mtlLoader.loadAsync(mtlUrl)
          materials.preload()
          objLoader.setMaterials(materials)
        } catch {
          // MTL not available — OBJLoader will use defaults
          console.log("MTL not found, using OBJ materials or fallback")
        }

        objLoader.load(
          url,
          (obj) => {
            if (!mounted) return
            objGroup = obj

            // Center and scale the model
            const box = new THREE.Box3().setFromObject(obj)
            const center = box.getCenter(new THREE.Vector3())
            const size = box.getSize(new THREE.Vector3())
            const maxDim = Math.max(size.x, size.y, size.z)
            const scale = maxDim > 0 ? 1.2 / maxDim : 1
            obj.scale.set(scale, scale, scale)
            obj.position.set(-center.x * scale, -center.y * scale, -center.z * scale)

            obj.traverse((child) => {
              if (child instanceof THREE.Mesh) {
                child.castShadow = true
                child.receiveShadow = true
                // Only apply fallback material if no material was loaded (from MTL or OBJ)
                if (!child.material) {
                  child.material = new THREE.MeshPhysicalMaterial({
                    color: "#7C5CFF",
                    metalness: 0.05,
                    roughness: 0.4,
                  })
                }
              }
            })

            groupRef.current.add(obj)
            scene.add(groupRef.current)
            setLoaded(true)
            onLoad?.()
          },
          undefined,
          (err) => {
            console.error("OBJ load error:", err)
            onError?.("Failed to load 3D model")
          }
        )
      } catch (err) {
        console.error("OBJ loader import error:", err)
        onError?.("3D model loader not available")
      }
    }

    loadObj()

    return () => {
      mounted = false
      if (objGroup) {
        scene.remove(objGroup)
      }
    }
  }, [url, scene, onLoad, onError])

  return null
}

function SceneContent({
  modelUrl,
  autoRotate,
  autoRotateSpeed,
  fallbackType,
  onLoad,
  onError,
}: {
  modelUrl?: string | null
  autoRotate?: boolean
  autoRotateSpeed?: number
  fallbackType: "head" | "bust" | "sphere"
  onLoad?: () => void
  onError?: (error: string) => void
}) {
  const controlsRef = useRef<any>(null)
  const [modelLoaded, setModelLoaded] = useState(false)

  const hasModel = modelUrl && modelUrl.length > 0

  const handleModelLoad = useCallback(() => {
    setModelLoaded(true)
    onLoad?.()
  }, [onLoad])

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.6} />
      <hemisphereLight args={[0x7c5cff, 0x00e5ff, 0.8]} position={[0, 5, 0]} />
      <directionalLight
        position={[5, 8, 5]}
        intensity={1.5}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
      />
      <directionalLight position={[-5, 3, -5]} intensity={0.5} />
      <pointLight position={[0, -3, 0]} intensity={0.3} />

      {/* Environment */}
      <Environment preset="city" />

      {/* Contact shadow */}
      <ContactShadows
        position={[0, -1.2, 0]}
        opacity={0.4}
        scale={4}
        blur={2.5}
        far={2}
      />

      {/* Show fallback 3D head while loading or when no model URL */}
      {(!hasModel || !modelLoaded) && (
        <FallbackHead type={fallbackType} />
      )}

      {/* Single ObjModel instance - only rendered when modelUrl is provided */}
      {hasModel && (
        <ObjModel url={modelUrl} onLoad={handleModelLoad} onError={onError} />
      )}

      {/* Orbit controls for 360° rotation */}
      <OrbitControls
        ref={controlsRef}
        enableDamping
        dampingFactor={0.08}
        minDistance={1.2}
        maxDistance={6}
        minPolarAngle={0.2}
        maxPolarAngle={Math.PI - 0.2}
        autoRotate={autoRotate}
        autoRotateSpeed={autoRotateSpeed ?? 2.0}
        enablePan={false}
        rotateSpeed={0.8}
      />
    </>
  )
}

export function AvatarViewer3D({
  modelUrl,
  className,
  height = 400,
  autoRotate = true,
  autoRotateSpeed = 2.0,
  showControls = true,
  backgroundColor = "transparent",
  fallbackType = "head",
  onLoad,
  onError,
}: AvatarViewer3DProps) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const heightStr = typeof height === "number" ? `${height}px` : height

  if (!mounted) {
    return (
      <div
        className={cn("flex items-center justify-center bg-[#0F172A]/40 rounded-2xl", className)}
        style={{ height: heightStr }}
      >
        <div className="flex flex-col items-center gap-2">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#7C5CFF]/30 border-t-[#7C5CFF]" />
          <span className="text-xs text-[#64748B]">Initializing 3D viewer...</span>
        </div>
      </div>
    )
  }

  return (
    <div
      className={cn("relative rounded-2xl overflow-hidden", className)}
      style={{ height: heightStr }}
    >
      {/* Gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#7C5CFF]/5 via-transparent to-[#00E5FF]/5 pointer-events-none" />

      {/* Grid pattern overlay */}
      <div
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23fff' fill-opacity='0.15'%3E%3Cpath d='M40 0H0v40h40V0z'/%3E%3C/g%3E%3C/svg%3E")`,
        }}
      />

      <Canvas
        camera={{ position: [0, 0.8, 3.5], fov: 35, near: 0.1, far: 10 }}
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: "high-performance",
          preserveDrawingBuffer: true,
        }}
        dpr={[1, 1.5]}
        style={{ width: "100%", height: "100%", background: backgroundColor }}
      >
        <SceneContent
          modelUrl={modelUrl}
          autoRotate={autoRotate}
          autoRotateSpeed={autoRotateSpeed}
          fallbackType={fallbackType}
          onLoad={onLoad}
          onError={onError}
        />
      </Canvas>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-[#070B14]/80 to-transparent pointer-events-none" />

      {/* Controls hint */}
      {showControls && (
        <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-black/40 backdrop-blur-sm border border-white/[0.06] pointer-events-none">
          <svg className="w-3 h-3 text-[#94A3B8]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
          </svg>
          <span className="text-[10px] text-[#94A3B8] font-medium">
            Drag to rotate &bull; Scroll to zoom
          </span>
        </div>
      )}

      {/* Rotation indicator */}
      <div className="absolute top-3 right-3 flex items-center gap-1.5 px-2 py-1 rounded-full bg-black/30 backdrop-blur-sm border border-white/[0.06] pointer-events-none">
        <div className="w-1.5 h-1.5 rounded-full bg-[#42FFC6]" />
        <span className="text-[10px] text-[#CBD5E1] font-medium">360°</span>
      </div>
    </div>
  )
}

export default AvatarViewer3D
