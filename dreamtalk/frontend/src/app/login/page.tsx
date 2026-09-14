import { Suspense, type ReactNode } from "react"
import { LoginExperience } from "@/components/login/LoginExperience"

function LoadingFallback() {
  return (
    <main className="min-h-dvh flex bg-background" suppressHydrationWarning>
      <div className="flex-1 flex items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-border border-t-primary" />
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
