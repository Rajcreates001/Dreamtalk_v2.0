"use client"

import { useEffect, useReducer } from "react"
import { AnimatePresence, motion, useReducedMotion } from "motion/react"

const SESSION_KEY = "dreamtalk_splash_seen"

/**
 * Lightweight cinematic intro (~2.2s): concentric identity rings form and a
 * wordmark resolves, then it dissolves into the hero. No heavy 3D here — the
 * real digital human lives in the hero — so the splash is instant and smooth.
 * Once per session; skippable; collapses under reduced-motion.
 */
export function Splash() {
  const [done, finish] = useReducer(() => true, false)
  const reduce = useReducedMotion()

  useEffect(() => {
    let seen = false
    try { seen = sessionStorage.getItem(SESSION_KEY) === "1" } catch { /* private */ }
    if (seen) { finish(); return }
    const t = setTimeout(finish, reduce ? 350 : 2200)
    return () => clearTimeout(t)
  }, [reduce])

  const close = () => {
    try { sessionStorage.setItem(SESSION_KEY, "1") } catch { /* ignore */ }
    finish()
  }

  return (
    <AnimatePresence onExitComplete={close}>
      {!done && (
        <motion.div
          key="splash"
          className="fixed inset-0 z-[100] grid place-items-center bg-background overflow-hidden"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, filter: "blur(16px)", scale: 1.04 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          onAnimationComplete={() => { try { sessionStorage.setItem(SESSION_KEY, "1") } catch { /* ignore */ } }}
        >
          <div className="pointer-events-none absolute inset-0 opacity-80"
            style={{ background: "radial-gradient(55% 55% at 50% 45%, var(--glow-primary), transparent 70%)" }} />

          <div className="relative flex flex-col items-center">
            {/* Identity rings forming */}
            <div className="relative grid h-40 w-40 place-items-center">
              {[0, 1, 2, 3].map((i) => (
                <motion.span
                  key={i}
                  className="absolute rounded-full border"
                  style={{ borderColor: i % 2 ? "var(--secondary)" : "var(--primary)" }}
                  initial={{ width: 8, height: 8, opacity: 0 }}
                  animate={{ width: [8, 60 + i * 34], height: [8, 60 + i * 34], opacity: [0, 0.6, 0] }}
                  transition={{ duration: 1.8, delay: 0.1 + i * 0.16, ease: "easeOut", repeat: reduce ? 0 : Infinity, repeatDelay: 0.3 }}
                />
              ))}
              <motion.span
                className="h-4 w-4 rounded-full bg-gradient-to-br from-primary to-secondary"
                initial={{ scale: 0 }} animate={{ scale: [0, 1.4, 1] }}
                transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              />
            </div>

            <motion.div
              className="mt-6 text-center"
              initial={{ opacity: 0, y: 14, filter: "blur(10px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              transition={{ duration: 0.7, delay: reduce ? 0 : 0.7, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="font-display text-4xl font-bold tracking-[0.02em] text-foreground">
                DREAM<span className="text-primary">TALK</span>
              </div>
              <div className="label-mono mt-2 !text-[10px] !tracking-[0.42em]">Digital Humans</div>
            </motion.div>
          </div>

          <button onClick={close} className="absolute bottom-8 right-8 label-mono hover:text-foreground transition-colors">
            Skip →
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
