"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import {
  Cuboid, Loader2, Send, Sparkles, UserPlus, Video, TriangleAlert,
  Mic, Gauge, Languages, Clapperboard, CheckCircle2, CircleSlash,
} from "lucide-react"
import { AvatarRenderer, type AvatarMode } from "@/components/avatar3d/AvatarRenderer"
import { useAvatarChat } from "@/services/avatar/useAvatarChat"
import { avatarRuntime } from "@/services/avatar/client"
import type { LanguagesResponse } from "@/services/avatar/types"

/* ──────────────────────────────────────────────────────────────
   Live Digital Human.

   Replaces a page that rendered `VRMAvatar` hardcoded to
   /models/utsuwa.vrm — a stock anime model with no connection to the
   signed-in user's avatar at all. It showed a generic head, had no 2D/3D
   switching, and its Start button opened a session against an avatar the
   user had never created.

   This is wired to the real runtime:
     - the user's own profile (2D talking head / 3D FLAME mesh)
     - their cloned voice, with the language actually driving which engine
       runs, because the clone only covers Indic languages today
     - lip-sync video behind an explicit toggle, since rendering it is the
       expensive path
     - measured latency and clone/stand-in state surfaced rather than hidden
   ────────────────────────────────────────────────────────────── */

export default function LivePage() {
  // renderVideo is state, not a constant: the old studio hardcoded `false`,
  // which is why the 2D avatar never actually moved its mouth.
  const [renderVideo, setRenderVideo] = useState(false)
  const chat = useAvatarChat({ renderVideo })

  const [mode, setMode] = useState<AvatarMode>("2d")
  const [language, setLanguage] = useState("auto")
  const [langs, setLangs] = useState<LanguagesResponse | null>(null)
  const [input, setInput] = useState("")
  const scroller = useRef<HTMLDivElement>(null)

  useEffect(() => {
    avatarRuntime.languages().then(setLangs).catch(() => setLangs(null))
  }, [])

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" })
  }, [chat.turns.length, chat.sending])

  const profile = chat.activeProfile
  const caps = profile?.appearance?.capabilities
  const can3D = !!(profile?.appearance?.glb_url && caps?.browser_glb)
  const blendshapes = profile?.appearance?.blendshape_names?.length ?? 0

  /** Languages the clone engine genuinely covers, so the picker can say so
   *  instead of letting the user discover a stand-in voice after waiting. */
  const cloneLangs = useMemo(
    () => new Set(Object.keys(langs?.voice_clone_languages ?? {})),
    [langs],
  )

  const lastAudio = chat.speech?.audio
  const usedClone = lastAudio?.cloned === true
  const processingMs = chat.speech?.processing_ms

  const submit = () => {
    const v = input.trim()
    if (!v) return
    setInput("")
    chat.send(v, language)
  }

  if (chat.loadingProfiles) {
    return (
      <div className="grid min-h-[60vh] place-items-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    )
  }

  if (chat.profiles.length === 0) {
    return (
      <div className="mx-auto max-w-md py-20 text-center">
        <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-primary/12 text-primary">
          <UserPlus className="h-7 w-7" />
        </span>
        <h1 className="mt-5 font-display text-2xl font-bold text-foreground">No digital human yet</h1>
        <p className="mt-2 text-foreground-muted">
          Build your twin from a photo and a short voice sample, then talk to it live here.
        </p>
        <Link
          href="/create-twin"
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition-all hover:bg-primary-hover"
        >
          <Sparkles className="h-4 w-4" /> Create your digital twin
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* ── Header ─────────────────────────────────────────────── */}
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="label-mono">Live</p>
          <h1 className="font-display text-2xl font-bold text-foreground">
            {profile?.name ?? "Digital Human"}
          </h1>
          <p className="mt-1 text-sm text-foreground-muted">
            Speaks in its cloned voice, with lip-sync driven off the audio clock.
          </p>
        </div>

        {chat.profiles.length > 1 && (
          <select
            aria-label="Active digital human"
            value={chat.activeId ?? ""}
            onChange={(e) => chat.setActiveId(e.target.value)}
            className="rounded-xl border border-border bg-card px-3 py-2 text-sm text-foreground"
          >
            {chat.profiles.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        )}
      </header>

      <div className="grid gap-5 lg:grid-cols-5">
        {/* ── Avatar stage ─────────────────────────────────────── */}
        <section className="lg:col-span-3">
          <div className="relative aspect-square w-full overflow-hidden rounded-3xl border border-border bg-surface/40">
            <AvatarRenderer
              mode={mode}
              profile={profile}
              speech={chat.speech}
              className="h-full w-full"
              interactive
            />

            {/* 2D / 3D switch. 3D is disabled rather than hidden when the
                profile has no GLB, so the reason is visible. */}
            <div className="absolute left-3 top-3 inline-flex rounded-xl border border-border bg-background/70 p-1 backdrop-blur">
              {([["2d", Video, "Live"], ["3d", Cuboid, "3D"]] as const).map(([m, Icon, label]) => {
                const disabled = m === "3d" && !can3D
                return (
                  <button
                    key={m}
                    onClick={() => !disabled && setMode(m)}
                    disabled={disabled}
                    title={disabled ? "This twin has no 3D head yet" : undefined}
                    className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition-all disabled:cursor-not-allowed disabled:opacity-40 ${
                      mode === m ? "bg-primary/15 text-primary" : "text-foreground-muted hover:text-foreground"
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" /> {label}
                  </button>
                )
              })}
            </div>

            <div className="absolute bottom-3 left-1/2 -translate-x-1/2">
              <span className="label-mono rounded-full border border-border bg-background/70 px-3 py-1 !text-[10px] backdrop-blur">
                {profile?.name ?? "Digital Human"} ·{" "}
                {chat.sending ? "thinking…" : chat.speech ? "live" : "ready"}
              </span>
            </div>
          </div>

          {/* Real capability chips, read from the profile manifest. */}
          <div className="mt-3 flex flex-wrap gap-2">
            <Chip ok={!!caps?.talkinghead_2d} icon={Video} label="2D talking head" />
            <Chip ok={can3D} icon={Cuboid} label="3D head" />
            <Chip ok={blendshapes > 0} icon={Sparkles} label={`${blendshapes} blendshapes`} />
            {/* voice.engine arrives through an index signature, so it is not
                statically a string — coerce rather than assert. */}
            <Chip
              ok={!!profile?.voice?.ready}
              icon={Mic}
              label={typeof profile?.voice?.engine === "string" ? profile.voice.engine : "voice"}
            />
          </div>
        </section>

        {/* ── Controls + conversation ──────────────────────────── */}
        <section className="lg:col-span-2 flex flex-col gap-3">
          {/* Language: this is what decides whether the real clone runs. */}
          <div className="rounded-2xl border border-border bg-card/60 p-3">
            <label className="label-mono flex items-center gap-1.5 !text-[10px]">
              <Languages className="h-3 w-3" /> Reply language
            </label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="mt-2 w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground"
            >
              <option value="auto">Auto-detect</option>
              {Object.entries(langs?.languages ?? {}).map(([code, name]) => (
                <option key={code} value={code}>
                  {name}{cloneLangs.has(code) ? " — cloned voice" : " — stand-in voice"}
                </option>
              ))}
            </select>
            {language !== "auto" && !cloneLangs.has(language) && (
              <p className="mt-2 flex items-start gap-1.5 text-[11px] text-warning">
                <TriangleAlert className="mt-0.5 h-3 w-3 shrink-0" />
                The clone engine does not cover this language, so the reply uses a
                clearly-labelled stand-in voice.
              </p>
            )}
          </div>

          {/* Lip-sync video: expensive, so it is opt-in and says so. */}
          <label className="flex items-start gap-3 rounded-2xl border border-border bg-card/60 p-3">
            <input
              type="checkbox"
              checked={renderVideo}
              onChange={(e) => setRenderVideo(e.target.checked)}
              className="mt-0.5 h-4 w-4 accent-[var(--primary)]"
            />
            <span>
              <span className="flex items-center gap-1.5 text-sm font-medium text-foreground">
                <Clapperboard className="h-3.5 w-3.5" /> Render lip-sync video
              </span>
              <span className="mt-0.5 block text-[11px] text-foreground-muted">
                Animates the 2D face with MuseTalk. Much slower — leave off for
                quick text replies.
              </span>
            </span>
          </label>

          {/* Transcript */}
          <div className="flex min-h-[240px] flex-1 flex-col overflow-hidden rounded-2xl border border-border bg-card/60">
            <div ref={scroller} className="max-h-[38vh] flex-1 space-y-3 overflow-y-auto p-4">
              {chat.turns.length === 0 && (
                <p className="text-sm text-foreground-muted">
                  Say something — your digital human replies in its cloned voice.
                </p>
              )}
              {chat.turns.map((t, i) => (
                <div
                  key={i}
                  className={`max-w-[92%] rounded-2xl px-3 py-2 text-sm ${
                    t.role === "user"
                      ? "ml-auto bg-primary/12 text-foreground"
                      : "bg-surface text-foreground"
                  }`}
                >
                  {t.content}
                </div>
              ))}
              {chat.sending && (
                <p className="flex items-center gap-2 text-sm text-foreground-muted">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> generating reply…
                </p>
              )}
              {chat.error && (
                <p className="flex items-start gap-1.5 text-sm text-destructive">
                  <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {chat.error}
                </p>
              )}
            </div>

            {/* Honest state for the last reply, rather than implying the clone
                always ran. */}
            {chat.speech && (
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-border px-4 py-2 text-[11px] text-foreground-muted">
                <span className="inline-flex items-center gap-1">
                  {usedClone
                    ? <><CheckCircle2 className="h-3 w-3 text-success" /> cloned voice</>
                    : <><CircleSlash className="h-3 w-3 text-warning" /> stand-in voice</>}
                </span>
                {lastAudio?.engine && <span>engine: {lastAudio.engine}</span>}
                {typeof processingMs === "number" && (
                  <span className="inline-flex items-center gap-1">
                    <Gauge className="h-3 w-3" /> {(processingMs / 1000).toFixed(1)}s
                  </span>
                )}
                {lastAudio?.fallback_reason && (
                  <span className="w-full text-warning">{lastAudio.fallback_reason}</span>
                )}
              </div>
            )}

            <div className="flex items-center gap-2 border-t border-border p-3">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit() } }}
                placeholder="Speak through your digital human…"
                aria-label="Message"
                className="flex-1 rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-1 focus:ring-primary/40"
              />
              <button
                onClick={submit}
                disabled={chat.sending || !input.trim()}
                aria-label="Send message"
                className="grid h-10 w-10 place-items-center rounded-xl bg-primary text-primary-foreground transition-all hover:bg-primary-hover disabled:opacity-40"
              >
                {chat.sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

function Chip({ ok, icon: Icon, label }: { ok: boolean; icon: typeof Video; label: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] ${
        ok
          ? "border-success/30 bg-success/10 text-success"
          : "border-border bg-surface text-foreground-muted"
      }`}
    >
      <Icon className="h-3 w-3" /> {label}
    </span>
  )
}
