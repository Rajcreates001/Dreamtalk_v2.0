import { Suspense, type ReactNode } from "react"
import { LoginExperience } from "@/components/login/LoginExperience"

function LoadingFallback() {
  return (
    <main className="min-h-dvh flex bg-[#070B14]" suppressHydrationWarning>
      <div className="flex-1 flex items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#64748B]/30 border-t-[#7C5CFF]" />
      </div>
    </main>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <LoginExperience />
    </Suspense>
  )
}
