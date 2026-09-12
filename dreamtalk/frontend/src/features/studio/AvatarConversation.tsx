"use client"

import { useEffect, useRef, useState } from "react"
import Link from "next/link"
import { motion } from "motion/react"
import { Loader2, Send, Sparkles, Cuboid, Video, UserPlus, TriangleAlert } from "lucide-react"
import { AvatarRenderer, type AvatarMode } from "@/components/avatar3d/AvatarRenderer"
import { useAvatarChat } from "@/services/avatar/useAvatarChat"

/**
 * The digital-human studio: the active profile speaks your replies (backend
 * talking-head + cloned voice), with a text conversation and a 2D/3D toggle.
 */
export function AvatarConversation() {
  const chat = useAvatarChat({ renderVideo: false })
  const [mode, setMode] = useState<AvatarMode>("2d")
  const [input, setInput] = useState("")
  const scroller = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" })
  }, [chat.turns.length, chat.sending])

  const submit = () => { const v = input; setInput(""); chat.send(v) }

  if (chat.loadingProfiles) {
    return <div className="grid min-h-[60vh] place-items-center text-foreground-muted"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>
  }

  if (chat.profiles.length === 0) {
    return (
      <div className="mx-auto max-w-md text-center py-20">
        <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-primary/12 text-primary"><UserPlus className="h-7 w-7" /></span>
        <h1 className="mt-5 font-display text-2xl font-bold">No digital human yet</h1>
        <p className="mt-2 text-foreground-muted">Create your twin from a photo and a voice sample, then talk to it here.</p>
        <Link href="/create-twin" className="mt-6 inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary-hover transition-all">
          <Sparkles className="h-4 w-4" /> Create your digital twin
        </Link>
      </div>
    )
  }

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      {/* Avatar stage */}
      <div className="lg:col-span-3">
        <div className="relative aspect-square w-full overflow-hidden rounded-3xl border border-border bg-surface/40">
          <AvatarRenderer mode={mode} profile={chat.activeProfile} speech={chat.speech} className="h-full w-full" interactive />
          <div className="absolute left-3 top-3 inline-flex rounded-xl border border-border bg-background/70 backdrop-blur p-1">
            {([["2d", Video, "Live"], ["3d", Cuboid, "3D"]] as const).map(([m, Icon, label]) => (
              <button key={m} onClick={() => setMode(m)}
                className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition-all ${mode === m ? "bg-primary/15 text-primary" : "text-foreground-muted hover:text-foreground"}`}>
                <Icon className="h-3.5 w-3.5" /> {label}
              </button>
            ))}
          </div>
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2">
            <span className="label-mono rounded-full border border-border bg-background/70 px-3 py-1 !text-[10px] backdrop-blur">
              {chat.activeProfile?.name ?? "Digital Human"} · {chat.sending ? "thinking…" : chat.speech ? "live" : "ready"}
            </span>
          </div>
        </div>
      </div>

      {/* Conversation */}
      <div className="lg:col-span-2 flex flex-col rounded-3xl border border-border bg-card/60 overflow-hidden">
        <div ref={scroller} className="flex-1 min-h-[300px] max-h-[52vh] overflow-y-auto p-4 space-y-3">
          {chat.turns.length === 0 && (
            <p className="text-sm text-foreground-muted">Say something — your digital human will reply in its cloned voice.</p>
          )}
          {chat.turns.map((t, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm ${t.role === "user" ? "ml-auto bg-primary/12 text-foreground" : "bg-surface/70 text-foreground"}`}>
              {t.content}
            </motion.div>
          ))}
          {chat.sending && (
            <div className="inline-flex items-center gap-2 rounded-2xl bg-surface/70 px-3.5 py-2 text-sm text-foreground-muted">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" /> generating reply…
            </div>
          )}
        </div>

        {chat.speech?.audio && chat.speech.audio.cloned === false && (
          <div className="mx-4 mb-2 flex items-start gap-2 rounded-xl border border-border bg-surface/60 p-3 text-xs text-foreground-muted">
            <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
            <span>
              Stand-in voice — your cloned voice doesn&apos;t cover this language yet
              {chat.speech.audio.engine ? ` (via ${chat.speech.audio.engine})` : ""}.
            </span>
          </div>
        )}

        {chat.error && (
          <div className="mx-4 mb-2 flex items-start gap-2 rounded-xl border border-destructive/40 bg-destructive/8 p-3 text-xs">
            <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-destructive" /> {chat.error}
          </div>
        )}

        <div className="border-t border-border-subtle p-3">
          <div className="flex items-center gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              placeholder="Speak through your digital human…"
              className="flex-1 rounded-xl border border-input bg-background px-3.5 py-2.5 text-sm text-foreground placeholder:text-foreground-muted/70 focus:outline-none focus:ring-2 focus:ring-ring/40 focus:border-primary/50 transition-all"
            />
            <button onClick={submit} disabled={!input.trim() || chat.sending}
              className="grid h-10 w-10 place-items-center rounded-xl bg-primary text-primary-foreground disabled:opacity-40 enabled:hover:bg-primary-hover transition-all">
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AvatarConversation
