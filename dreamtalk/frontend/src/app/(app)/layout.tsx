"use client"

import { useEffect, useState, useRef } from "react"
import { useRouter, usePathname } from "next/navigation"
import { motion, AnimatePresence } from "motion/react"
import { AppSidebar } from "@/components/layout/AppSidebar"
import { AppTopbar } from "@/components/layout/AppTopbar"
import { authApi, clearAuth } from "@/lib/api"

// ─── Page transition variants ───
const pageVariants = {
  initial: { opacity: 0, y: 12, filter: "blur(4px)" },
  animate: { opacity: 1, y: 0, filter: "blur(0px)" },
  exit: { opacity: 0, y: -8, filter: "blur(2px)" },
}

const pageTransition = {
  duration: 0.35,
  ease: [0.25, 0.1, 0.25, 1] as const,
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [mounted, setMounted] = useState(false)
  const [sidebarMobileOpen, setSidebarMobileOpen] = useState(false)

  useEffect(() => {
    setMounted(true)
    // Check auth on mount
    authApi.me().catch(() => {
      clearAuth()
      router.push("/login")
    })
  }, [router])

  if (!mounted) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-[#070B14]">
        <div className="relative">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[#7C5CFF] via-[#00E5FF] to-[#42FFC6] animate-breathe" />
          <div className="absolute inset-0 w-12 h-12 rounded-full bg-[#7C5CFF] animate-pulse-glow" />
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-dvh bg-[#070B14] overflow-hidden">
      {/* Mobile sidebar backdrop */}
      {sidebarMobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarMobileOpen(false)}
        />
      )}

      {/* Mobile sidebar */}
      {sidebarMobileOpen && (
        <div className="fixed inset-y-0 left-0 z-50 w-[260px] lg:hidden">
          <AppSidebar />
        </div>
      )}

      {/* Desktop sidebar */}
      <div className="hidden lg:flex">
        <AppSidebar />
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        <AppTopbar onToggleSidebar={() => setSidebarMobileOpen(!sidebarMobileOpen)} />
        <main className="flex-1 overflow-y-auto p-6 lg:p-8 relative">
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={pageTransition}
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
