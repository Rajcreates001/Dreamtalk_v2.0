"use client"

import { useState, useEffect } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { motion } from "motion/react"

import { BackToHome } from "@/components/ui/BackToHome"
import { AuroraBackdrop } from "@/components/hero/AuroraBackground"
import { DigitalHumanScene } from "./DigitalHumanScene"
import { AuthenticationPanel } from "./AuthenticationPanel"
import { storeAuth } from "@/lib/api"

type RoleId = "personal" | "healthcare" | "business" | null | ""

const ROLE_COLORS: Record<string, string> = {
  personal: "#CC3A63",
  healthcare: "#A2AB73",
  business: "#A2AB73",
}

const PROGRESS_STEPS = ["Choose Role", "Authenticate", "Enter DreamTalk"]

const OAUTH_ERROR_MESSAGES: Record<string, string> = {
  google_not_configured: "Google OAuth is not configured. Please use email login.",
  github_not_configured: "GitHub OAuth is not configured. Please use email login.",
  microsoft_not_configured: "Microsoft OAuth is not configured. Please use email login.",
  invalid_provider: "Invalid OAuth provider selected.",
  missing_code: "OAuth login failed - no authorization code received.",
  token_exchange_failed: "Failed to exchange OAuth credentials. Please try again.",
  missing_access_token: "OAuth login failed - no access token received.",
  auth_failed: "OAuth authentication failed. Please try again.",
}

export function LoginExperience() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [mounted, setMounted] = useState(false)

  const [selectedRole, setSelectedRole] = useState<RoleId>(null)
  const [step, setStep] = useState<"role" | "login">("role")
  const [oauthError, setOauthError] = useState("")

  // Handle OAuth redirect callbacks
  useEffect(() => {
    const error = searchParams.get("error")
    if (error) {
      setOauthError(OAUTH_ERROR_MESSAGES[error] || `OAuth error: ${error}. Please try email login instead.`)
      return
    }

    const oauthToken = searchParams.get("oauth_token")
    const oauthRefresh = searchParams.get("oauth_refresh")
    if (oauthToken && oauthRefresh) {
      storeAuth({ access_token: oauthToken, refresh_token: oauthRefresh })
      router.push("/dashboard/user")
    }
  }, [searchParams, router])

  useEffect(() => { setMounted(true) }, [])

  const handleRoleSelect = (roleId: string) => {
    setSelectedRole(roleId as RoleId)
    setStep("login")
  }

  const accentColor = selectedRole && ROLE_COLORS[selectedRole] ? ROLE_COLORS[selectedRole] : "#CC3A63"
  const progressIndex = step === "role" ? 0 : 1

  if (!mounted) {
    return (
      <main className="min-h-dvh flex bg-[#201D1D]" suppressHydrationWarning>
        <div className="flex-1 flex items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#8A8178]/30 border-t-[#CC3A63]" />
        </div>
      </main>
    )
  }

  return (
    <main className="relative min-h-dvh bg-[#201D1D] overflow-hidden flex flex-col">
      {/* ─── Aurora Background ─── */}
      <AuroraBackdrop />

      {/* ─── Back to Home ─── */}
      <BackToHome />

      {/* ─── Mobile Digital Human (lg:hidden) ─── */}
      <div className="lg:hidden relative z-10 pt-16 pb-4 flex items-center justify-center overflow-hidden">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8 }}
          className="w-full max-w-[320px]"
        >
          <DigitalHumanScene roleColor={accentColor} roleId={selectedRole} />
        </motion.div>
      </div>

      {/* ─── SPLIT LAYOUT ─── */}
      <div className="relative z-10 flex w-full flex-1">
        {/* ─── LEFT: Living Digital Human (1/2 desktop) ─── */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
          className="hidden lg:flex lg:w-1/2 relative items-center justify-center"
        >
          {/* Progress timeline - vertical */}
          <div className="absolute left-8 top-1/2 -translate-y-1/2 z-20 space-y-6">
            {PROGRESS_STEPS.map((label, i) => (
              <motion.div
                key={label}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.15 }}
                className="flex items-center gap-2"
              >
                <div className="relative flex items-center justify-center">
                  <div
                    className="w-2 h-2 rounded-full transition-all duration-500"
                    style={{
                      background: progressIndex >= i ? accentColor : "rgba(255,255,255,0.1)",
                      boxShadow: progressIndex >= i ? `0 0 8px ${accentColor}50` : "none",
                    }}
                  />
                  {i < PROGRESS_STEPS.length - 1 && (
                    <div className="absolute top-3 left-1/2 -translate-x-1/2 w-px h-6 bg-white/[0.06]" />
                  )}
                </div>
                <span
                  className="text-[10px] font-mono tracking-wider transition-all duration-500"
                  style={{ color: progressIndex >= i ? `${accentColor}CC` : "rgba(255,255,255,0.2)" }}
                >
                  {label}
                </span>
              </motion.div>
            ))}
          </div>

          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 1, delay: 0.2 }}
            className="w-full max-w-[560px]"
          >
            <DigitalHumanScene roleColor={accentColor} roleId={selectedRole} />
          </motion.div>
        </motion.div>

        {/* ─── RIGHT: Authentication Panel (1/2) ─── */}
        <motion.div
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="w-full lg:w-1/2 flex items-center justify-center px-4 sm:px-6 lg:px-10 py-8"
        >
          <div className="w-full max-w-md">
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-center mb-8"
            >
              <span className="text-xs uppercase tracking-[0.3em] text-white/20 font-mono">DreamTalk</span>
              <h1 className="text-2xl font-bold mt-2" style={{
                backgroundImage: `linear-gradient(135deg, #F3F4F4, ${accentColor}, #A2AB73)`,
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}>
                Enter the Future
              </h1>
              <p className="text-xs text-[#B0A79C] mt-1">Your Digital Twin Operating System</p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="relative rounded-[24px] p-6 sm:p-8"
              style={{
                background: "rgba(15,23,42,0.75)",
                backdropFilter: "blur(32px)",
                WebkitBackdropFilter: "blur(32px)",
                border: "1px solid",
                borderColor: selectedRole ? `${accentColor}25` : "rgba(255,255,255,0.06)",
                boxShadow: selectedRole ? `0 0 40px ${accentColor}08` : "none",
                transition: "border-color 0.5s, box-shadow 0.5s",
              }}
            >
              <div className="flex items-center justify-center gap-2 mb-6">
                {PROGRESS_STEPS.map((label, i) => (
                  <div key={label} className="flex items-center gap-2">
                    <div className="flex items-center gap-1.5">
                      <div className="w-1.5 h-1.5 rounded-full transition-all duration-300" style={{ background: progressIndex >= i ? accentColor : "rgba(255,255,255,0.1)" }} />
                      <span className="text-[8px] font-mono tracking-wider hidden sm:inline" style={{ color: progressIndex >= i ? `${accentColor}99` : "rgba(255,255,255,0.15)" }}>{label}</span>
                    </div>
                    {i < PROGRESS_STEPS.length - 1 && <div className="w-6 h-px bg-white/[0.06]" />}
                  </div>
                ))}
              </div>

              <AuthenticationPanel
                selectedRole={selectedRole}
                onRoleSelect={handleRoleSelect}
                step={step}
                accentColor={accentColor}
                oauthError={oauthError}
              />
            </motion.div>

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
              className="text-center text-[10px] text-[#8A8178] mt-6"
            >
              By continuing, you agree to DreamTalk&apos;s{" "}
              <a href="#" className="hover:text-[#F3F4F4] transition-colors" style={{ color: accentColor }}>Terms</a>
              {" "}and{" "}
              <a href="#" className="hover:text-[#F3F4F4] transition-colors" style={{ color: accentColor }}>Privacy Policy</a>
            </motion.p>
          </div>
        </motion.div>
      </div>
    </main>
  )
}
