"use client"

import { motion } from "motion/react"

interface WordRevealProps {
  text: string
  className?: string
  delay?: number
  gradient?: boolean
  revealType?: "fade" | "slide" | "blur" | "scale" | "rotate"
}

function WordReveal({ text, className = "", delay = 0, gradient = false, revealType = "slide" }: WordRevealProps) {
  const words = text.split(" ")

  const getVariants = (type: string) => {
    switch (type) {
      case "fade":
        return { initial: { opacity: 0 }, animate: { opacity: 1 } }
      case "slide":
        return { initial: { opacity: 0, y: 40 }, animate: { opacity: 1, y: 0 } }
      case "blur":
        return { initial: { opacity: 0, filter: "blur(8px)" }, animate: { opacity: 1, filter: "blur(0px)" } }
      case "scale":
        return { initial: { opacity: 0, scale: 0.8 }, animate: { opacity: 1, scale: 1 } }
      case "rotate":
        return { initial: { opacity: 0, y: 20, rotateX: -15 }, animate: { opacity: 1, y: 0, rotateX: 0 } }
      default:
        return { initial: { opacity: 0, y: 30 }, animate: { opacity: 1, y: 0 } }
    }
  }

  const variants = getVariants(revealType)

  return (
    <span className={className}>
      {words.map((word, i) => (
        <motion.span
          key={i}
          initial={variants.initial}
          animate={variants.animate}
          transition={{
            duration: 0.6,
            delay: delay + i * 0.06,
            ease: [0.16, 1, 0.3, 1],
          }}
          className="inline-block mr-[0.3em]"
        >
          {gradient ? (
            <span className="bg-gradient-to-r from-[#CC3A63] via-[#A2AB73] to-[#A2AB73] bg-clip-text text-transparent bg-[length:200%_200%] animate-aurora">
              {word}
            </span>
          ) : (
            word
          )}
        </motion.span>
      ))}
    </span>
  )
}

interface CinematicTextProps {
  lines: {
    text: string
    gradient?: boolean
    className?: string
    delay?: number
    revealType?: "fade" | "slide" | "blur" | "scale" | "rotate"
  }[]
}

export function CinematicText({ lines }: CinematicTextProps) {
  const baseDelay = lines[0]?.delay ?? 0.6

  return (
    <div className="space-y-2">
      {lines.map((line, i) => {
        const lineDelay = baseDelay + i * 0.3
        return (
          <div key={i} className="overflow-hidden">
            {line.gradient ? (
              <motion.h1
                initial={{ opacity: 0, y: 60, scale: 0.95, filter: "blur(4px)" }}
                animate={{ opacity: 1, y: 0, scale: 1, filter: "blur(0px)" }}
                transition={{
                  duration: 0.9,
                  delay: lineDelay,
                  ease: [0.16, 1, 0.3, 1],
                }}
                className={line.className}
              >
                <span className="bg-gradient-to-r from-[#CC3A63] via-[#A2AB73] to-[#A2AB73] bg-clip-text text-transparent bg-[length:200%_200%] animate-aurora">
                  {line.text}
                </span>
              </motion.h1>
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{
                  duration: 0.3,
                  delay: lineDelay - 0.1,
                }}
              >
                <WordReveal
                  text={line.text}
                  className={line.className}
                  delay={lineDelay}
                  revealType={line.revealType || "slide"}
                />
              </motion.div>
            )}
          </div>
        )
      })}
    </div>
  )
}
