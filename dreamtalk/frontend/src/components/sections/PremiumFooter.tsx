"use client"

import { useState } from "react"
import { motion } from "motion/react"
import { Sparkles, ArrowUp, Heart, Mail } from "lucide-react"
import Link from "next/link"

/**
 * Every entry resolves to a real destination.
 *
 * These were all `<button>` with no onClick and no href — inert, and styled
 * `hover:text-foreground-muted`, the colour they already were, so they gave no
 * hover feedback either. Entries now point at routes that exist or at an
 * anchor on this page. Anything the product genuinely does not have yet is
 * marked `soon` and rendered as non-interactive text rather than a button that
 * lies about being clickable.
 */
type FooterItem = { label: string; href?: string; soon?: boolean }

const footerColumns: { title: string; items: FooterItem[] }[] = [
  {
    title: "Platform",
    items: [
      { label: "Avatar Studio", href: "/avatar-studio" },
      { label: "Voice Engine", href: "/voice-cloning" },
      { label: "Knowledge Base", href: "/knowledge" },
      { label: "Memory System", href: "/digital-brain" },
      { label: "Emotion AI", href: "/brain-manager" },
      { label: "API & SDK", href: "/integrations" },
    ],
  },
  {
    title: "Solutions",
    items: [
      { label: "Personal", href: "/dashboard/user" },
      { label: "Healthcare", href: "/dashboard/healthcare" },
      { label: "Enterprise", href: "/dashboard/business" },
      { label: "Industries", href: "/#industries" },
      { label: "Deployments", href: "/deployments" },
      { label: "Marketplace", href: "/marketplace" },
    ],
  },
  {
    title: "Company",
    items: [
      { label: "Pricing", href: "/#pricing" },
      { label: "Security", href: "/#security" },
      { label: "FAQ", href: "/#faq" },
      { label: "Blog", soon: true },
      { label: "Careers", soon: true },
      { label: "Contact", soon: true },
    ],
  },
  {
    title: "Resources",
    items: [
      { label: "Live Session", href: "/live" },
      { label: "Conversations", href: "/conversations" },
      { label: "Analytics", href: "/analytics" },
      { label: "Design System", href: "/design-system" },
      { label: "Documentation", soon: true },
      { label: "API Reference", soon: true },
    ],
  },
]

export function PremiumFooter() {
  const [email, setEmail] = useState("")
  const [status, setStatus] = useState<"idle" | "invalid" | "pending">("idle")

  return (
    <footer className="relative z-10 border-t border-foreground/[0.04] bg-background">
      {/* Top divider glow */}
      <div className="h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Main footer grid */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-6 gap-8 mb-12">
          {/* Brand */}
          <div className="lg:col-span-2">
            <Link href="/" className="flex items-center gap-2.5 mb-4 group">
              <div className="relative w-8 h-8">
                <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-primary to-secondary animate-breathe" />
                <Sparkles className="relative h-4 w-4 text-white absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
              </div>
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                DreamTalk
              </span>
            </Link>
            <p className="text-sm text-foreground-muted max-w-xs leading-relaxed mb-6">
              The operating system for digital humans. Create, train, and deploy intelligent AI avatars
              with voice, emotion, memory, and knowledge.
            </p>
            {/* Newsletter */}
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-foreground-muted" />
                <input
                  name="newsletter-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Get product updates"
                  aria-label="Email address for product updates"
                  className="w-full bg-card/60 border border-foreground/[0.06] rounded-lg pl-9 pr-3 py-2 text-xs text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-1 focus:ring-primary/30 transition-all"
                />
              </div>
              <motion.button
                type="submit"
                // Previously had no handler at all — it animated on tap and did
                // nothing. There is no subscribe endpoint yet, so rather than
                // fake a success this validates the address and tells the truth.
                onClick={() => {
                  const valid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
                  if (!valid) { setStatus("invalid"); return }
                  setStatus("pending")
                }}
                disabled={status === "pending"}
                className="px-3 py-2 rounded-lg bg-gradient-to-r from-primary to-secondary text-white text-xs font-medium disabled:opacity-60"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                Subscribe
              </motion.button>
            </div>
            {status !== "idle" && (
              <p
                role="status"
                className={`mt-2 text-[11px] ${status === "invalid" ? "text-destructive" : "text-foreground-muted"}`}
              >
                {status === "invalid"
                  ? "Enter a valid email address."
                  : "Product updates aren't wired up yet — nothing was sent."}
              </p>
            )}
          </div>

          {/* Link columns */}
          {footerColumns.map((col) => (
            <div key={col.title}>
              <h4 className="text-sm font-semibold text-foreground mb-4">{col.title}</h4>
              <ul className="space-y-2.5">
                {col.items.map((item) => (
                  <li key={item.label}>
                    {item.href ? (
                      <Link
                        href={item.href}
                        className="text-sm text-foreground-muted hover:text-foreground transition-colors"
                      >
                        {item.label}
                      </Link>
                    ) : (
                      <span
                        aria-disabled="true"
                        title="Coming soon"
                        className="text-sm text-foreground-muted/50 cursor-default"
                      >
                        {item.label}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4 pt-8 border-t border-foreground/[0.04]">
          <p className="text-xs text-foreground-muted flex items-center gap-1.5">
            © 2026 DreamTalk. Built with <Heart className="h-3 w-3 text-destructive" /> for Digital Humans
          </p>
          <div className="flex items-center gap-4">
            {["Privacy", "Terms", "Cookies", "Licenses"].map((item) => (
              <span
                key={item}
                aria-disabled="true"
                title="Coming soon"
                className="text-xs text-foreground-muted/50 cursor-default"
              >
                {item}
              </span>
            ))}
            <motion.button
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
              className="w-8 h-8 rounded-lg bg-card/80 border border-foreground/[0.06] flex items-center justify-center text-foreground-muted hover:text-foreground transition-all"
              whileHover={{ y: -2 }}
            >
              <ArrowUp className="h-4 w-4" />
            </motion.button>
          </div>
        </div>
      </div>
    </footer>
  )
}
