"use client"

import { useEffect, useState, useRef } from "react"
import { useRouter, usePathname } from "next/navigation"
import { motion, AnimatePresence } from "motion/react"
import { AppSidebar } from "@/components/layout/AppSidebar"
import { AppTopbar } from "@/components/layout/AppTopbar"
import { AuroraField } from "@/components/depth"
import { authApi, clearAuth, isAuthRejection } from "@/lib/api"

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
    /* Only a real auth rejection ends the session.
     *
     * This used to clear the token on ANY rejection, so a backend restart,
     * a timeout or a 502 logged the user out and threw away credentials
     * that were still valid — observed live: one ERR_EMPTY_RESPONSE during
     * a deploy bounced an authenticated session back to /login.
     * A transport failure says nothing about whether the token is good. */
    authApi.me().catch((err) => {
      if (isAuthRejection(err)) {
        clearAuth()
        router.push("/login")
      }
    })
  }, [router])

  if (!mounted) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-background">
        <div className="relative">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary via-secondary to-secondary animate-breathe" />
          <div className="absolute inset-0 w-12 h-12 rounded-full bg-primary animate-pulse-glow" />
        </div>
      </div>
    )
  }

  return (
    // No `bg-background` here: <html> already carries the page colour, and an
    // opaque background on this element would paint over the ambient field the
    // glass chrome refracts (block backgrounds paint after -z-10 children).
    <div className="flex h-dvh overflow-hidden">
      <AuroraField intensity={1} />
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
