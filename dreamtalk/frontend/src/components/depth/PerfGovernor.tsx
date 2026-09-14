"use client"

import { useEffect } from "react"

/* ──────────────────────────────────────────────────────────────
   Adaptive performance governor.

   Goal: hold the display's own refresh rate, and give up visual effects only
   when the page genuinely cannot.

   The dominant cost is `backdrop-filter` over a MOVING backdrop: a changing
   backdrop cannot be cached, so every glass surface re-blurs every frame.
   Tier `medium` therefore freezes the ambient field rather than shrinking any
   radius — once the backdrop is static those results become cacheable, which
   buys back more than any blur tweak.

   Why measured rather than guessed: `hardwareConcurrency` says nothing about
   the GPU, and would punish a 4-core desktop with a real card while letting a
   16-core laptop on integrated graphics run at full quality.

   ── Thresholds are RELATIVE, and that is the whole point ──

   This governor previously compared against absolute rates (demote below 90,
   demote again below 70). requestAnimationFrame cannot fire faster than the
   display refreshes, so on an ordinary 60 Hz laptop the best attainable
   reading is ~60 — already under the 70 floor. The governor therefore
   demoted to `low` on its first window on essentially every machine and
   stayed there, permanently disabling backdrop-filter, saturation and grain.
   The glassmorphism was not missing because it was unimplemented; it was
   being switched off by this file, on hardware that was keeping up perfectly.

   Measured while writing this: inside an embedded browser pane the ceiling is
   ~48 Hz, and a completely blank iframe reported the same 20.8 ms frame time
   as the full 3D avatar page — the page was hitting the ceiling exactly, and
   was still being judged a failure.

   So: learn the ceiling from the fastest frame actually observed, then judge
   each window as a fraction of that. A page holding its display's refresh
   rate scores 1.0 whether that display runs at 48, 60, 120 or 144 Hz.
   ────────────────────────────────────────────────────────────── */

/** Below this fraction of the display's own refresh rate, freeze the ambient
 *  field so the backdrop becomes cacheable. */
const MEDIUM_RATIO = 0.85
/** Below this fraction, also drop blur, saturation and grain. */
const LOW_RATIO = 0.65
/** Length of each measurement window. Long enough to ignore one-off hitches. */
const WINDOW_MS = 1500
/** Let first paint, font swap and the 3D scene settle before judging. */
const WARMUP_MS = 1500
/** Frame intervals shorter than this are treated as timer noise, not a real
 *  refresh period — 400 Hz displays do not exist. */
const MIN_PLAUSIBLE_FRAME_MS = 3
/** Until the ceiling is known, assume the most common panel. */
const ASSUMED_HZ = 60
/** Demote only after this many consecutive failing windows, so one stutter
 *  (a route change, a GLB decode) cannot cost the whole session its effects. */
const STRIKES_TO_DEMOTE = 2

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
    let lastFrame = 0
    let stopped = false
    let intervals: number[] = []
    let strikes = 0
    /* Dropped when the tab changes visibility mid-window: resuming a hidden
     * tab emits a catch-up frame whose interval is meaninglessly short. */
    let windowTainted = false
    /* One display refresh period, estimated as the smallest MEDIAN interval
     * any window has produced.
     *
     * Taking a global minimum instead is what a first attempt did, and it is
     * wrong: a single catch-up frame after the tab is revealed reported 6.8 ms
     * and pinned the estimated ceiling at 147 Hz on a 48 Hz surface, after
     * which every honest window looked like a 46% failure. A window's median
     * cannot be moved by one spurious frame. */
    let bestMedianMs = Infinity

    const applyTier = (next: Tier) => {
      if (ORDER.indexOf(next) <= ORDER.indexOf(tier)) return // never ratchet up
      tier = next
      root.dataset.perf = tier
    }

    const tick = (now: number) => {
      if (stopped) return
      if (!windowStart) windowStart = now
      if (lastFrame) {
        const delta = now - lastFrame
        if (delta >= MIN_PLAUSIBLE_FRAME_MS) intervals.push(delta)
      }
      lastFrame = now
      frames++
      const elapsed = now - windowStart

      if (elapsed >= WINDOW_MS) {
        // rAF is throttled in a hidden tab, which looks identical to a slow
        // machine. Discard the window instead of demoting on it.
        if (!document.hidden && !windowTainted && intervals.length > 8) {
          const sorted = [...intervals].sort((a, b) => a - b)
          const median = sorted[Math.floor(sorted.length / 2)]
          if (median < bestMedianMs) bestMedianMs = median

          const fps = (frames / elapsed) * 1000
          const ceiling = Number.isFinite(bestMedianMs) ? 1000 / bestMedianMs : ASSUMED_HZ
          // How much of what this display can actually deliver we are holding.
          const ratio = fps / ceiling

          root.dataset.perfFps = String(Math.round(fps))
          root.dataset.perfCeiling = String(Math.round(ceiling))

          if (ratio < MEDIUM_RATIO) {
            strikes++
            if (strikes >= STRIKES_TO_DEMOTE) {
              applyTier(ratio < LOW_RATIO ? "low" : "medium")
              strikes = 0
            }
          } else {
            strikes = 0
          }
        }
        frames = 0
        windowStart = 0
        intervals = []
        windowTainted = false
        // Once at the lowest tier there is nothing further to give up, so stop
        // burning a rAF callback on measurement for the rest of the session.
        if (tier === "low") return
      }
      raf = requestAnimationFrame(tick)
    }

    /* Revealing a hidden tab emits a catch-up frame and a burst of re-layout.
     * Neither says anything about steady-state performance, so throw the
     * window containing them away rather than scoring it. */
    const onVisibility = () => {
      windowTainted = true
      lastFrame = 0
      if (!document.hidden && !stopped && tier !== "low" && !raf) {
        raf = requestAnimationFrame(tick)
      }
    }
    document.addEventListener("visibilitychange", onVisibility)

    const warmup = window.setTimeout(() => {
      raf = requestAnimationFrame(tick)
    }, WARMUP_MS)

    return () => {
      stopped = true
      document.removeEventListener("visibilitychange", onVisibility)
      window.clearTimeout(warmup)
      cancelAnimationFrame(raf)
    }
  }, [])

  return null
}

export default PerfGovernor
