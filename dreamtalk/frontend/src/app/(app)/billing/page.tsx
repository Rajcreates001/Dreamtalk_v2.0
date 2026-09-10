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
    color: "#64748B",
  },
  {
    name: "Pro",
    price: "$29",
    desc: "For professionals",
    features: ["5 Digital Humans", "10,000 conversations/month", "Full knowledge access", "Priority support", "Custom voice"],
    color: "#7C5CFF",
    popular: true,
  },
  {
    name: "Business",
    price: "$99",
    desc: "For teams and enterprises",
    features: ["Unlimited Digital Humans", "Unlimited conversations", "Advanced analytics", "Dedicated support", "Custom models", "API access"],
    color: "#00E5FF",
  },
]

export default function BillingPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-[#F8FAFC]">Billing</h1>
        <p className="text-sm text-[#94A3B8] mt-1">Manage your subscription and usage</p>
      </div>

      {/* Current plan */}
      <div className="p-5 rounded-xl bg-gradient-to-br from-[#7C5CFF]/8 to-[#00E5FF]/5 border border-[#7C5CFF]/15">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#7C5CFF] to-[#00E5FF] flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#F8FAFC]">Pro Plan</h3>
              <p className="text-xs text-[#94A3B8]">Next billing: April 15, 2026</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm text-[#64748B]">
              <span className="text-lg font-bold text-[#F8FAFC]">$29</span>/month
            </p>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-4 text-xs text-[#94A3B8]">
          <div className="flex items-center gap-1.5">
            <CheckCircle className="h-3 w-3 text-[#42FFC6]" />
            <span>2,450 / 10,000 conversations</span>
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle className="h-3 w-3 text-[#42FFC6]" />
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
                ? "bg-gradient-to-br from-[#7C5CFF]/10 to-[#00E5FF]/8 border-[#7C5CFF]/30 shadow-lg shadow-[#7C5CFF]/10"
                : "bg-[#0F172A]/80 border-white/[0.06] hover:border-white/[0.12]"
            }`}
          >
            {plan.popular && (
              <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-gradient-to-r from-[#7C5CFF] to-[#00E5FF] text-[10px] text-white font-medium">
                Popular
              </div>
            )}
            <h3 className="text-lg font-bold text-[#F8FAFC]">{plan.name}</h3>
            <div className="mt-2 mb-4">
              <span className="text-3xl font-bold text-[#F8FAFC]">{plan.price}</span>
              {plan.price !== "$0" && <span className="text-sm text-[#64748B]">/month</span>}
            </div>
            <p className="text-xs text-[#94A3B8] mb-4">{plan.desc}</p>

            <ul className="space-y-2 mb-5">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2">
                  <CheckCircle className="h-3.5 w-3.5 text-[#42FFC6] mt-0.5 shrink-0" />
                  <span className="text-xs text-[#CBD5E1]">{f}</span>
                </li>
              ))}
            </ul>

            <Link
              href="#"
              className={`flex items-center justify-center gap-2 w-full py-2.5 rounded-xl text-sm font-medium transition-all ${
                plan.popular
                  ? "bg-gradient-to-r from-[#7C5CFF] to-[#00E5FF] text-white shadow-lg shadow-[#7C5CFF]/20"
                  : "bg-white/[0.04] border border-white/[0.06] text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-white/[0.08]"
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
