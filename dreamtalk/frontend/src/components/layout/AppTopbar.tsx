"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { useRouter } from "next/navigation"
import { motion, AnimatePresence } from "motion/react"
import {
  Search,
  Bell,
  User,
  Sparkles,
  Menu,
  Command,
  MessageSquare,
  Users,
  Bot,
  Settings as SettingsIcon,
} from "lucide-react"
import { cn } from "@/lib/utils"

const QUICK_SEARCH_ITEMS = [
  { href: "/home", label: "Go to Home", icon: Sparkles },
  { href: "/digital-humans", label: "Browse Digital Humans", icon: Users },
  { href: "/studio", label: "Open Studio", icon: Bot },
  { href: "/conversations", label: "View Conversations", icon: MessageSquare },
  { href: "/settings", label: "Settings", icon: SettingsIcon },
]

export function AppTopbar({ onToggleSidebar }: { onToggleSidebar?: () => void }) {
  const router = useRouter()
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedIndex, setSelectedIndex] = useState(0)
  const searchRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [user, setUser] = useState<{ full_name?: string; role?: string } | null>(null)

  useEffect(() => {
    const stored = localStorage.getItem("user")
    if (stored) {
      try { setUser(JSON.parse(stored)) } catch {}
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        setSearchOpen((prev) => !prev)
      }
      if (e.key === "Escape") {
        setSearchOpen(false)
        setSearchQuery("")
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [])

  useEffect(() => {
    if (searchOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [searchOpen])

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setSearchOpen(false)
        setSearchQuery("")
      }
    }
    if (searchOpen) {
      document.addEventListener("mousedown", handleClickOutside)
    }
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [searchOpen])

  const filteredItems = QUICK_SEARCH_ITEMS.filter(
    (item) =>
      item.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.href.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleSelect = useCallback(
    (href: string) => {
      setSearchOpen(false)
      setSearchQuery("")
      router.push(href)
    },
    [router]
  )

  const handleKeyNavigation = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault()
      setSelectedIndex((prev) => (prev + 1) % filteredItems.length)
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % filteredItems.length)
    } else if (e.key === "Enter" && filteredItems[selectedIndex]) {
      handleSelect(filteredItems[selectedIndex].href)
    }
  }

  return (
    <header className="flex items-center justify-between h-16 px-4 lg:px-6 border-b border-white/[0.06] bg-[#2C2929]/40 backdrop-blur-xl shrink-0 relative z-30">
      {/* Left: Mobile hamburger + brand */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="lg:hidden w-9 h-9 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center text-[#B0A79C] hover:text-[#F3F4F4] transition-colors"
        >
          <Menu className="h-4 w-4" />
        </button>
        <div className="hidden sm:flex items-center gap-1.5">
          <span className="text-xs font-semibold text-[#8A8178] tracking-wide">DreamTalk</span>
          <span className="text-[10px] text-[#8A8178]">/</span>
          <span className="text-[10px] text-[#B0A79C] font-medium capitalize">
            {user?.role || "workspace"}
          </span>
        </div>
      </div>

      {/* Center: Search */}
      <div className="relative" ref={searchRef}>
        <button
          onClick={() => setSearchOpen(true)}
          className="hidden sm:flex items-center gap-2 px-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-[#8A8178] text-sm hover:bg-white/[0.08] hover:border-white/[0.12] transition-all min-w-[240px] lg:min-w-[320px]"
        >
          <Search className="h-4 w-4 shrink-0" />
          <span className="text-xs">Search avatars, chats, documents...</span>
          <div className="ml-auto flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-white/[0.08] text-[10px] font-mono text-[#8A8178]">
            <Command className="h-2.5 w-2.5" />
            K
          </div>
        </button>

        <AnimatePresence>
          {searchOpen && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="fixed sm:absolute top-16 sm:top-12 left-0 sm:left-1/2 sm:-translate-x-1/2 right-0 sm:right-auto sm:w-[480px] mx-4 sm:mx-0 rounded-2xl bg-[#2C2929] border border-white/[0.12] shadow-2xl shadow-black/40 overflow-hidden z-50"
            >
              {/* Search input */}
              <div className="flex items-center gap-3 px-4 py-3 border-b border-white/[0.06]">
                <Search className="h-4 w-4 text-[#8A8178] shrink-0" />
                <input
                  ref={inputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => { setSearchQuery(e.target.value); setSelectedIndex(0) }}
                  onKeyDown={handleKeyNavigation}
                  placeholder="Search avatars, conversations, documents..."
                  className="flex-1 bg-transparent text-sm text-[#F3F4F4] placeholder:text-[#8A8178] focus:outline-none"
                />
                <button
                  onClick={() => { setSearchOpen(false); setSearchQuery("") }}
                  className="text-[10px] px-2 py-1 rounded-md bg-white/[0.06] text-[#8A8178] hover:text-[#B0A79C] font-mono"
                >
                  ESC
                </button>
              </div>

              {/* Results */}
              <div className="p-2 space-y-0.5 max-h-[300px] overflow-y-auto">
                {filteredItems.length === 0 ? (
                  <div className="px-4 py-8 text-center">
                    <p className="text-xs text-[#8A8178]">No results found</p>
                  </div>
                ) : (
                  filteredItems.map((item, i) => {
                    const Icon = item.icon
                    return (
                      <button
                        key={item.href}
                        onClick={() => handleSelect(item.href)}
                        onMouseEnter={() => setSelectedIndex(i)}
                        className={cn(
                          "flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-sm transition-all text-left",
                          i === selectedIndex
                            ? "bg-[#CC3A63]/10 text-[#F3F4F4]"
                            : "text-[#B0A79C] hover:text-[#D8D2C8] hover:bg-white/[0.04]"
                        )}
                      >
                        <div className={cn(
                          "w-7 h-7 rounded-lg flex items-center justify-center",
                          i === selectedIndex ? "bg-[#CC3A63]/20" : "bg-white/[0.04]"
                        )}>
                          <Icon className={cn("h-3.5 w-3.5", i === selectedIndex && "text-[#CC3A63]")} />
                        </div>
                        <span>{item.label}</span>
                      </button>
                    )
                  })
                )}
              </div>

              {/* Footer hints */}
              <div className="flex items-center gap-3 px-4 py-2 border-t border-white/[0.06] bg-white/[0.02]">
                <div className="flex items-center gap-1.5 text-[10px] text-[#8A8178]">
                  <kbd className="px-1 py-0.5 rounded bg-white/[0.06] font-mono">↑↓</kbd>
                  <span>Navigate</span>
                </div>
                <div className="flex items-center gap-1.5 text-[10px] text-[#8A8178]">
                  <kbd className="px-1 py-0.5 rounded bg-white/[0.06] font-mono">↵</kbd>
                  <span>Open</span>
                </div>
                <div className="flex items-center gap-1.5 text-[10px] text-[#8A8178] ml-auto">
                  <kbd className="px-1 py-0.5 rounded bg-white/[0.06] font-mono">esc</kbd>
                  <span>Close</span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        {/* Notification bell */}
        <button className="relative w-9 h-9 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center text-[#B0A79C] hover:text-[#F3F4F4] hover:bg-white/[0.08] transition-all">
          <Bell className="h-4 w-4" />
          <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-[#CC3A63] shadow-[0_0_6px_rgba(204,58,99,0.6)]" />
        </button>

        {/* Credits */}
        <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#CC3A63]/10 border border-[#CC3A63]/20 text-xs text-[#CC3A63] font-medium">
          <Sparkles className="h-3 w-3" />
          2,450
        </div>

        {/* User avatar */}
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#CC3A63] to-[#A2AB73] flex items-center justify-center text-white font-bold text-xs cursor-pointer shadow-lg shadow-[#CC3A63]/20">
          {user?.full_name?.charAt(0)?.toUpperCase() || "?"}
        </div>
      </div>
    </header>
  )
}
