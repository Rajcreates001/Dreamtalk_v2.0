import { Suspense } from "react"
import { SignupExperience } from "@/components/signup/SignupExperience"

function LoadingFallback() {
  return (
    <main className="min-h-dvh flex bg-background" suppressHydrationWarning>
      <div className="flex-1 flex items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#8A8178]/30 border-t-[#CC3A63]" />
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
