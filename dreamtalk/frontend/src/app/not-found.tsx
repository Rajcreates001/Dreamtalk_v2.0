import Link from "next/link"
import { ArrowLeft, Home } from "lucide-react"

export default function NotFound() {
  return (
    <main className="min-h-dvh flex flex-col items-center justify-center bg-background px-6">
      <div className="text-center space-y-6 max-w-md">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-emerald-400/20 to-blue-400/20 ring-1 ring-border">
          <span className="text-3xl font-bold text-emerald-500/50">?</span>
        </div>
        <div className="space-y-2">
          <h1 className="text-6xl font-bold tracking-tight">404</h1>
          <p className="text-lg text-muted-foreground">
            This page wandered off somewhere unknown
          </p>
        </div>
        <div className="flex items-center justify-center gap-4 pt-4">
          <Link
            href="/"
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-foreground text-background text-sm font-medium hover:opacity-90 transition-all"
          >
            <Home className="h-4 w-4" />
            Go Home
          </Link>
          <Link
            href="/conversations"
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl border border-border text-sm font-medium text-muted-foreground hover:text-foreground transition-all"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Chat
          </Link>
        </div>
      </div>
    </main>
  )
}
