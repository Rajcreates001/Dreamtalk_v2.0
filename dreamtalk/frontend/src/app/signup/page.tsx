import { Suspense } from "react"
import { SignupExperience } from "@/components/signup/SignupExperience"

function LoadingFallback() {
  return (
    <main className="min-h-dvh flex bg-[#070B14]" suppressHydrationWarning>
      <div className="flex-1 flex items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#64748B]/30 border-t-[#7C5CFF]" />
      </div>
    </main>
  )
}

export default function SignupPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <SignupExperience />
    </Suspense>
  )
}
