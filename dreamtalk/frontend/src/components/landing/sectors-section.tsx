"use client"

import { motion } from "motion/react"
import { Stethoscope, Briefcase, User, ArrowRight, CheckCircle2 } from "lucide-react"
import { BlurFade } from "@/components/magic/blur-fade"
import { BorderBeam } from "@/components/magic/border-beam"
import { cn } from "@/lib/utils"
import Link from "next/link"

const SECTORS = [
  {
    id: "healthcare",
    title: "Healthcare",
    tagline: "Digital Humans for Patient Care",
    description: "Digital medical assistants, therapy companions, and patient education beings available 24/7. Extend care beyond office hours with digital humans.",
    icon: Stethoscope,
    color: "emerald",
    gradient: "from-primary/20 via-primary/10 to-secondary/20",
    borderColor: "border-primary/30",
    badgeColor: "bg-primary/10 text-primary",
    features: [
      "Patient intake digital humans",
      "Mental health digital companions",
      "Medication reminder beings",
      "Post-op follow-up interactions",
      "HIPAA-compliant infrastructure",
    ],
    href: "/dashboard/healthcare",
    stats: "Used by 200+ clinics",
  },
  {
    id: "business",
    title: "Business",
    tagline: "Your Brand, Personified",
    description: "Custom-branded digital humans for sales, support, internal training, and client engagement. Scale your workforce without hiring overhead.",
    icon: Briefcase,
    color: "blue",
    gradient: "from-accent/20 via-accent/10 to-indigo-500/20",
    borderColor: "border-accent/30",
    badgeColor: "bg-accent/10 text-accent",
    features: [
      "Sales & demo digital humans",
      "Customer support digital beings",
      "Employee training digital humans",
      "Brand ambassador digital humans",
      "Multi-language support",
    ],
    href: "/dashboard/business",
    stats: "Trusted by 500+ companies",
  },
  {
    id: "personal",
    title: "Personal",
    tagline: "Create Your Digital Self",
    description: "Choose from 50+ pre-built digital humans or create your own. Practice languages, get life advice, or just have a meaningful connection — anytime.",
    icon: User,
    color: "purple",
    gradient: "from-secondary/20 via-secondary/10 to-pink-500/20",
    borderColor: "border-secondary/30",
    badgeColor: "bg-secondary/10 text-secondary",
    features: [
      "50+ pre-built digital human personalities",
      "Custom digital human creation studio",
      "Language learning companions",
      "Life coaching & mentorship",
      "Creative brainstorming beings",
    ],
    href: "/dashboard/user",
    stats: "Join 50,000+ users",
  },
]

const colorMap = {
  emerald: { ring: "ring-primary/30", from: "from-primary", to: "to-secondary" },
  blue: { ring: "ring-accent/30", from: "from-accent", to: "to-indigo-500" },
  purple: { ring: "ring-secondary/30", from: "from-secondary", to: "to-pink-500" },
}

export function SectorsSection() {
  return (
    <section id="sectors" className="relative w-full py-12 px-6 lg:px-16 xl:px-24 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-background/0 via-primary/[0.03] to-background/0 pointer-events-none" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" />

      <div className="relative max-w-7xl mx-auto">
        <BlurFade inView offset={10} blur="4px">
          <div className="text-center space-y-4 mb-10">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-xs text-primary font-medium">
              Three Platforms, One Vision
            </span>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
              Built for{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent">
                Everyone
              </span>
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              Whether you&apos;re a healthcare provider, business owner, or individual — Dreamtalk creates digital humans for you
            </p>
          </div>
        </BlurFade>

        <div className="grid lg:grid-cols-3 gap-6">
          {SECTORS.map((sector, i) => {
            const Icon = sector.icon
            const colors = colorMap[sector.color as keyof typeof colorMap]

            return (
              <BlurFade key={sector.id} inView offset={20} blur="6px" delay={0.1 * i}>
                <Link href={sector.href}>
                  <motion.div
                    whileHover={{ y: -4 }}
                    data-glow={sector.color === "emerald" ? "primary" : sector.color === "blue" ? "accent" : "secondary"}
                    className={cn(
                      "group relative flex flex-col rounded-2xl border p-6 transition-all h-full",
                      "bg-gradient-to-br from-card via-card/90 to-card/80 animate-gradient-shift",
                      sector.borderColor
                    )}
                  >
                    <BorderBeam size={120} duration={12} colorFrom={sector.color === "emerald" ? "hsl(var(--primary))" : sector.color === "blue" ? "hsl(var(--accent))" : "hsl(var(--secondary))"} colorTo={sector.color === "emerald" ? "hsl(var(--accent))" : sector.color === "blue" ? "hsl(var(--primary))" : "hsl(var(--accent))"} borderWidth={1} />

                    <div className="relative z-10 space-y-6">
                      {/* Header */}
                      <div className="flex items-start justify-between">
                        <div className={cn("h-14 w-14 rounded-2xl bg-gradient-to-br flex items-center justify-center", sector.gradient, "ring-1", colors.ring)}>
                          <Icon className={cn("h-7 w-7", sector.color === "emerald" ? "text-primary" : sector.color === "blue" ? "text-accent" : "text-secondary")} />
                        </div>
                        <span className={cn("px-2.5 py-1 rounded-full text-[10px] font-medium", sector.badgeColor)}>
                          {sector.stats}
                        </span>
                      </div>

                      {/* Content */}
                      <div className="space-y-3">
                        <h3 className="text-xl font-bold">{sector.title}</h3>
                        <p className="text-sm text-muted-foreground">{sector.description}</p>
                      </div>

                      {/* Features */}
                      <ul className="space-y-2">
                        {sector.features.map((f) => (
                          <li key={f} className="flex items-center gap-2 text-xs text-muted-foreground">
                            <CheckCircle2 className={cn("h-3.5 w-3.5 shrink-0", sector.color === "emerald" ? "text-primary" : sector.color === "blue" ? "text-accent" : "text-secondary")} />
                            {f}
                          </li>
                        ))}
                      </ul>

                      {/* Footer CTA */}
                      <div className="flex items-center gap-1 text-xs font-medium text-muted-foreground group-hover:text-foreground transition-colors pt-2">
                        Learn more <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-1" />
                      </div>
                    </div>
                  </motion.div>
                </Link>
              </BlurFade>
            )
          })}
        </div>
      </div>
    </section>
  )
}
