"use client"

import { gsap } from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"
import { useGSAP } from "@gsap/react"

/* GSAP plugins must be registered exactly once, and only in the browser —
 * ScrollTrigger touches `document` at registration time, so importing this
 * module from a server component would throw.
 *
 * Every plugin is free as of GSAP 3.13, including ScrollTrigger. */
if (typeof window !== "undefined") {
  // registerPlugin is idempotent — re-registering the same plugin is a no-op,
  // so this is safe under Fast Refresh and repeated module evaluation.
  gsap.registerPlugin(ScrollTrigger, useGSAP)
}

/**
 * Wraps animation setup so it is skipped for reduced-motion users, with the
 * elements left in their FINAL state rather than their initial one. Skipping
 * a reveal animation without this leaves the page blank at opacity 0 — the
 * single most common reduced-motion bug.
 */
export function withMotionPreference(
  build: () => void,
  settle: () => void = () => {},
): void {
  const mm = gsap.matchMedia()
  mm.add("(prefers-reduced-motion: no-preference)", () => build())
  mm.add("(prefers-reduced-motion: reduce)", () => settle())
}

export { gsap, ScrollTrigger, useGSAP }
