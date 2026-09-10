"use client"

import { Canvas } from "@react-three/fiber"
import { Preload, AdaptiveDpr, PerformanceMonitor } from "@react-three/drei"
import { Suspense, useRef, useEffect, useState, type ReactNode } from "react"

interface SceneCanvasProps {
  children: ReactNode
  className?: string
  cameraPosition?: [number, number, number]
  cameraFov?: number
  priority?: boolean
}

/**
 * SceneCanvas — renders a Three.js canvas with automatic pause/resume.
 *
 * PERFORMANCE:
 * 1. DEFERRED MOUNT: Canvas starts invisible. After first paint (via
 *    requestIdleCallback or a 1.5s fallback timeout), it becomes visible.
 *    This prevents Three.js (~500KB bundle + shader compilation + WebGL init)
 *    from blocking the main thread during the critical first paint.
 *
 * 2. VISIBILITY GATE: IntersectionObserver unmounts Canvas (via key toggle)
 *    when the hero section scrolls out of view. This disposes all WebGL
 *    resources and stops all useFrame loops. GPU usage drops to ~0%.
 */
export function SceneCanvas({
  children,
  className = "fixed inset-0 -z-10",
  cameraPosition = [0, 0, 8],
  cameraFov = 75,
}: SceneCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)
  const [intersecting, setIntersecting] = useState(true)
  const [pref, setPref] = useState<"low" | "medium" | "high">("medium")

  // Defer Three.js mount until after first paint (non-blocking)
  useEffect(() => {
    const idleCallback = window.requestIdleCallback || ((cb: IdleRequestCallback) => setTimeout(cb, 1))
    const id = idleCallback(() => {
      setVisible(true)
    }, { timeout: 1500 })

    // Fallback: if requestIdleCallback never fires, show after 1.5s anyway
    const fallback = setTimeout(() => setVisible(true), 800)

    return () => {
      if (typeof window.cancelIdleCallback === "function") {
        window.cancelIdleCallback(id as any)
      } else {
        clearTimeout(id as any)
      }
      clearTimeout(fallback)
    }
  }, [])

  // Visibility gate: pause Canvas when hero is out of viewport
  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIntersecting(entry.isIntersecting || entry.intersectionRatio > 0)
      },
      { threshold: [0, 0.1] }
    )

    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const showCanvas = visible && intersecting

  return (
    <div ref={containerRef} className={className}>
      {showCanvas && (
        <Canvas
          key={showCanvas ? "visible" : "hidden"}
          camera={{ position: cameraPosition, fov: cameraFov }}
          gl={{
            antialias: pref !== "low",
            alpha: true,
            powerPreference: "high-performance",
          }}
          dpr={pref === "low" ? 0.8 : pref === "medium" ? 1.2 : Math.min(window.devicePixelRatio, 2)}
        >
          <Suspense fallback={null}>
            <PerformanceMonitor
              onDecline={() => setPref("low")}
              onChange={() => setPref("medium")}
              onFallback={() => setPref("low")}
              flipflops={3}
              factor={0.8}
            />
            <AdaptiveDpr pixelated />
            {children}
            <Preload all />
          </Suspense>
        </Canvas>
      )}
    </div>
  )
}
