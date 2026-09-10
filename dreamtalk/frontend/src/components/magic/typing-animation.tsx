"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { motion, useInView } from "motion/react"
import { cn } from "@/lib/utils"

interface TypingAnimationProps {
  children?: string
  words?: string[]
  className?: string
  duration?: number
  delay?: number
  pauseDelay?: number
  loop?: boolean
  startOnView?: boolean
  showCursor?: boolean
  blinkCursor?: boolean
}

export function TypingAnimation({
  children,
  words,
  className,
  duration = 100,
  delay = 0,
  pauseDelay = 1000,
  loop = false,
  startOnView = true,
  showCursor = true,
  blinkCursor = true,
}: TypingAnimationProps) {
  const [displayedText, setDisplayedText] = useState("")
  const [currentWordIndex, setCurrentWordIndex] = useState(0)
  const [currentCharIndex, setCurrentCharIndex] = useState(0)
  const [phase, setPhase] = useState<"typing" | "pause" | "deleting">("typing")
  const elementRef = useRef<HTMLSpanElement>(null)
  const isInView = useInView(elementRef, { amount: 0.3, once: true })

  const wordsToAnimate = useMemo(
    () => words ?? (children ? [children] : []),
    [words, children]
  )
  const hasMultipleWords = wordsToAnimate.length > 1
  const shouldStart = startOnView ? isInView : true
  const animationSourceKey = useMemo(
    () => (words ? words.join("\u0000") : (children ?? "")),
    [words, children]
  )

  useEffect(() => {
    setDisplayedText("")
    setCurrentWordIndex(0)
    setCurrentCharIndex(0)
    setPhase("typing")
  }, [animationSourceKey])

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout> | null = null

    if (shouldStart && wordsToAnimate.length > 0) {
      const timeoutDelay =
        delay > 0 && displayedText === ""
          ? delay
          : phase === "typing" ? duration
          : phase === "deleting" ? duration / 2
          : pauseDelay

      timeout = setTimeout(() => {
        const currentWord = wordsToAnimate[currentWordIndex] || ""
        const graphemes = Array.from(currentWord)

        switch (phase) {
          case "typing":
            if (currentCharIndex < graphemes.length) {
              setDisplayedText(graphemes.slice(0, currentCharIndex + 1).join(""))
              setCurrentCharIndex(currentCharIndex + 1)
            } else if (hasMultipleWords || loop) {
              const isLastWord = currentWordIndex === wordsToAnimate.length - 1
              if (!isLastWord || loop) setPhase("pause")
            }
            break
          case "pause":
            setPhase("deleting")
            break
          case "deleting":
            if (currentCharIndex > 0) {
              setDisplayedText(graphemes.slice(0, currentCharIndex - 1).join(""))
              setCurrentCharIndex(currentCharIndex - 1)
            } else {
              setCurrentWordIndex((currentWordIndex + 1) % wordsToAnimate.length)
              setPhase("typing")
            }
            break
        }
      }, timeoutDelay)
    }

    return () => { if (timeout) clearTimeout(timeout) }
  }, [shouldStart, phase, currentCharIndex, currentWordIndex, displayedText, wordsToAnimate, hasMultipleWords, loop, duration, pauseDelay, delay])

  const currentWordGraphemes = Array.from(wordsToAnimate[currentWordIndex] || "")
  const isComplete = !loop && currentWordIndex === wordsToAnimate.length - 1 && currentCharIndex >= currentWordGraphemes.length && phase !== "deleting"
  const shouldShowCursor = showCursor && !isComplete && (hasMultipleWords || loop || currentCharIndex < currentWordGraphemes.length)

  return (
    <motion.span
      ref={elementRef}
      className={cn("inline-block", className)}
    >
      {displayedText}
      {shouldShowCursor && (
        <span className={cn("inline-block animate-pulse", blinkCursor && "opacity-100")}>|</span>
      )}
    </motion.span>
  )
}
