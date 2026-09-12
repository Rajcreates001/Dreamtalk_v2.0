"use client"

import { useState, useRef, useEffect } from "react"
import { motion, AnimatePresence } from "motion/react"
import { User, Stethoscope, Briefcase, Mail, Lock, Eye, EyeOff, AlertTriangle, ArrowRight, Sparkles, Check } from "lucide-react"
import { authApi, storeAuth, loginWithGoogle, loginWithGitHub, loginWithMicrosoft } from "@/lib/api"
import { navigateAfterAuth, dashboardPathForRole } from "@/lib/navigate"
import { useRouter } from "next/navigation"
import Link from "next/link"

type Step = "role" | "account" | "security" | "welcome"

const ROLES = [
  { id: "personal", label: "Personal", desc: "Create your own Digital Human companion", icon: User, color: "#CC3A63", benefits: ["Preserve memories", "AI Companion", "Build relationships"] },
  { id: "healthcare", label: "Healthcare", desc: "Digital Doctors for patient care", icon: Stethoscope, color: "#A2AB73", benefits: ["Medical Knowledge", "Patient Support", "HIPAA Ready"] },
  { id: "business", label: "Business", desc: "Branded AI employees for enterprise", icon: Briefcase, color: "#A2AB73", benefits: ["Sales & Support", "HR Automation", "Enterprise Ready"] },
]

const STEP_LABELS = ["Identity", "Account", "Security", "Welcome"]

export function SignupWizard() {
  const router = useRouter()
  const timeoutRef = useRef<ReturnType<typeof setTimeout>[]>([])
  const [step, setStep] = useState<Step>("role")
  const [selectedRole, setSelectedRole] = useState("personal")
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [welcomeStep, setWelcomeStep] = useState(0)
  const [showWelcome, setShowWelcome] = useState(false)
  const [acceptedTerms, setAcceptedTerms] = useState(false)

  // Cleanup timeouts on unmount
  useEffect(() => () => timeoutRef.current.forEach(clearTimeout), [])

  const accentColor = ROLES.find(r => r.id === selectedRole)?.color || "#CC3A63"

  // Password strength calculation
  const getStrength = (pwd: string): { score: number; label: string; color: string } => {
    let score = 0
    if (pwd.length >= 8) score++
    if (pwd.length >= 12) score++
    if (/[A-Z]/.test(pwd)) score++
    if (/[a-z]/.test(pwd)) score++
    if (/[0-9]/.test(pwd)) score++
    if (/[^A-Za-z0-9]/.test(pwd)) score++
    if (score <= 2) return { score: Math.min(score, 4), label: "Weak", color: "#D84C63" }
    if (score <= 4) return { score: Math.min(score, 4), label: "Good", color: "#D6A44C" }
    if (score <= 5) return { score: Math.min(score, 4), label: "Strong", color: "#A2AB73" }
    return { score: 4, label: "Very Strong", color: "#8F9A5E" }
  }

  const strength = getStrength(password)

  const handleRoleSelect = (roleId: string) => {
    setSelectedRole(roleId)
    setStep("account")
  }

  const handleAccountNext = () => {
    if (!name || !email || !password) return
    if (password.length < 8) { setError("Password must be at least 8 characters"); return }
    setError("")
    setStep("security")
  }

  const handleSubmit = async () => {
    if (password !== confirmPassword) { setError("Passwords do not match"); return }
    if (!acceptedTerms) { setError("Please accept the terms and conditions"); return }
    setError("")
    setLoading(true)
    try {
      const res = await authApi.signup({ email, password, full_name: name, role: selectedRole })
      storeAuth(res.tokens)
      localStorage.setItem("user", JSON.stringify(res.user))
      setLoading(false)
      triggerWelcome()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Signup failed")
      setLoading(false)
    }
  }

  const triggerWelcome = () => {
    setStep("welcome")
    setShowWelcome(true)
    setWelcomeStep(0)
    timeoutRef.current = []
    const steps = [
      () => setWelcomeStep(1), // Identity Created
      () => setWelcomeStep(2), // Digital Human Initializing
      () => setWelcomeStep(3), // Knowledge Engine Ready
      () => setWelcomeStep(4), // Memory Engine Ready
      () => {
        setWelcomeStep(5) // Welcome to DreamTalk
        const userStr = localStorage.getItem("user")
        const role = userStr ? JSON.parse(userStr).role : null
        timeoutRef.current.push(setTimeout(() => {
          navigateAfterAuth(router, dashboardPathForRole(role))
        }, 1500))
      },
    ]
    steps.forEach((fn, i) => { timeoutRef.current.push(setTimeout(fn, (i + 1) * 700)) })
  }

  const stepIndex = STEP_LABELS.indexOf(
    step === "role" ? "Identity" :
    step === "account" ? "Account" :
    step === "security" ? "Security" : "Welcome"
  )

  return (
    <div className="w-full">
      {/* Progress timeline */}
      <div className="flex items-center justify-center gap-2 mb-8">
        {STEP_LABELS.map((label, i) => (
          <div key={label} className="flex items-center gap-2">
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full transition-all duration-400`} style={{ background: i <= stepIndex ? accentColor : "rgba(255,255,255,0.1)" }} />
              <span className="text-[9px] font-mono tracking-wider hidden sm:inline" style={{ color: i <= stepIndex ? `${accentColor}CC` : "rgba(255,255,255,0.15)" }}>{label}</span>
            </div>
            {i < STEP_LABELS.length - 1 && <div className="w-8 h-px" style={{ background: i < stepIndex ? accentColor : "rgba(255,255,255,0.06)" }} />}
          </div>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {step === "welcome" ? (
          /* ── WELCOME SEQUENCE ── */
          <motion.div key="welcome" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} className="text-center py-10">
            <div className="w-20 h-20 mx-auto mb-6 rounded-full flex items-center justify-center" style={{ background: `linear-gradient(135deg, ${accentColor}30, transparent)`, border: `2px solid ${accentColor}40` }}>
              <motion.div animate={{ scale: [1, 1.1, 1] }} transition={{ duration: 2, repeat: Infinity }} className="w-10 h-10 rounded-full" style={{ background: accentColor, boxShadow: `0 0 20px ${accentColor}50` }} />
            </div>
            <h2 className="text-xl font-bold text-foreground mb-6">Creating Your Digital Twin</h2>
            {["Identity Created", "Digital Human Initializing", "Knowledge Engine Ready", "Memory Engine Ready", "Welcome to DreamTalk"].map((text, i) => (
              <motion.div key={text} initial={{ opacity: 0, x: -20 }} animate={welcomeStep > i ? { opacity: 1, x: 0 } : {}} className="flex items-center gap-3 px-6 py-2">
                <div className={`w-1.5 h-1.5 rounded-full ${welcomeStep > i ? "" : "opacity-0"}`} style={{ background: accentColor }} />
                <span className={`text-sm ${welcomeStep > i ? "text-foreground" : "text-foreground-muted"}`}>{text}</span>
              </motion.div>
            ))}
            {welcomeStep >= 4 && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-6">
                <div className="h-0.5 mx-auto w-40 rounded-full" style={{ background: `linear-gradient(90deg, ${accentColor}, transparent)`, animation: "shimmer 2s ease-in-out infinite" }} />
              </motion.div>
            )}
          </motion.div>
        ) : (
          <motion.div key={step} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.3 }}>
            {/* ── ERROR ── */}
            {error && (
              <div className="flex items-start gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 mb-4">
                <AlertTriangle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                <p className="text-xs text-red-400">{error}</p>
              </div>
            )}

            {step === "role" && (
              /* ── STEP 1: ROLE SELECTION ── */
              <div className="space-y-4">
                <div className="text-center mb-4">
                  <h2 className="text-lg font-bold text-foreground">Choose Your Identity</h2>
                  <p className="text-xs text-foreground-muted mt-1">Select how you'll use DreamTalk</p>
                </div>
                {ROLES.map((role, i) => {
                  const Icon = role.icon
                  const isSelected = selectedRole === role.id
                  const rc = role.color
                  return (
                    <motion.button
                      key={role.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.1 + i * 0.08 }}
                      onClick={() => handleRoleSelect(role.id)}
                      className="relative w-full text-left p-4 rounded-2xl transition-all duration-300 group"
                      style={{
                        background: isSelected ? `${rc}15` : "var(--card)",
                        border: "1px solid",
                        borderColor: isSelected ? `${rc}50` : "rgba(255,255,255,0.06)",
                        backdropFilter: "blur(20px)",
                      }}
                    >
                      <div className="relative z-10 flex items-start gap-3">
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: `${rc}18` }}>
                          <Icon className="h-4 w-4" style={{ color: rc }} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="text-sm font-semibold text-foreground">{role.label}</h3>
                          <p className="text-[11px] text-foreground-muted mt-0.5">{role.desc}</p>
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {role.benefits.map((b) => (
                              <span key={b} className="text-[9px] px-1.5 py-0.5 rounded-md" style={{ background: `${rc}12`, color: rc }}>{b}</span>
                            ))}
                          </div>
                        </div>
                        <ArrowRight className="h-4 w-4 mt-2 shrink-0" style={{ color: isSelected ? rc : "#8A8178" }} />
                      </div>
                    </motion.button>
                  )
                })}

                {/* Back to Home */}
                <div className="text-center pt-1">
                  <Link href="/" className="text-[10px] text-foreground-muted hover:text-foreground transition-colors">← Back to Home</Link>
                </div>
              </div>
            )}

            {step === "account" && (
              /* ── STEP 2: ACCOUNT INFO ── */
              <div className="space-y-4">
                <div className="text-center mb-2">
                  <h2 className="text-lg font-bold text-foreground">Your Information</h2>
                  <p className="text-xs text-foreground-muted mt-1">Tell us about yourself</p>
                </div>
                <div className="grid sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-foreground">Full Name</label>
                    <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="John Doe" required
                      className="w-full h-11 px-3 rounded-[14px] bg-foreground/[0.04] border border-foreground/[0.06] text-xs text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 transition-all"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-foreground">Email</label>
                    <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" required
                      className="w-full h-11 px-3 rounded-[14px] bg-foreground/[0.04] border border-foreground/[0.06] text-xs text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 transition-all"
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-foreground">Password</label>
                  <div className="relative">
                    <input type={showPassword ? "text" : "password"} value={password} onChange={e => setPassword(e.target.value)} placeholder="Create a strong password" required minLength={8}
                      className="w-full h-11 pl-3 pr-9 rounded-[14px] bg-foreground/[0.04] border border-foreground/[0.06] text-xs text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 transition-all"
                    />
                    <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground-muted hover:text-foreground">
                      {showPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                    </button>
                  </div>
                  {/* Password strength meter */}
                  {password && (
                    <div className="mt-2 space-y-1.5">
                      <div className="flex gap-1">
                        {[0, 1, 2, 3].map((i) => (
                          <div key={i} className="flex-1 h-1 rounded-full transition-all duration-300" style={{ background: i < strength.score ? strength.color : "rgba(255,255,255,0.06)" }} />
                        ))}
                      </div>
                      <p className="text-[10px]" style={{ color: strength.color }}>{strength.label}</p>
                    </div>
                  )}
                </div>
                <button onClick={handleAccountNext} disabled={!name || !email || !password}
                  className="w-full h-11 rounded-[14px] text-white text-xs font-semibold flex items-center justify-center gap-2 transition-all duration-300 disabled:opacity-50"
                  style={{ background: `linear-gradient(135deg, ${accentColor}, ${accentColor}CC)` }}
                >
                  Continue <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            )}

            {step === "security" && (
              /* ── STEP 3: SECURITY ── */
              <div className="space-y-4">
                <div className="text-center mb-2">
                  <h2 className="text-lg font-bold text-foreground">Secure Your Account</h2>
                  <p className="text-xs text-foreground-muted mt-1">One last step before creating your Digital Twin</p>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-foreground">Confirm Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-foreground-muted" />
                    <input type={showConfirm ? "text" : "password"} value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} placeholder="Re-enter your password" required
                      className="w-full h-11 pl-9 pr-9 rounded-[14px] bg-foreground/[0.04] border border-foreground/[0.06] text-xs text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 transition-all"
                    />
                    <button type="button" onClick={() => setShowConfirm(!showConfirm)} className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground-muted hover:text-foreground">
                      {showConfirm ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                    </button>
                  </div>
                  {confirmPassword && (
                    <p className="text-[10px] flex items-center gap-1" style={{ color: password === confirmPassword ? "#A2AB73" : "#D84C63" }}>
                      <Check className="h-2.5 w-2.5" /> {password === confirmPassword ? "Passwords match" : "Passwords do not match"}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <input type="checkbox" id="terms" checked={acceptedTerms} onChange={e => setAcceptedTerms(e.target.checked)} className="rounded border-foreground/[0.06] bg-foreground/[0.04] accent-[#CC3A63]" />
                  <label htmlFor="terms" className="text-[11px] text-foreground-muted cursor-pointer">I accept the <a href="#" className="hover:text-foreground transition-colors" style={{ color: accentColor }}>Terms</a> and <a href="#" className="hover:text-foreground transition-colors" style={{ color: accentColor }}>Privacy Policy</a></label>
                </div>
                <div className="flex gap-3 pt-1">
                  <button onClick={() => setStep("account")} className="flex-1 h-11 rounded-[14px] bg-foreground/[0.04] border border-foreground/[0.06] text-xs font-medium text-foreground-muted hover:text-foreground transition-all">Back</button>
                  <button onClick={handleSubmit} disabled={loading || !confirmPassword || !acceptedTerms}
                    className="flex-[2] h-11 rounded-[14px] text-white text-xs font-semibold flex items-center justify-center gap-2 transition-all duration-300 disabled:opacity-50"
                    style={{ background: `linear-gradient(135deg, ${accentColor}, ${accentColor}CC)` }}
                  >
                    {loading ? (
                      <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    ) : (
                      <>Create My Digital Twin <Sparkles className="h-3.5 w-3.5" /></>
                    )}
                  </button>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Back to role selector */}
      {(step === "account" || step === "security") && (
        <button onClick={() => { setStep("role"); setError("") }} className="text-center w-full mt-4 text-[10px] text-foreground-muted hover:text-foreground transition-colors">← Change role</button>
      )}

      {/* OAuth section */}
      {step !== "welcome" && (
        <div className="mt-4">
          <div className="relative text-center text-[10px] text-foreground-muted mb-3">
            <span className="relative z-10 px-2" style={{ background: "#2C2929" }}>or sign up with</span>
            <div className="absolute inset-x-0 top-1/2 h-px bg-foreground/[0.06]" />
          </div>
          <div className="grid grid-cols-3 gap-2">
            <button onClick={loginWithGoogle} className="py-2.5 rounded-xl border border-foreground/[0.06] text-[11px] font-medium text-foreground-muted hover:text-foreground hover:bg-foreground/[0.04] transition-all bg-foreground/[0.04]">Google</button>
            <button onClick={loginWithGitHub} className="py-2.5 rounded-xl border border-foreground/[0.06] text-[11px] font-medium text-foreground-muted hover:text-foreground hover:bg-foreground/[0.04] transition-all bg-foreground/[0.04]">GitHub</button>
            <button onClick={loginWithMicrosoft} className="py-2.5 rounded-xl border border-foreground/[0.06] text-[11px] font-medium text-foreground-muted hover:text-foreground hover:bg-foreground/[0.04] transition-all bg-foreground/[0.04]">Microsoft</button>
          </div>
        </div>
      )}

      {/* Sign in link */}
      {step !== "welcome" && (
        <p className="text-center text-[10px] text-foreground-muted mt-4 pt-4 border-t border-foreground/[0.06]">
          Already have an account?{" "}<Link href="/login" className="font-medium transition-colors" style={{ color: accentColor }}>Sign in</Link>
        </p>
      )}
    </div>
  )
}
