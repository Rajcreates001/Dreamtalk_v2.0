"use client"

import { usePathname, useRouter } from "next/navigation"
import Link from "next/link"
import { motion, AnimatePresence } from "motion/react"
import { cn } from "@/lib/utils"
import {
  ChevronLeft,
  ChevronRight,
  LogOut,
  Plus,
  Sparkles,
  Monitor,
  Mic,
  Brain,
  Headphones,
  Camera,
  Puzzle,
  Sliders,
} from "lucide-react"
import { useState, useEffect } from "react"
import { authApi, clearAuth, digitalTwinApi } from "@/lib/api"

const MODULES = [
  { href: "/live", label: "Live Digital Human", icon: Monitor, color: "#CC3A63" },
  { href: "/voice-cloning", label: "Voice Cloning", icon: Mic, color: "#CC3A63" },
  { href: "/digital-brain", label: "Digital Brain", icon: Brain, color: "#A2AB73" },
  { href: "/voice-chat", label: "Voice Chat", icon: Headphones, color: "#A2AB73" },
  { href: "/avatar-studio", label: "Avatar Studio", icon: Camera, color: "#D6A44C" },
  { href: "/builder", label: "Complete Builder", icon: Puzzle, color: "#B03A5E" },
  { href: "/brain-manager", label: "Brain Management", icon: Sliders, color: "#D84C63" },
]

export function AppSidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const [collapsed, setCollapsed] = useState(false)
  const [user, setUser] = useState<{ full_name?: string; role?: string } | null>(null)
  const [digitalHumans, setDigitalHumans] = useState<Array<{ id: string; name: string; initials: string; color: string; href: string }>>([])
  const [dhLoading, setDhLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem("user")
    if (stored) {
      try { setUser(JSON.parse(stored)) } catch {}
    }

    async function loadDhs() {
      try {
        const twins = await digitalTwinApi.list()
        if (twins && twins.length > 0) {
          const colors = ["#CC3A63", "#A2AB73", "#A2AB73", "#CC3A63", "#D6A44C", "#B03A5E", "#D84C63"]
          const mapped = twins.map((twin: any, i: number) => {
            const name = twin.name || twin.digital_twin_name || "Digital Human"
            const id = twin.id || twin._id || twin.twin_id
            const words = name.split(" ")
            const initials = words.length >= 2 ? words[0][0] + words[1][0] : name.slice(0, 2)
            return { id, name, initials: initials.toUpperCase(), color: colors[i % colors.length], href: `/dh/${id}` }
          })
          setDigitalHumans(mapped)
        }
      } catch {}
      setDhLoading(false)
    }
    loadDhs()
  }, [])

  const handleLogout = () => {
    authApi.logout().catch(() => {})
    clearAuth()
    router.push("/login")
  }

  const isActive = (href: string) => {
    if (href === "/live") return pathname === "/live"
    return pathname?.startsWith(href) ?? false
  }

  return (
    <motion.aside
      layout
      transition={{ duration: 0.3, ease: "easeInOut" }}
      className={cn(
        "hidden lg:flex flex-col border-r border-white/[0.06] bg-[#2C2929]/60 backdrop-blur-2xl relative shrink-0 h-dvh",
        collapsed ? "w-[68px]" : "w-[240px]"
      )}
    >
      {/* ── Logo ── */}
      <Link
        href="/"
        className={cn(
          "flex items-center border-b border-white/[0.06] px-4 h-16 shrink-0 group",
          collapsed ? "justify-center" : "gap-3"
        )}
      >
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#CC3A63] to-[#A2AB73] flex items-center justify-center shrink-0 shadow-lg shadow-[#CC3A63]/20">
          <Sparkles className="h-4 w-4 text-white" />
        </div>
        <AnimatePresence mode="wait">
          {!collapsed && (
            <motion.span
              key="logo-text"
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: "auto" }}
              exit={{ opacity: 0, width: 0 }}
              className="text-base font-bold bg-gradient-to-r from-[#F3F4F4] to-[#B0A79C] bg-clip-text text-transparent whitespace-nowrap overflow-hidden"
            >
              DreamTalk
            </motion.span>
          )}
        </AnimatePresence>
      </Link>

      {/* ── 7 Module Navigation ── */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1 scrollbar-thin">
        <AnimatePresence mode="wait">
          {!collapsed && (
            <motion.span
              key="modules-header"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-[10px] font-semibold tracking-[0.15em] uppercase text-[#8A8178] block px-1 mb-2"
            >
              Modules
            </motion.span>
          )}
        </AnimatePresence>

        {MODULES.map((mod) => {
          const Icon = mod.icon
          const active = pathname === mod.href || pathname?.startsWith(mod.href + "/")
          return (
            <Link
              key={mod.href}
              href={mod.href}
              className={cn(
                "flex items-center gap-3 rounded-xl text-sm font-medium transition-all duration-200 group relative",
                collapsed ? "justify-center py-2.5" : "px-3 py-2",
                active
                  ? "bg-gradient-to-r from-[#CC3A63]/15 to-[#A2AB73]/10 text-[#F3F4F4]"
                  : "text-[#B0A79C] hover:text-[#D8D2C8] hover:bg-white/[0.04]"
              )}
            >
              <div
                className={cn(
                  "w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-all",
                  active ? "ring-2 ring-[#CC3A63]/30" : ""
                )}
                style={{ background: `${mod.color}18`, color: mod.color }}
              >
                <Icon className="h-3.5 w-3.5" />
              </div>
              <AnimatePresence mode="wait">
                {!collapsed && (
                  <motion.span
                    key={mod.label}
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: "auto" }}
                    exit={{ opacity: 0, width: 0 }}
                    className="whitespace-nowrap overflow-hidden text-xs truncate"
                  >
                    {mod.label}
                  </motion.span>
                )}
              </AnimatePresence>
              {active && (
                <motion.div
                  layoutId="activeIndicator"
                  className="absolute right-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full bg-gradient-to-b from-[#CC3A63] to-[#A2AB73] shadow-[0_0_6px_rgba(204,58,99,0.3)]"
                />
              )}
            </Link>
          )
        })}

        {/* Divider */}
        <div className="border-t border-white/[0.06] my-3" />

        {/* Create CTA */}
        <div className={cn(collapsed && "flex justify-center")}>
          <Link
            href="/create"
            className={cn(
              "flex items-center gap-2 rounded-xl text-sm font-medium transition-all group",
              collapsed
                ? "w-10 h-10 justify-center bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] rounded-xl"
                : "w-full px-4 py-3 bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-white shadow-lg shadow-[#CC3A63]/20 hover:shadow-[#CC3A63]/30"
            )}
          >
            <Plus className={cn("h-4 w-4", collapsed ? "text-white" : "")} />
            <AnimatePresence mode="wait">
              {!collapsed && (
                <motion.span
                  key="create-label"
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: "auto" }}
                  exit={{ opacity: 0, width: 0 }}
                  className="font-medium whitespace-nowrap overflow-hidden"
                >
                  Create Digital Human
                </motion.span>
              )}
            </AnimatePresence>
          </Link>
        </div>

        {/* Section header */}
        <AnimatePresence mode="wait">
          {!collapsed && (
            <motion.span
              key="dh-header"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-[10px] font-semibold tracking-[0.15em] uppercase text-[#8A8178] block px-1"
            >
              Your Digital Humans
            </motion.span>
          )}
        </AnimatePresence>

        {dhLoading ? (
          <div className="flex justify-center py-4">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-[#8A8178] border-t-transparent" />
          </div>
        ) : digitalHumans.length === 0 ? (
          <div className="text-center py-4">
            <p className="text-[10px] text-[#8A8178]">No digital humans yet</p>
          </div>
        ) : digitalHumans.map((dh) => {
          const active = pathname === dh.href || pathname?.startsWith(`/dh/${dh.id}`)
          return (
            <Link
              key={dh.id}
              href={dh.href}
              className={cn(
                "flex items-center gap-3 rounded-xl text-sm font-medium transition-all duration-200 group",
                collapsed ? "px-0 justify-center py-2.5" : "px-3 py-2",
                active
                  ? "bg-gradient-to-r from-[#CC3A63]/15 to-[#A2AB73]/10 text-[#F3F4F4]"
                  : "text-[#B0A79C] hover:text-[#D8D2C8] hover:bg-white/[0.04]"
              )}
            >
              <div
                className={cn(
                  "w-7 h-7 rounded-lg flex items-center justify-center text-white text-[10px] font-bold shrink-0",
                  active ? "ring-2 ring-[#CC3A63]/30" : ""
                )}
                style={{ background: dh.color }}
              >
                {dh.initials}
              </div>
              <AnimatePresence mode="wait">
                {!collapsed && (
                  <motion.span
                    key={dh.name}
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: "auto" }}
                    exit={{ opacity: 0, width: 0 }}
                    className="whitespace-nowrap overflow-hidden text-xs truncate"
                  >
                    {dh.name}
                  </motion.span>
                )}
              </AnimatePresence>
              {active && (
                <motion.div
                  layoutId="activeIndicator"
                  className="absolute right-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full bg-gradient-to-b from-[#CC3A63] to-[#A2AB73] shadow-[0_0_6px_rgba(204,58,99,0.3)]"
                />
              )}
            </Link>
          )
        })}
      </nav>

      {/* ── User + Logout ── */}
      <div className="border-t border-white/[0.06] p-3 space-y-2">
        {user && (
          <div className={cn("flex items-center gap-3 px-3 py-2 rounded-xl", collapsed && "justify-center px-0")}>
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#CC3A63] to-[#A2AB73] flex items-center justify-center text-white font-bold text-xs shrink-0">
              {user.full_name?.charAt(0)?.toUpperCase() || "?"}
            </div>
            <AnimatePresence mode="wait">
              {!collapsed && (
                <motion.div
                  key="user-info"
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: "auto" }}
                  exit={{ opacity: 0, width: 0 }}
                  className="min-w-0 overflow-hidden"
                >
                  <p className="text-xs font-semibold text-[#F3F4F4] truncate">{user.full_name || "User"}</p>
                  <p className="text-[10px] text-[#B0A79C] capitalize truncate">{user.role || "Member"}</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            "flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-sm font-medium transition-all text-[#8A8178] hover:text-[#B0A79C] hover:bg-white/[0.04]",
            collapsed && "justify-center px-0"
          )}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          <AnimatePresence mode="wait">
            {!collapsed && (
              <motion.span
                key="collapse-label"
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                className="whitespace-nowrap overflow-hidden text-xs"
              >
                Collapse
              </motion.span>
            )}
          </AnimatePresence>
        </button>
        <button
          onClick={handleLogout}
          className={cn(
            "flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-sm font-medium transition-all text-[#8A8178] hover:text-[#D84C63] hover:bg-[#D84C63]/5",
            collapsed && "justify-center px-0"
          )}
        >
          <div className="w-8 h-8 rounded-lg flex items-center justify-center">
            <LogOut className="h-4 w-4 shrink-0" />
          </div>
          <AnimatePresence mode="wait">
            {!collapsed && (
              <motion.span
                key="logout-label"
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                className="whitespace-nowrap overflow-hidden text-xs"
              >
                Logout
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>
    </motion.aside>
  )
}
