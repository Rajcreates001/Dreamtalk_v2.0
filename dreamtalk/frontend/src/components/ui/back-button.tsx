"use client"

import { ArrowLeft } from "lucide-react"
import { useRouter } from "next/navigation"
import { cn } from "@/lib/utils"

interface BackButtonProps {
  href?: string
  className?: string
}

export function BackButton({ href, className }: BackButtonProps) {
  const router = useRouter()

  return (
    <button
      type="button"
      onClick={() => (href ? router.push(href) : router.back())}
      className={cn(
        "fixed top-4 left-4 z-50 h-10 w-10 rounded-xl bg-background/80 backdrop-blur-md border border-border/50 flex items-center justify-center shadow-lg hover:bg-muted/30 transition-all",
        className
      )}
      aria-label="Go back"
    >
      <ArrowLeft className="h-4 w-4" />
    </button>
  )
}
