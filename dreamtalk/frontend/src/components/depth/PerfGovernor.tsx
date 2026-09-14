"use client"

import { useEffect } from "react"

/* ──────────────────────────────────────────────────────────────
   Adaptive performance tiers.

   The expensive thing in this design is not the blur radius — it is that
   `backdrop-filter` cannot be cached while the backdrop is MOVING. With an
   animated ambient field behind them, every glass surface on screen re-blurs
   the backdrop every single frame. Ten glass panels on a weak integrated GPU
   is ten full-viewport blur passes per frame, and the frame budget is gone.

   So rather than guess from `hardwareConcurrency` (which says nothing about
   the GPU, and on which a 4-core desktop with a real card would be punished
   for no reason), this measures actual delivered frame time and steps DOWN
   only when the machine demonstrably cannot keep up.

   Tiers, written to `data-perf` on <html>:
     high    everything on
     medium  ambient animation frozen — the backdrop becomes static, so every
             backdrop-filter result becomes cacheable. This is the single
             biggest win and is close to invisible, because the drift was
             already slow enough to be subliminal.
     low     blur radii cut and grain dropped; glass degrades to a flat
             translucent fill. Still looks deliberate, just cheaper.

   The tier only ever ratchets downward within a session. Oscillating between
   tiers would be far more distracting than simply running at the lower one.
   ────────────────────────────────────────────────────────────── */

const SAMPLE_MS = 2200
/** Below this we stop animating the backdrop; below LOW we also cut blur. */
const MEDIUM_FPS = 52
const LOW_FPS = 38

export function PerfGovernor() {
  useEffect(() => {
    const root = document.documentElement
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      // Reduced motion already freezes the ambient field, so the backdrop is
      // static and the expensive case cannot arise. Leave quality high.
      root.dataset.perf = "high"
      return
    }
    root.dataset.perf = "high"

    let frames = 0
    let raf = 0
    let start = 0
    let stopped = false

    const tick = (now: number) => {
      if (stopped) return
      if (!start) start = now
      frames++
      const elapsed = now - start
      if (elapsed >= SAMPLE_MS) {
        const fps = (frames / elapsed) * 1000
        // A tab that was backgrounded mid-sample reports a nonsense low number;
        // rAF is throttled there, so discard and re-sample instead of demoting.
        if (document.hidden) {
          frames = 0
          start = 0
        } else {
          root.dataset.perf = fps < LOW_FPS ? "low" : fps < MEDIUM_FPS ? "medium" : "high"
          root.dataset.perfFps = String(Math.round(fps))
          return // ratchet down once, then stop measuring
        }
      }
      raf = requestAnimationFrame(tick)
    }

    // Let first paint, font swap and the 3D scene settle before judging.
    const warmup = window.setTimeout(() => {
      raf = requestAnimationFrame(tick)
    }, 1200)

    return () => {
      stopped = true
      window.clearTimeout(warmup)
      cancelAnimationFrame(raf)
    }
  }, [])

  return null
}

export default PerfGovernor
