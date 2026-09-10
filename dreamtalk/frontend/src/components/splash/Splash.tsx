"use client"

import { useEffect, useReducer } from "react"
import { AnimatePresence, motion, useReducedMotion } from "motion/react"
import { AvatarStage } from "@/components/avatar3d/AvatarStage"

const SESSION_KEY = "dreamtalk_splash_seen"

/**
 * Cinematic ~2.4s intro: a 3D digital human awakens, the wordmark resolves,
 * then the whole scene dissolves into the hero. Once per session; skippable;
 * collapses to a brief flash under reduced-motion.
 */
export function Splash() {
  const [done, finish] = useReducer(() => true, false)
  const reduce = useReducedMotion()

  useEffect(() => {
    let seen = false
    try { seen = sessionStorage.getItem(SESSION_KEY) === "1" } catch { /* private mode */ }
    if (seen) { finish(); return }
    const t = setTimeout(finish, reduce ? 400 : 2400)
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
          exit={{ opacity: 0, filter: "blur(14px)" }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          onAnimationComplete={() => { try { sessionStorage.setItem(SESSION_KEY, "1") } catch { /* ignore */ } }}
        >
          {/* ambient bloom */}
          <div className="pointer-events-none absolute inset-0 opacity-70"
            style={{ background: "radial-gradient(55% 55% at 50% 42%, var(--glow-primary), transparent 70%)" }} />

          <div className="relative flex flex-col items-center">
            {/* 3D digital human awakening */}
            <motion.div
              className="h-[300px] w-[300px] sm:h-[360px] sm:w-[360px]"
              initial={{ opacity: 0, scale: 0.6, filter: "blur(10px)" }}
              animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
              transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1] }}
            >
              <AvatarStage className="h-full w-full" autoSpeak={false} interactive={false} />
            </motion.div>

            {/* wordmark */}
            <motion.div
              className="mt-2 text-center"
              initial={{ opacity: 0, y: 12, filter: "blur(8px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              transition={{ duration: 0.7, delay: reduce ? 0 : 0.9, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="font-display text-3xl font-bold tracking-[0.02em] text-foreground">
                DREAM<span className="text-primary">TALK</span>
              </div>
              <div className="label-mono mt-1 !text-[10px] !tracking-[0.42em]">
                Digital Humans
              </div>
            </motion.div>
          </div>

          <button onClick={close}
            className="absolute bottom-8 right-8 label-mono hover:text-foreground transition-colors">
            Skip →
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
