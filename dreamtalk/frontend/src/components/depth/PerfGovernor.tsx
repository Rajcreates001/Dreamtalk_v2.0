"use client"

import { useEffect } from "react"

/* ──────────────────────────────────────────────────────────────
   Adaptive performance governor.

   Target: >100 FPS idle, >=80 FPS under load (fast scrolling, route changes,
   avatar mounts). Those are high bars for a page carrying a WebGL head, so the
   strategy is to spend the frame budget only while there is budget to spend.

   The dominant cost is `backdrop-filter` over a MOVING backdrop: a changing
   backdrop cannot be cached, so every glass surface re-blurs every frame.
   Tier `medium` therefore freezes the ambient field rather than shrinking any
   radius — once the backdrop is static those results become cacheable, which
   buys back more than any blur tweak.

   Why measured rather than guessed: `hardwareConcurrency` says nothing about
   the GPU, and would punish a 4-core desktop with a real card while letting a
   16-core laptop on integrated graphics run at full quality.

   Sampling is CONTINUOUS, not one-shot. A single sample at load cannot see the
   stress cases the user actually feels — flinging the scrollbar, navigating,
   mounting a second avatar. Each window that misses the target ratchets the
   tier down one step.

   The tier only ever ratchets DOWN. Oscillating between tiers mid-scroll would
   be far more distracting than simply running at the lower one, and each
   transition itself costs a style recalc across the page.
   ────────────────────────────────────────────────────────────── */

/** Sustained FPS below this drops ambient animation (backdrop becomes cacheable). */
const MEDIUM_FPS = 90
/** Sustained FPS below this also drops blur, saturation and grain. */
const LOW_FPS = 70
/** Length of each measurement window. Long enough to ignore one-off hitches. */
const WINDOW_MS = 1500
/** Let first paint, font swap and the 3D scene settle before judging. */
const WARMUP_MS = 1500

type Tier = "high" | "medium" | "low"
const ORDER: Tier[] = ["high", "medium", "low"]

export function PerfGovernor() {
  useEffect(() => {
    const root = document.documentElement
    root.dataset.perf = "high"

    // Reduced motion already freezes the ambient field, so the expensive
    // moving-backdrop case cannot arise. Leave quality high and don't measure.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return

    let tier: Tier = "high"
    let raf = 0
    let frames = 0
    let windowStart = 0
    let stopped = false

    const applyTier = (next: Tier) => {
      if (ORDER.indexOf(next) <= ORDER.indexOf(tier)) return // never ratchet up
      tier = next
      root.dataset.perf = tier
    }

    const tick = (now: number) => {
      if (stopped) return
      if (!windowStart) windowStart = now
      frames++
      const elapsed = now - windowStart

      if (elapsed >= WINDOW_MS) {
        // rAF is throttled in a hidden tab, which looks identical to a slow
        // machine. Discard the window instead of demoting on it.
        if (!document.hidden) {
          const fps = (frames / elapsed) * 1000
          root.dataset.perfFps = String(Math.round(fps))
          if (fps < LOW_FPS) applyTier("low")
          else if (fps < MEDIUM_FPS) applyTier("medium")
        }
        frames = 0
        windowStart = 0
        // Once at the lowest tier there is nothing further to give up, so stop
        // burning a rAF callback on measurement for the rest of the session.
        if (tier === "low") return
      }
      raf = requestAnimationFrame(tick)
    }

    const warmup = window.setTimeout(() => {
      raf = requestAnimationFrame(tick)
    }, WARMUP_MS)

    return () => {
      stopped = true
      window.clearTimeout(warmup)
      cancelAnimationFrame(raf)
    }
  }, [])

  return null
}

export default PerfGovernor
