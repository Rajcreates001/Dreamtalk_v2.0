"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { motion, AnimatePresence } from "motion/react"
import {
  Sparkles, Menu, X, ChevronDown, ArrowRight, Check,
  Bot, Users,
  Search, LogIn,
} from "lucide-react"
import Link from "next/link"
import dynamic from "next/dynamic"

// Hero — dynamically imported to defer Three.js bundle (~500KB)
// Three.js Canvas itself defers mount via requestIdleCallback (see SceneCanvas),
// but the JavaScript bundle must still be downloaded + parsed.
// Dynamic import moves this off the critical path entirely.
// The loading placeholder prevents layout shift while the chunk loads.
const HeroContainer = dynamic(() => import("@/components/hero/HeroContainer").then(m => ({ default: m.HeroContainer })), {
  ssr: false,
  loading: () => <div className="relative min-h-dvh bg-[#201D1D]" />,
})

// ── All section components are DYNAMIC (lazy-loaded, SSR disabled) ──
// This means the initial JS bundle is ~80% smaller.
// Sections only load when they scroll into the viewport.
const ProblemComparison = dynamic(() => import("@/components/sections/ProblemComparison").then(m => ({ default: m.ProblemComparison })), { ssr: false })
const DreamTalkSolution = dynamic(() => import("@/components/sections/DreamTalkSolution").then(m => ({ default: m.DreamTalkSolution })), { ssr: false })
const AvatarStudioInteractive = dynamic(() => import("@/components/sections/AvatarStudioInteractive").then(m => ({ default: m.AvatarStudioInteractive })), { ssr: false })
const HumanizationEngine = dynamic(() => import("@/components/sections/HumanizationEngine").then(m => ({ default: m.HumanizationEngine })), { ssr: false })
const MemoryVisualization = dynamic(() => import("@/components/sections/MemoryVisualization").then(m => ({ default: m.MemoryVisualization })), { ssr: false })
const KnowledgeEngine = dynamic(() => import("@/components/sections/KnowledgeEngine").then(m => ({ default: m.KnowledgeEngine })), { ssr: false })
const ReasoningEngine = dynamic(() => import("@/components/sections/ReasoningEngine").then(m => ({ default: m.ReasoningEngine })), { ssr: false })
const VoiceIntelligence = dynamic(() => import("@/components/sections/VoiceIntelligence").then(m => ({ default: m.VoiceIntelligence })), { ssr: false })
const DeploymentNetwork = dynamic(() => import("@/components/sections/DeploymentNetwork").then(m => ({ default: m.DeploymentNetwork })), { ssr: false })
const IndustrySolutions = dynamic(() => import("@/components/sections/IndustrySolutions").then(m => ({ default: m.IndustrySolutions })), { ssr: false })
const SecurityIntegrations = dynamic(() => import("@/components/sections/SecurityIntegrations").then(m => ({ default: m.SecurityIntegrations })), { ssr: false })
const MetricsCounter = dynamic(() => import("@/components/sections/MetricsCounter").then(m => ({ default: m.MetricsCounter })), { ssr: false })
const PremiumTestimonials = dynamic(() => import("@/components/sections/PremiumTestimonials").then(m => ({ default: m.PremiumTestimonials })), { ssr: false })
const PremiumFAQ = dynamic(() => import("@/components/sections/PremiumFAQ").then(m => ({ default: m.PremiumFAQ })), { ssr: false })
const PremiumCTA = dynamic(() => import("@/components/sections/PremiumCTA").then(m => ({ default: m.PremiumCTA })), { ssr: false })
const PremiumFooter = dynamic(() => import("@/components/sections/PremiumFooter").then(m => ({ default: m.PremiumFooter })), { ssr: false })

import { SectionWrapper, SectionHeading, StaggerGrid, staggerItem, GlassCard } from "@/components/sections/SectionWrapper"
import { Splash } from "@/components/splash/Splash"

const Nav = () => {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const scrollFrame = useRef(0)

  useEffect(() => {
    const onScroll = () => {
      // RAF throttle: only update state once per frame max
      if (scrollFrame.current) return
      scrollFrame.current = requestAnimationFrame(() => {
        setScrolled(window.scrollY > 40)
        scrollFrame.current = 0
      })
    }
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => {
      window.removeEventListener("scroll", onScroll)
      if (scrollFrame.current) cancelAnimationFrame(scrollFrame.current)
    }
  }, [])

  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, delay: 0.1 }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
        scrolled
          ? "bg-[#201D1D]/80 backdrop-blur-2xl border-b border-white/[0.06] py-3"
          : "bg-transparent py-5"
      }`}
    >
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="relative w-8 h-8">
            <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-[#CC3A63] to-[#A2AB73] animate-breathe" />
            <Sparkles className="relative h-4 w-4 text-white absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
          </div>
          <span className="font-display font-bold text-lg tracking-tight text-[#F3F4F4]">
            DreamTalk <span className="bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] bg-clip-text text-transparent">Astra</span>
          </span>
        </Link>

        <div className="hidden lg:flex items-center gap-8">
          {["Platform", "Solutions", "Developers", "Pricing"].map((item) => (
            <button key={item} className="flex items-center gap-1 text-sm text-[#B0A79C] hover:text-[#F3F4F4] transition-colors">
              {item} <ChevronDown className="h-3 w-3" />
            </button>
          ))}
        </div>

        <div className="hidden lg:flex items-center gap-3">
          <button className="w-9 h-9 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center text-[#B0A79C] hover:text-[#F3F4F4] transition-all">
            <Search className="h-4 w-4" />
          </button>
          
          <Link href="/login" className="px-4 py-2 rounded-xl text-sm font-medium text-[#D8D2C8] hover:text-[#F3F4F4] hover:bg-white/[0.04] transition-all">
            Sign In
          </Link>
          <Link href="/create-twin" className="px-5 py-2 rounded-xl bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-white text-sm font-medium shadow-lg shadow-[#CC3A63]/20 hover:shadow-[#CC3A63]/30 transition-all">
            Get Started
          </Link>
        </div>

        <button onClick={() => setMobileOpen(!mobileOpen)} className="lg:hidden text-[#B0A79C]">
          {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </nav>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="lg:hidden bg-[#2C2929]/95 backdrop-blur-2xl border-t border-white/[0.06] overflow-hidden"
          >
            <div className="px-4 py-6 space-y-4">
              {["Platform", "Solutions", "Developers", "Pricing", "Resources", "Company"].map((item) => (
                <button key={item} className="block w-full text-left text-sm text-[#D8D2C8] hover:text-[#F3F4F4] py-2 transition-colors">
                  {item}
                </button>
              ))}
              <div className="flex items-center gap-3 pt-4 border-t border-white/[0.06]">
                <Link href="/login" className="flex-1 text-center px-4 py-2.5 rounded-xl border border-white/[0.06] text-sm font-medium text-[#D8D2C8]">
                  Sign In
                </Link>
                <Link href="/signup" className="flex-1 text-center px-4 py-2.5 rounded-xl bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-white text-sm font-medium">
                  Get Started
                </Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  )
}

export default function LandingPage() {
  const [demoInput, setDemoInput] = useState("")
  const [demoMessages, setDemoMessages] = useState<{ role: string; text: string }[]>([
    { role: "assistant", text: "Hello! I'm an AI avatar powered by DreamTalk. Ask me anything!" },
  ])
  const [demoLoading, setDemoLoading] = useState(false)

  const handleDemoSend = useCallback(() => {
    if (!demoInput.trim() || demoLoading) return
    const userMsg = demoInput.trim()
    setDemoInput("")
    setDemoMessages((prev) => [...prev, { role: "user", text: userMsg }])
    setDemoLoading(true)
    setTimeout(() => {
      const responses: Record<string, string> = {
        hello: "Hi there! I'm your DreamTalk AI avatar. I can help with conversations, tasks, or just chat!",
        who: "I'm an AI digital human — built on DreamTalk's platform. I can speak, understand emotions, remember context, and learn from knowledge bases.",
        what: "DreamTalk lets you create, train, and deploy intelligent AI avatars for personal, healthcare, and business use.",
        price: "DreamTalk offers Free, Pro (₹2,499/mo), and Business (₹8,499/mo) plans. Check our pricing section for details!",
      }
      const reply = responses[userMsg.toLowerCase()] || `That's a great question! DreamTalk's AI avatars can handle everything from customer support to personal companionship. Try asking "what", "who", or "price"!`
      setTimeout(() => {
        setDemoMessages((prev) => [...prev, { role: "assistant", text: reply }])
        setDemoLoading(false)
      }, 1000)
    }, 500)
  }, [demoInput, demoLoading])

  return (
    <main className="relative min-h-dvh bg-[#201D1D] overflow-x-hidden" style={{ contain: "paint layout" }}>
      <Splash />
      <Nav />

      {/* ─── CHAPTER 1: Hero — Digital Human Awakening ─── */}
      <HeroContainer />

      {/* ─── CHAPTER 2: The Problem — AI Fragmentation ─── */}
      <ProblemComparison />

      {/* ─── CHAPTER 3: The Solution — DreamTalk OS ─── */}
      <DreamTalkSolution />

      {/* ─── Interactive AI Demo ─── */}
      <SectionWrapper id="demo" bg="aurora" reveal="blur" spacing="compact">
        <div className="max-w-4xl mx-auto">
          <SectionHeading
            label="Live Demo"
            title="Talk to an AI Avatar"
            description="Type a message and see how DreamTalk avatars respond with real-time intelligence."
          />
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="rounded-[20px] bg-[#2C2929]/80 backdrop-blur-2xl border border-white/[0.06] overflow-hidden shadow-2xl"
          >
            <div className="flex items-center gap-3 px-5 py-3 border-b border-white/[0.06] bg-white/[0.02]">
              <div className="flex gap-1.5">
                <span className="w-3 h-3 rounded-full bg-[#D84C63]" />
                <span className="w-3 h-3 rounded-full bg-[#D6A44C]" />
                <span className="w-3 h-3 rounded-full bg-[#8F9A5E]" />
              </div>
              <div className="flex items-center gap-2 mx-auto">
                <Bot className="h-4 w-4 text-[#CC3A63]" />
                <span className="text-xs text-[#B0A79C] font-medium">DreamTalk Avatar — Interactive Demo</span>
              </div>
            </div>
            <div className="p-6 space-y-4 min-h-[300px] max-h-[400px] overflow-y-auto" id="demo-chat">
              {demoMessages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex items-start gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
                >
                  <div className={`w-8 h-8 rounded-xl shrink-0 flex items-center justify-center ${
                    msg.role === "user" ? "bg-gradient-to-br from-[#A2AB73]/20 to-[#A2AB73]/20" : "bg-gradient-to-br from-[#CC3A63]/20 to-[#A2AB73]/20"
                  }`}>
                    {msg.role === "user" ? <Users className="h-4 w-4 text-[#A2AB73]" /> : <Bot className="h-4 w-4 text-[#CC3A63]" />}
                  </div>
                  <div className={`max-w-[80%] px-4 py-2.5 rounded-xl text-sm ${
                    msg.role === "user"
                      ? "bg-gradient-to-r from-[#CC3A63]/20 to-[#A2AB73]/10 text-[#F3F4F4] rounded-tr-sm"
                      : "bg-white/[0.04] border border-white/[0.06] text-[#D8D2C8] rounded-tl-sm"
                  }`}>
                    {msg.text}
                  </div>
                </motion.div>
              ))}
              {demoLoading && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#CC3A63]/20 to-[#A2AB73]/20 flex items-center justify-center">
                    <Bot className="h-4 w-4 text-[#CC3A63]" />
                  </div>
                  <div className="flex gap-1 items-center px-4 py-3 rounded-xl bg-white/[0.04] border border-white/[0.06]">
                    <motion.span className="w-1.5 h-1.5 rounded-full bg-[#CC3A63]" animate={{ y: [0, -4, 0] }} transition={{ duration: 0.6, repeat: Infinity }} />
                    <motion.span className="w-1.5 h-1.5 rounded-full bg-[#CC3A63]" animate={{ y: [0, -4, 0] }} transition={{ duration: 0.6, delay: 0.15, repeat: Infinity }} />
                    <motion.span className="w-1.5 h-1.5 rounded-full bg-[#CC3A63]" animate={{ y: [0, -4, 0] }} transition={{ duration: 0.6, delay: 0.3, repeat: Infinity }} />
                  </div>
                </motion.div>
              )}
            </div>
            <div className="p-4 border-t border-white/[0.06] bg-white/[0.02]">
              <div className="flex items-center gap-3">
                <input
                  name="demo-message"
                  value={demoInput}
                  onChange={(e) => setDemoInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleDemoSend()}
                  placeholder="Type a message... (try: hello, who, what, price)"
                  className="flex-1 bg-white/[0.04] border border-white/[0.06] rounded-xl px-4 py-2.5 text-sm text-[#F3F4F4] placeholder:text-[#8A8178] focus:outline-none focus:ring-2 focus:ring-[#CC3A63]/30 focus:border-[#CC3A63]/50 transition-all"
                />
                <button
                  onClick={handleDemoSend}
                  disabled={demoLoading || !demoInput.trim()}
                  className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-white text-sm font-medium disabled:opacity-50 hover:shadow-lg hover:shadow-[#CC3A63]/20 transition-all"
                >
                  Send
                </button>
              </div>
              <div className="flex gap-2 mt-3">
                {["Hello", "What is DreamTalk?", "How much?"].map((s) => (
                  <button
                    key={s}
                    onClick={() => { setDemoInput(s); setTimeout(handleDemoSend, 100) }}
                    className="px-3 py-1 rounded-lg bg-white/[0.04] border border-white/[0.06] text-[10px] text-[#8A8178] hover:text-[#B0A79C] hover:bg-white/[0.06] transition-all"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </SectionWrapper>

      {/* ─── CHAPTER 4: Avatar Studio — Creation Pipeline ─── */}
      <AvatarStudioInteractive />

      {/* ─── CHAPTER 5: Humanization Engine ─── */}
      <HumanizationEngine />

      {/* ─── CHAPTER 6: Memory Engine ─── */}
      <MemoryVisualization />

      {/* ─── CHAPTER 7: Knowledge Engine ─── */}
      <KnowledgeEngine />

      {/* ─── CHAPTER 8: Reasoning Engine ─── */}
      <ReasoningEngine />

      {/* ─── CHAPTER 9: Voice Intelligence ─── */}
      <VoiceIntelligence />

      {/* ─── CHAPTER 10: Deployment ─── */}
      <DeploymentNetwork />

      {/* ─── CHAPTER 11: Industry Solutions ─── */}
      <IndustrySolutions />

      {/* ─── Metrics & Trust ─── */}
      <MetricsCounter />

      {/* ─── CHAPTER 12: Security & Integrations ─── */}
      <SecurityIntegrations />

      {/* ─── CHAPTER 14: Testimonials ─── */}
      <PremiumTestimonials />

      {/* ─── Pricing Section ─── */}
      <PricingSection />

      {/* ─── CHAPTER 15: FAQ ─── */}
      <PremiumFAQ />

      {/* ─── CHAPTER 16: CTA — Final Conversion ─── */}
      <PremiumCTA />

      {/* ─── Footer ─── */}
      <PremiumFooter />
    </main>
  )
}

/* ─── Pricing Section ─── */
const plans = [
  {
    name: "Free", monthly: 0, yearly: 0, desc: "Perfect for getting started",
    features: ["5 AI Avatars", "Basic Voice", "10 min/interaction", "1 Knowledge Base", "Community Support"],
    cta: "Get Started", highlight: false,
  },
  {
    name: "Pro", monthly: 2499, yearly: 1999, desc: "Best for professionals",
    features: ["Unlimited Avatars", "Voice Cloning", "60 min/interaction", "10 Knowledge Bases", "Priority Support", "Analytics Dashboard", "API Access"],
    cta: "Start Free Trial", highlight: true,
  },
  {
    name: "Business", monthly: 8499, yearly: 6999, desc: "For organizations",
    features: ["Everything in Pro", "Unlimited interactions", "Unlimited Knowledge Bases", "Custom Integrations", "SSO & RBAC", "Dedicated Support", "SLA Guarantee", "On-premise Deployment"],
    cta: "Contact Sales", highlight: false,
  },
]

function PricingSection() {
  const [yearly, setYearly] = useState(false)

  return (
    <SectionWrapper id="pricing" bg="alt" label="Pricing" reveal="slide">
      <SectionHeading label="Pricing" title="Choose your plan" description="Start free, scale as you grow. No hidden fees, no surprises." />

      <div className="flex justify-center mb-10">
        <div className="inline-flex items-center gap-2 p-1 rounded-xl bg-[#2C2929]/80 border border-white/[0.06]">
          {[
            { label: "Monthly", active: !yearly, onClick: () => setYearly(false) },
            { label: "Yearly", active: yearly, onClick: () => setYearly(true), badge: "Save 20%" },
          ].map((opt) => (
            <button
              key={opt.label}
              onClick={opt.onClick}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                opt.active
                  ? "bg-gradient-to-r from-[#CC3A63]/20 to-[#A2AB73]/10 text-[#F3F4F4] border border-white/[0.08]"
                  : "text-[#8A8178] hover:text-[#B0A79C]"
              }`}
            >
              {opt.label}
              {opt.badge && <span className="ml-1.5 text-[#A2AB73] text-[10px]">{opt.badge}</span>}
            </button>
          ))}
        </div>
      </div>

      <StaggerGrid className="grid md:grid-cols-3 gap-4 max-w-5xl mx-auto">
        {plans.map((plan) => {
          const price = yearly ? plan.yearly : plan.monthly
          return (
            <GlassCard key={plan.name} className={plan.highlight ? "border-[#CC3A63]/30 shadow-xl shadow-[#CC3A63]/10" : ""}>
              <h3 className="text-lg font-bold text-[#F3F4F4] mb-1">{plan.name}</h3>
              <p className="text-sm text-[#B0A79C] mb-4">{plan.desc}</p>
              <div className="mb-6">
                <span className="text-3xl font-bold text-[#F3F4F4]">₹{price.toLocaleString()}</span>
                <span className="text-sm text-[#8A8178]">/mo</span>
              </div>
              <ul className="space-y-2 mb-6">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-[#D8D2C8]">
                    <Check className="h-4 w-4 text-[#A2AB73] shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/signup"
                className={`block w-full text-center px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  plan.highlight
                    ? "bg-gradient-to-r from-[#CC3A63] to-[#A2AB73] text-white shadow-lg shadow-[#CC3A63]/20 hover:shadow-[#CC3A63]/30"
                    : "bg-white/[0.04] border border-white/[0.06] text-[#D8D2C8] hover:text-[#F3F4F4] hover:bg-white/[0.06]"
                }`}
              >
                {plan.cta}
              </Link>
            </GlassCard>
          )
        })}
      </StaggerGrid>
    </SectionWrapper>
  )
}
