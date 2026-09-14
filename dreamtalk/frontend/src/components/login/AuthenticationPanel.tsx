"use client"

import { useState, useRef, useEffect } from "react"
import { motion, AnimatePresence } from "motion/react"
import { Mail, Lock, Eye, EyeOff, ArrowRight, AlertTriangle, Sparkles, User, Stethoscope, Briefcase } from "lucide-react"
import { authApi, storeAuth, loginWithGoogle, loginWithGitHub, loginWithMicrosoft } from "@/lib/api"
import { navigateAfterAuth, dashboardPathForRole } from "@/lib/navigate"
import Link from "next/link"
import { useRouter } from "next/navigation"

interface AuthenticationPanelProps {
  selectedRole: string | null
  onRoleSelect: (roleId: string) => void
  step: "role" | "login"
  accentColor: string
  oauthError?: string
}

const ROLES = [
  { id: "personal", label: "Personal", desc: "Digital companions with memory and emotion", icon: User },
  { id: "healthcare", label: "Healthcare", desc: "HIPAA-compliant AI for patient care", icon: Stethoscope },
  { id: "business", label: "Business", desc: "Branded AI employees for enterprise", icon: Briefcase },
]

/* DEMO_CREDENTIALS removed.
 *
 * Picking a role used to immediately call authApi.login() with a hardcoded
 * demo@dreamtalk.ai / demo1234 pair that shipped in the client bundle. Anyone
 * loading /login and clicking "Personal" was handed a real, signed JWT without
 * entering a credential, and the email/password form was never reached — which
 * is why sign-in appeared to "work" while never authenticating anybody.
 *
 * Role selection now does what it says: it selects a role and advances to the
 * credential step. */

const ROLE_COLORS: Record<string, string> = {
  personal: "var(--primary)",
  healthcare: "var(--secondary)",
  business: "var(--secondary)",
}

export function AuthenticationPanel({ selectedRole, onRoleSelect, step, accentColor, oauthError: externalError }: AuthenticationPanelProps) {
  const router = useRouter()
  const timeoutRef = useRef<ReturnType<typeof setTimeout>[]>([])
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(externalError || "")
  const [showWelcome, setShowWelcome] = useState(false)
  const [welcomeStep, setWelcomeStep] = useState(0)

  // Clear all pending timeouts on unmount
  useEffect(() => () => timeoutRef.current.forEach(clearTimeout), [])

  const handleRoleSelect = (roleId: string) => {
    setError("")
    onRoleSelect(roleId)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    timeoutRef.current.forEach(clearTimeout)
    timeoutRef.current = []
    setError("")
    setLoading(true)
    try {
      const res = await authApi.login({ email, password })
      storeAuth(res.tokens)
      localStorage.setItem("user", JSON.stringify(res.user))
      triggerWelcome()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed")
    } finally {
      setLoading(false)
    }
  }

  const triggerWelcome = () => {
    setShowWelcome(true)
    setWelcomeStep(0)
    timeoutRef.current = []
    const steps = [
      () => setWelcomeStep(1),
      () => setWelcomeStep(2),
      () => setWelcomeStep(3),
      () => setWelcomeStep(4),
      () => {
        setWelcomeStep(5)
        const userStr = localStorage.getItem("user")
        const role = userStr ? JSON.parse(userStr).role : null
        timeoutRef.current.push(setTimeout(() => {
          navigateAfterAuth(router, dashboardPathForRole(role))
        }, 1200))
      },
    ]
    steps.forEach((fn, i) => { timeoutRef.current.push(setTimeout(fn, (i + 1) * 700)) })
  }

  /** Switch which role you are signing in as. Does NOT touch the credentials —
   *  it used to paste the shipped demo email/password into the form. */
  const handleRoleSwitch = (roleId: string) => {
    setError("")
    onRoleSelect(roleId)
  }

  const handleBack = () => {
    onRoleSelect("")
    setError("")
  }

  return (
    <div className="relative">
      <AnimatePresence mode="wait">
        {showWelcome ? (
          <motion.div
            key="welcome"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            className="text-center py-16"
          >
            <div className="w-20 h-20 mx-auto mb-6 rounded-full" style={{ background: `linear-gradient(135deg, color-mix(in srgb, ${accentColor} 19%, transparent), transparent)`, border: `2px solid color-mix(in srgb, ${accentColor} 25%, transparent)` }}>
              <div className="w-full h-full rounded-full flex items-center justify-center">
                <motion.div
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="w-10 h-10 rounded-full" style={{ background: accentColor, boxShadow: `0 0 20px color-mix(in srgb, ${accentColor} 31%, transparent)` }}
                />
              </div>
            </div>

            {[
              "Identity Verified",
              "Knowledge Synchronized",
              "Loading Memory",
              "Initializing Personality",
              "Entering DreamTalk...",
            ].map((text, i) => (
              <motion.div
                key={text}
                initial={{ opacity: 0, x: -20 }}
                animate={welcomeStep > i ? { opacity: 1, x: 0 } : {}}
                className="flex items-center gap-3 px-6 py-2"
              >
                <div className={`w-1.5 h-1.5 rounded-full ${welcomeStep > i ? "" : "opacity-0"}`} style={{ background: accentColor }} />
                <span className={`text-sm ${welcomeStep > i ? "text-foreground" : "text-foreground-muted"}`}>{text}</span>
              </motion.div>
            ))}

            {welcomeStep >= 4 && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-8">
                <div className="h-0.5 mx-auto w-32 rounded-full" style={{ background: `linear-gradient(90deg, ${accentColor}, transparent)`, animation: "shimmer 2s ease-in-out infinite" }} />
              </motion.div>
            )}
          </motion.div>
        ) : step === "role" ? (
          <motion.div key="role" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="space-y-5">
            <div className="text-center">
              <h2 className="text-xl font-bold text-foreground">Choose Your Role</h2>
              <p className="text-xs text-foreground-muted mt-1">Select how you&apos;ll use DreamTalk</p>
            </div>

            {error && (
              <div className="flex items-start gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20">
                <AlertTriangle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                <p className="text-xs text-red-400">{error}</p>
              </div>
            )}

            {ROLES.map((role, i) => {
              const Icon = role.icon
              const rc = ROLE_COLORS[role.id]
              const isSelected = selectedRole === role.id
              return (
                <motion.button
                  key={role.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 + i * 0.07 }}
                  onClick={() => handleRoleSelect(role.id)}
                  className={`relative w-full text-left p-4 rounded-2xl transition-all duration-300 group ${
                    isSelected ? "scale-[1.02]" : "hover:scale-[1.01]"
                  }`}
                  style={{
                    background: isSelected ? `color-mix(in srgb, ${rc} 7%, transparent)` : "var(--card)",
                    border: "1px solid",
                    borderColor: isSelected ? `color-mix(in srgb, ${rc} 31%, transparent)` : "var(--border)",
                    backdropFilter: "blur(20px)",
                  }}
                >
                  <div className="relative z-10 flex items-start gap-3">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: `color-mix(in srgb, ${rc} 9%, transparent)` }}>
                      <Icon className="h-4 w-4" style={{ color: rc }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-semibold text-foreground">{role.label}</h3>
                      <p className="text-[11px] text-foreground-muted mt-0.5">{role.desc}</p>
                    </div>
                    <ArrowRight className="h-4 w-4 text-foreground-muted group-hover:text-foreground transition-colors mt-2 shrink-0" />
                  </div>
                </motion.button>
              )
            })}

            <div className="pt-2">
              <div className="relative text-center text-[10px] text-foreground-muted mb-3">
                <span className="relative z-10 px-2" style={{ background: "var(--card)" }}>or continue with</span>
                <div className="absolute inset-x-0 top-1/2 h-px bg-foreground/[0.06]" />
              </div>
              <div className="flex gap-2">
                <button onClick={loginWithGoogle} className="flex-1 py-2.5 rounded-xl border border-foreground/[0.06] text-[11px] font-medium text-foreground-muted hover:text-foreground hover:bg-foreground/[0.04] transition-all bg-foreground/[0.04]">Google</button>
                <button onClick={loginWithGitHub} className="flex-1 py-2.5 rounded-xl border border-foreground/[0.06] text-[11px] font-medium text-foreground-muted hover:text-foreground hover:bg-foreground/[0.04] transition-all bg-foreground/[0.04]">GitHub</button>
                <button onClick={loginWithMicrosoft} className="flex-1 py-2.5 rounded-xl border border-foreground/[0.06] text-[11px] font-medium text-foreground-muted hover:text-foreground hover:bg-foreground/[0.04] transition-all bg-foreground/[0.04]">Microsoft</button>
              </div>
            </div>

            {/* Back to Home */}
            <div className="text-center pt-1">
              <Link href="/" className="text-[10px] text-foreground-muted hover:text-foreground transition-colors">← Back to Home</Link>
            </div>
          </motion.div>
        ) : (
          <motion.div key="login" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}>
            <div className="text-center">
              <button onClick={handleBack} className="text-[10px] hover:text-secondary mb-2 inline-block" style={{ color: accentColor }}>← Change role</button>
              <h2 className="text-lg font-bold text-foreground">Welcome</h2>
              <p className="text-xs text-foreground-muted">Sign in to your account</p>
            </div>

            {error && (
              <div className="flex items-start gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 mt-3">
                <AlertTriangle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                <p className="text-xs text-red-400">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-3 mt-4">
              <div className="space-y-1">
                <label className="text-xs font-medium text-foreground">Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-foreground-muted" />
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required
                    className="w-full h-11 pl-9 pr-3 rounded-[14px] bg-foreground/[0.04] border border-foreground/[0.06] text-xs text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 transition-all"
                  />
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-foreground">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-foreground-muted" />
                  <input type={showPassword ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter password" required
                    className="w-full h-11 pl-9 pr-9 rounded-[14px] bg-foreground/[0.04] border border-foreground/[0.06] text-xs text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 transition-all"
                  />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground-muted hover:text-foreground">
                    {showPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                  </button>
                </div>
              </div>

              <button type="submit" disabled={loading || !email || !password}
                className="w-full h-11 rounded-[14px] text-white text-xs font-semibold flex items-center justify-center gap-2 transition-all duration-300 disabled:opacity-50"
                style={{ background: `linear-gradient(135deg, ${accentColor}, color-mix(in srgb, ${accentColor} 80%, transparent))` }}
              >
                {loading ? (
                  <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                ) : (
                  <>Enter DreamTalk <ArrowRight className="h-3.5 w-3.5" /></>
                )}
              </button>
            </form>

            {/* Demo quick-fill */}
            <div className="mt-4 pt-3 border-t border-foreground/[0.06]">
              <p className="text-[10px] text-foreground-muted text-center mb-2">Signing in as</p>
              <div className="flex gap-2">
                {ROLES.map((role) => {
                  const rc = ROLE_COLORS[role.id]
                  return (
                    <button key={role.id} onClick={() => handleRoleSwitch(role.id)}
                      className="flex-1 py-1.5 rounded-xl border text-[10px] font-medium transition-all"
                      style={{
                        borderColor: selectedRole === role.id ? `color-mix(in srgb, ${rc} 31%, transparent)` : "var(--border)",
                        background: selectedRole === role.id ? `color-mix(in srgb, ${rc} 6%, transparent)` : "var(--surface)",
                        color: selectedRole === role.id ? rc : "var(--foreground-muted)",
                      }}
                    >
                      {role.label}
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="relative text-center text-[10px] text-foreground-muted mt-4">
              <span className="relative z-10 px-2" style={{ background: "var(--card)" }}>or continue with</span>
              <div className="absolute inset-x-0 top-1/2 h-px bg-foreground/[0.06]" />
            </div>
            <div className="flex gap-2 mt-3">
              <button onClick={loginWithGoogle} className="flex-1 py-2 rounded-xl border border-foreground/[0.06] text-[11px] font-medium text-foreground-muted hover:text-foreground hover:bg-foreground/[0.04] transition-all bg-foreground/[0.04]">Google</button>
              <button onClick={loginWithGitHub} className="flex-1 py-2 rounded-xl border border-foreground/[0.06] text-[11px] font-medium text-foreground-muted hover:text-foreground hover:bg-foreground/[0.04] transition-all bg-foreground/[0.04]">GitHub</button>
              <button onClick={loginWithMicrosoft} className="flex-1 py-2 rounded-xl border border-foreground/[0.06] text-[11px] font-medium text-foreground-muted hover:text-foreground hover:bg-foreground/[0.04] transition-all bg-foreground/[0.04]">Microsoft</button>
            </div>

            <p className="text-center text-[10px] text-foreground-muted mt-4">
              Don&apos;t have an account?{" "}<Link href="/signup" className="font-medium transition-colors" style={{ color: accentColor }}>Sign up</Link>
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
