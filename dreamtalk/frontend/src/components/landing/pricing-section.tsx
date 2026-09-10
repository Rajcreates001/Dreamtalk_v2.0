"use client"

import { motion } from "motion/react"
import { Check, ArrowRight, Sparkles } from "lucide-react"
import { BlurFade } from "@/components/magic/blur-fade"
import { cn } from "@/lib/utils"
import Link from "next/link"

const PLANS = [
  {
    name: "Free",
    tagline: "For personal exploration",
    price: "₹0",
    period: "forever",
    features: [
      "5 digital human personalities",
      "10 min per interaction",
      "Basic voice interaction",
      "Web access only",
    ],
    cta: "Get Started",
    href: "/signup",
    popular: false,
    color: "muted",
  },
  {
    name: "Personal",
    tagline: "For daily conversations",
    price: "₹999",
    period: "/month",
    features: [
      "50+ digital human personalities",
      "Unlimited interaction time",
      "Natural voice & presence",
      "Custom digital human creation (3)",
      "Mobile & web access",
      "Interaction history",
    ],
    cta: "Start Free Trial",
    href: "/signup",
    popular: true,
    color: "purple",
  },
  {
    name: "Healthcare",
    tagline: "For clinics & hospitals",
    price: "Custom",
    period: "/month",
    features: [
      "Everything in Personal",
      "HIPAA-compliant infrastructure",
      "Patient management dashboard",
      "Custom medical digital humans",
      "Analytics & reports",
      "Team accounts (up to 10)",
      "Priority support",
      "API access",
    ],
    cta: "Contact Sales",
    href: "/signup",
    popular: false,
    color: "emerald",
  },
  {
    name: "Business",
    tagline: "For companies & teams",
    price: "Custom",
    period: "/month",
    features: [
      "Everything in Personal",
      "Branded custom digital humans",
      "Sales & support digital humans",
      "Team management dashboard",
      "Analytics & reporting",
      "Unlimited team members",
      "SSO & SAML integration",
      "Dedicated account manager",
    ],
    cta: "Contact Sales",
    href: "/signup",
    popular: false,
    color: "blue",
  },
]

const colorStyles: Record<string, { border: string; bg: string; text: string; badge: string; btn: string }> = {
  muted: {
    border: "border-border/50",
    bg: "bg-muted/10",
    text: "text-muted-foreground",
    badge: "",
    btn: "border border-border text-muted-foreground hover:text-foreground hover:bg-muted/30",
  },
  purple: {
    border: "border-secondary/40",
    bg: "bg-gradient-to-b from-secondary/5 to-muted/10",
    text: "text-secondary",
    badge: "bg-gradient-to-r from-secondary to-accent",
    btn: "bg-secondary text-white hover:bg-secondary/80 shadow-lg shadow-secondary/20",
  },
  emerald: {
    border: "border-primary/30",
    bg: "bg-muted/10",
    text: "text-primary",
    badge: "",
    btn: "border border-primary/30 text-primary hover:bg-primary/10",
  },
  blue: {
    border: "border-accent/30",
    bg: "bg-muted/10",
    text: "text-accent",
    badge: "",
    btn: "border border-accent/30 text-accent hover:bg-accent/10",
  },
}

export function PricingSection() {
  return (
    <section id="pricing" className="relative w-full py-12 px-6 lg:px-16 xl:px-24 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-background/0 via-primary/[0.01] to-background/0 pointer-events-none" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent" />

      <div className="relative max-w-7xl mx-auto">
        <BlurFade inView offset={10} blur="4px">
          <div className="text-center space-y-4 mb-10">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-xs text-primary font-medium">
              Simple Pricing
            </span>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
              One Platform,{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent">
                Four Plans
              </span>
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              Start free, upgrade when you need more. No hidden fees, no surprises.
            </p>
          </div>
        </BlurFade>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
          {PLANS.map((plan, i) => {
            const colors = colorStyles[plan.color]
            return (
              <BlurFade key={plan.name} inView offset={20} blur="6px" delay={0.1 * i}>
                <motion.div
                  whileHover={{ y: -4 }}
                  data-glow={plan.color === "purple" ? "secondary" : plan.color === "emerald" ? "primary" : plan.color === "blue" ? "accent" : undefined}
                  className={cn(
                    "relative flex flex-col rounded-2xl border p-6 transition-all h-full",
                      plan.popular
                        ? cn(colors.border, "bg-gradient-to-br from-card via-card/90 to-card/80 animate-gradient-shift shadow-xl shadow-secondary/5")
                        : cn(colors.border, "bg-gradient-to-br from-card via-card/90 to-card/80 animate-gradient-shift")
                  )}
                >
                  {plan.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 inline-flex items-center gap-1 px-3 py-1 rounded-full bg-gradient-to-r from-primary to-accent text-white text-[10px] font-medium shadow-lg whitespace-nowrap">
                      <Sparkles className="h-3 w-3" />
                      Most Popular
                    </div>
                  )}

                  <div className="flex flex-col gap-6 flex-1">
                    <div>
                      <h3 className="text-lg font-bold">{plan.name}</h3>
                      <p className="text-xs text-muted-foreground mt-1">{plan.tagline}</p>
                    </div>

                    <div className="flex items-baseline gap-1">
                      <span className={cn("text-3xl font-bold", plan.price === "Custom" && "text-lg")}>
                        {plan.price}
                      </span>
                      <span className="text-sm text-muted-foreground">{plan.period}</span>
                    </div>

                    <ul className="space-y-2.5 flex-1">
                      {plan.features.map((f) => (
                        <li key={f} className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Check className={cn("h-3.5 w-3.5 shrink-0", plan.popular ? "text-secondary" : "text-muted-foreground")} />
                          {f}
                        </li>
                      ))}
                    </ul>

                    <Link
                      href={plan.href}
                      className={cn(
                        "flex items-center justify-center gap-2 w-full py-2.5 rounded-xl text-sm font-medium transition-all mt-auto",
                        colors.btn
                      )}
                    >
                      {plan.cta} <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                </motion.div>
              </BlurFade>
            )
          })}
        </div>
      </div>
    </section>
  )
}
