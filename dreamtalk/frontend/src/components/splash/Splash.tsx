"use client"

import { useEffect, useReducer } from "react"
import { AnimatePresence, motion, useReducedMotion } from "motion/react"

const SESSION_KEY = "astra_splash_seen"

/**
 * Cinematic ~1.8s intro: a point becomes an identity, then the wordmark
 * resolves and the whole thing dissolves into the hero. Shows once per
 * session; skippable; collapses to a flash under reduced-motion.
 */
export function Splash() {
  const [done, finish] = useReducer(() => true, false)
  const reduce = useReducedMotion()

  useEffect(() => {
    let seen = false
    try {
      seen = sessionStorage.getItem(SESSION_KEY) === "1"
    } catch {
      /* private mode */
    }
    if (seen) {
      finish()
      return
    }
    const t = setTimeout(finish, reduce ? 350 : 2000)
    return () => clearTimeout(t)
  }, [reduce])

  const close = () => {
    try {
      sessionStorage.setItem(SESSION_KEY, "1")
    } catch {
      /* ignore */
    }
    finish()
  }

  return (
    <AnimatePresence onExitComplete={close}>
      {!done && (
        <motion.div
          key="splash"
          className="fixed inset-0 z-[100] grid place-items-center bg-background"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, filter: "blur(12px)" }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          onAnimationComplete={() => {
            // mark seen as soon as the intro has played
            try { sessionStorage.setItem(SESSION_KEY, "1") } catch { /* ignore */ }
          }}
        >
          {/* ambient */}
          <div className="pointer-events-none absolute inset-0 opacity-60"
            style={{ background: "radial-gradient(60% 50% at 50% 45%, var(--glow-primary), transparent 70%)" }} />

          <div className="relative flex flex-col items-center">
            {/* identity forming: a point → rings */}
            <div className="relative grid h-28 w-28 place-items-center">
              {[0, 1, 2].map((i) => (
                <motion.span
                  key={i}
                  className="absolute rounded-full border border-primary/40"
                  initial={{ width: 6, height: 6, opacity: 0 }}
                  animate={{
                    width: [6, 60 + i * 26],
                    height: [6, 60 + i * 26],
                    opacity: [0, 0.7, 0],
                  }}
                  transition={{ duration: 1.6, delay: 0.1 + i * 0.18, ease: "easeOut", repeat: reduce ? 0 : Infinity, repeatDelay: 0.4 }}
                />
              ))}
              <motion.span
                className="h-3 w-3 rounded-full bg-gradient-to-br from-primary to-secondary"
                initial={{ scale: 0 }}
                animate={{ scale: [0, 1.3, 1] }}
                transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
              />
            </div>

            {/* wordmark */}
            <motion.div
              className="mt-6 text-center"
              initial={{ opacity: 0, y: 10, filter: "blur(8px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              transition={{ duration: 0.7, delay: reduce ? 0 : 0.7, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="font-display text-3xl font-bold tracking-tight text-foreground">
                DREAMTALK
              </div>
              <div className="label-mono mt-1 !text-[11px] !tracking-[0.4em] text-primary">
                ASTRA
              </div>
            </motion.div>
          </div>

          <button
            onClick={close}
            className="absolute bottom-8 right-8 label-mono text-foreground-muted hover:text-foreground transition-colors"
          >
            Skip →
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
