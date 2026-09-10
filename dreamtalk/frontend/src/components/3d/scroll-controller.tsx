"use client"

import { useEffect, useRef, type ReactNode } from "react"
import { motion, useScroll, useTransform } from "motion/react"
import { cn } from "@/lib/utils"

interface ScrollSectionProps {
  children: ReactNode
  className?: string
  parallaxSpeed?: number
  id?: string
}

export function ScrollSection({ children, className, parallaxSpeed = 0.3, id }: ScrollSectionProps) {
  const ref = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  })

  const y = useTransform(scrollYProgress, [0, 1], [parallaxSpeed * 60, parallaxSpeed * -60])
  const opacity = useTransform(scrollYProgress, [0, 0.15, 0.85, 1], [0.6, 1, 1, 0.6])

  return (
    <motion.section
      ref={ref}
      id={id}
      style={{ y, opacity }}
      className={cn("relative w-full", className)}
    >
      {children}
    </motion.section>
  )
}

export function useScrollCamera() {
  const scrollY = useRef(0)

  useEffect(() => {
    const handleScroll = () => {
      scrollY.current = window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)
    }
    window.addEventListener("scroll", handleScroll, { passive: true })
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  return scrollY
}
