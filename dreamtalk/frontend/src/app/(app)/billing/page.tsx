"use client"

import { motion } from "motion/react"
import { Sparkles, CreditCard, CheckCircle, ArrowRight } from "lucide-react"
import Link from "next/link"

const PLANS = [
  {
    name: "Free",
    price: "$0",
    desc: "For personal exploration",
    features: ["1 Digital Human", "100 conversations/month", "Basic knowledge", "Community support"],
    color: "#8A8178",
  },
  {
    name: "Pro",
    price: "$29",
    desc: "For professionals",
    features: ["5 Digital Humans", "10,000 conversations/month", "Full knowledge access", "Priority support", "Custom voice"],
    color: "#CC3A63",
    popular: true,
  },
  {
    name: "Business",
    price: "$99",
    desc: "For teams and enterprises",
    features: ["Unlimited Digital Humans", "Unlimited conversations", "Advanced analytics", "Dedicated support", "Custom models", "API access"],
    color: "#A2AB73",
  },
]

export default function BillingPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-foreground">Billing</h1>
        <p className="text-sm text-foreground-muted mt-1">Manage your subscription and usage</p>
      </div>

      {/* Current plan */}
      <div className="p-5 rounded-xl bg-gradient-to-br from-[#CC3A63]/8 to-[#A2AB73]/5 border border-[#CC3A63]/15">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#CC3A63] to-[#A2AB73] flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">Pro Plan</h3>
              <p className="text-xs text-foreground-muted">Next billing: April 15, 2026</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm text-foreground-muted">
              <span className="text-lg font-bold text-foreground">$29</span>/month
            </p>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-4 text-xs text-foreground-muted">
          <div className="flex items-center gap-1.5">
            <CheckCircle className="h-3 w-3 text-[#A2AB73]" />
            <span>2,450 / 10,000 conversations</span>
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle className="h-3 w-3 text-[#A2AB73]" />
            <span>3 / 5 avatars</span>
          </div>
        </div>
      </div>

      {/* Plans grid */}
      <div className="grid sm:grid-cols-3 gap-4">
        {PLANS.map((plan, i) => (
          <motion.div
            key={plan.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            className={`relative p-5 rounded-xl border transition-all ${
              plan.popular
                ? "bg-gradient-to-br from-[#CC3A63]/10 to-[#A2AB73]/8 border-[#CC3A63]/30 shadow-lg shadow-[#CC3A63]/10"
                : "bg-card/80 border-foreground/[0.06] hover:border-foreground/[0.12]"
            }`}
          >
            {plan.popular && (
              <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-[10px] text-white font-medium">
                Popular
              </div>
            )}
            <h3 className="text-lg font-bold text-foreground">{plan.name}</h3>
            <div className="mt-2 mb-4">
              <span className="text-3xl font-bold text-foreground">{plan.price}</span>
              {plan.price !== "$0" && <span className="text-sm text-foreground-muted">/month</span>}
            </div>
            <p className="text-xs text-foreground-muted mb-4">{plan.desc}</p>

            <ul className="space-y-2 mb-5">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2">
                  <CheckCircle className="h-3.5 w-3.5 text-[#A2AB73] mt-0.5 shrink-0" />
                  <span className="text-xs text-foreground">{f}</span>
                </li>
              ))}
            </ul>

            <Link
              href="#"
              className={`flex items-center justify-center gap-2 w-full py-2.5 rounded-xl text-sm font-medium transition-all ${
                plan.popular
                  ? "bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-white shadow-lg shadow-[#CC3A63]/20"
                  : "bg-foreground/[0.04] border border-foreground/[0.06] text-foreground-muted hover:text-foreground hover:bg-foreground/[0.08]"
              }`}
            >
              {plan.name === "Free" ? "Current Plan" : "Upgrade"} <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
