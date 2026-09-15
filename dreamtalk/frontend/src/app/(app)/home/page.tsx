"use client"

import { useCallback, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { motion } from "motion/react"
import Link from "next/link"
import {
  Mic, Boxes, Clapperboard, Plus, Loader2, Check, X, Radio,
  Cpu, AlertTriangle, ChevronRight,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { authApi } from "@/lib/api"
import { avatarRuntime, assetUrl } from "@/services/avatar/client"
import type { AvatarProfile, RuntimeStatus } from "@/services/avatar/types"

/* ═══════════════════════════════════════════════════════════════════
 * The dashboard used to list `digital_twins`, a parallel table whose rows
 * are all status="draft" and carry no voice, mesh or texture. The avatars
 * that actually exist — the ones with a cloned voice and a rigged GLB —
 * live in `avatar_profiles` and are served by /api/v1/avatar/*. Nothing
 * joins the two tables, so a user who had successfully built an avatar
 * still saw an empty, perpetually-draft dashboard.
 *
 * This page reads the runtime that owns the real data, and reports each
 * capability from the asset that backs it rather than from a status string.
 * ═══════════════════════════════════════════════════════════════════ */

type Capability = { label: string; ready: boolean; detail: string }

/** Derive what a profile can actually do from the assets it really has. */
function capabilities(p: AvatarProfile): Capability[] {
  const voice = p.voice ?? {}
  const look = p.appearance ?? {}
  const caps = look.capabilities ?? {}
  const shapes = look.blendshape_names ?? []

  /* The runtime does not publish a top-level `is_cloned`. What it publishes
   * is the result of its own clone-and-listen check, and that is the only
   * field that answers "does this avatar speak in its own voice". Reading
   * anything else here reports a working clone as missing. */
  const cloned = voice.ready === true && voice.validation?.cloned === true
  const clonedIn = voice.validated_language ?? voice.validation?.language
  const has3d = Boolean(look.glb_url)
  const has2d = caps.talkinghead_2d === true && Boolean(look.primary_image_url)

  return [
    {
      label: "Voice clone",
      ready: cloned,
      /* Coverage comes from the runtime, never from comparing languages here.
       *
       * This used to infer "sample_language is outside clone coverage" from
       * sample_language !== validated_language. That inference held while
       * IndicF5 covered 11 languages and validated Hindi for an English
       * sample. Indic-Mio now clones all 23 including English, and the card
       * still told users their English was a stand-in — while the runtime
       * was cloning it. The backend publishes
       * sample_language_supported_by_clone against the CURRENT engine; that
       * is the only thing that can be right after an engine change. */
      detail: cloned
        ? `verified${clonedIn ? ` in ${clonedIn}` : ""}${
            voice.sample_language &&
            voice.sample_language_supported_by_clone === false
              ? `; ${voice.sample_language} is outside clone coverage and uses a stand-in`
              : ""
          }`
        : "no cloned voice, replies use a stand-in",
    },
    {
      label: "3D avatar",
      ready: has3d,
      detail: has3d
        ? `rigged head, ${shapes.length} morph target${shapes.length === 1 ? "" : "s"}`
        : "no GLB mesh was built",
    },
    {
      label: "2D lip-sync",
      ready: has2d,
      detail: has2d ? "photo-real talking head" : "no source photo for 2D rendering",
    },
  ]
}

function initialsOf(name: string) {
  const w = name.trim().split(/\s+/)
  return ((w.length > 1 ? w[0][0] + w[1][0] : name.slice(0, 2)) || "AV").toUpperCase()
}

export default function HomePage() {
  const router = useRouter()
  const [greeting, setGreeting] = useState("Hello")
  const [userName, setUserName] = useState<string | null>(null)
  const [profiles, setProfiles] = useState<AvatarProfile[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [status, setStatus] = useState<RuntimeStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activating, setActivating] = useState<string | null>(null)

  useEffect(() => {
    const h = new Date().getHours()
    setGreeting(h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening")

    let alive = true
    void (async () => {
      try {
        const me = await authApi.me()
        if (alive) setUserName(me?.full_name || me?.name || me?.email || null)
      } catch {
        const stored = localStorage.getItem("user")
        if (stored && alive) {
          try { setUserName(JSON.parse(stored).full_name ?? null) } catch {}
        }
      }

      try {
        const r = await avatarRuntime.listProfiles()
        if (!alive) return
        setProfiles(r.profiles ?? [])
        setActiveId(r.active_profile_id ?? r.profiles?.[0]?.id ?? null)
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : "Could not reach the avatar runtime")
      } finally {
        if (alive) setLoading(false)
      }

      // Health is informational: a failure here must not blank the page.
      try {
        const s = await avatarRuntime.status()
        if (alive) setStatus(s)
      } catch { /* the strip simply stays hidden */ }
    })()
    return () => { alive = false }
  }, [])

  /* Activation is server-side state, so /live and every other surface agree
   * on which avatar is live. Navigate only once the server has confirmed. */
  const talkTo = useCallback(async (id: string) => {
    setActivating(id)
    try {
      await avatarRuntime.activate(id)
      setActiveId(id)
    } catch { /* /live falls back to the first profile */ }
    router.push("/live")
  }, [router])

  const health = (() => {
    if (!status) return null
    const hw = (status.hardware ?? {}) as Record<string, unknown>
    const vc = (status.voice_cloning ?? {}) as Record<string, unknown>
    const a2d = (status.avatar_2d ?? {}) as Record<string, unknown>
    const gpu = (hw.devices as Array<{ name?: string }> | undefined)?.[0]
    return [
      { label: "GPU", ok: Boolean(hw.cuda_available), text: gpu?.name ?? "CPU only" },
      { label: "Voice cloning", ok: Boolean(vc.available), text: vc.engine ? String(vc.engine) : "unavailable" },
      { label: "2D renderer", ok: Boolean(a2d.ready), text: a2d.preferred_engine ? String(a2d.preferred_engine) : "unavailable" },
    ]
  })()

  const fleet = status?.profiles as { total?: number; ready?: number } | undefined

  return (
    <div className="mx-auto w-full max-w-5xl px-5 py-8 sm:px-8 sm:py-12">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
          {greeting}{userName ? `, ${userName.split(" ")[0]}` : ""}
        </h1>
        <p className="mt-1 text-sm text-foreground-muted">
          Your avatars, their voices, and the engines that drive them.
        </p>
      </header>

      {health && (
        <div className="mb-8 flex flex-wrap gap-2">
          {health.map((h) => (
            <span
              key={h.label}
              className="glass-subtle inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs"
            >
              <span
                aria-hidden
                className={cn("h-1.5 w-1.5 rounded-full", h.ok ? "bg-secondary" : "bg-destructive")}
              />
              <span className="font-medium">{h.label}</span>
              <span className="text-foreground-muted">{h.text}</span>
            </span>
          ))}
        </div>
      )}

      <section aria-labelledby="avatars-heading">
        <div className="mb-4 flex items-center justify-between">
          <h2 id="avatars-heading" className="text-sm font-semibold tracking-[0.12em] uppercase text-foreground-muted">
            Your avatars {profiles.length > 0 && `(${profiles.length})`}
          </h2>
          {profiles.length > 0 && (
            <Link
              href="/create"
              className="neo-pressable inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium"
            >
              <Plus className="h-4 w-4" aria-hidden /> New avatar
            </Link>
          )}
        </div>

        {loading && (
          <div className="glass flex items-center gap-3 rounded-2xl p-8 text-sm text-foreground-muted">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Loading your avatars…
          </div>
        )}

        {!loading && error && (
          <div className="glass flex items-start gap-3 rounded-2xl p-6">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" aria-hidden />
            <div>
              <p className="text-sm font-medium">The avatar runtime did not respond</p>
              <p className="mt-1 text-sm text-foreground-muted">{error}</p>
            </div>
          </div>
        )}

        {!loading && !error && profiles.length === 0 && (
          <div className="glass rounded-2xl p-8 text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-secondary">
              <Plus className="h-6 w-6 text-white" aria-hidden />
            </div>
            <p className="text-base font-semibold">You have not built an avatar yet</p>
            <p className="mx-auto mt-2 max-w-md text-sm text-foreground-muted">
              One photo and about thirty seconds of speech is enough. DreamTalk builds a rigged
              3D head, a photo-real 2D talking head, and a clone of your voice.
            </p>
            <Link
              href="/create"
              className="mt-5 inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white"
            >
              Build my avatar <ChevronRight className="h-4 w-4" aria-hidden />
            </Link>
          </div>
        )}

        <ul className="grid gap-4 sm:grid-cols-2">
          {profiles.map((p, i) => {
            const caps = capabilities(p)
            const thumb = assetUrl(p.appearance?.primary_image_url)
            const live = p.id === activeId
            const busy = activating === p.id
            return (
              <motion.li
                key={p.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, delay: Math.min(i, 5) * 0.04 }}
                className={cn("glass layer-pop-sm rounded-2xl p-5", live && "glass-rim")}
              >
                <div className="flex items-start gap-4">
                  {thumb ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                      src={thumb}
                      alt=""
                      width={56}
                      height={56}
                      className="h-14 w-14 shrink-0 rounded-xl object-cover"
                    />
                  ) : (
                    <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-secondary text-sm font-bold text-white">
                      {initialsOf(p.name)}
                    </div>
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="truncate font-semibold">{p.name}</h3>
                      {live && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-secondary/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-secondary">
                          <Radio className="h-3 w-3" aria-hidden /> Active
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 text-xs text-foreground-muted">
                      {String(p.status ?? "unknown")}
                    </p>
                  </div>
                </div>

                <ul className="mt-4 space-y-1.5">
                  {caps.map((c) => (
                    <li key={c.label} className="flex items-start gap-2 text-xs">
                      {c.ready
                        ? <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-secondary" aria-hidden />
                        : <X className="mt-0.5 h-3.5 w-3.5 shrink-0 text-foreground-muted" aria-hidden />}
                      <span className={cn(c.ready ? "font-medium" : "text-foreground-muted")}>
                        {c.label}
                      </span>
                      <span className="text-foreground-muted">— {c.detail}</span>
                    </li>
                  ))}
                </ul>

                <div className="mt-5 flex gap-2">
                  <button
                    type="button"
                    onClick={() => talkTo(p.id)}
                    disabled={busy}
                    className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                  >
                    {busy
                      ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                      : <Clapperboard className="h-4 w-4" aria-hidden />}
                    Talk
                  </button>
                  <Link
                    href="/voice-cloning"
                    className="neo-pressable inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-medium"
                  >
                    <Mic className="h-4 w-4" aria-hidden /> Voice
                  </Link>
                </div>
              </motion.li>
            )
          })}
        </ul>
      </section>

      <section aria-labelledby="do-heading" className="mt-10">
        <h2 id="do-heading" className="mb-4 text-sm font-semibold tracking-[0.12em] uppercase text-foreground-muted">
          What you can do
        </h2>
        <div className="grid gap-3 sm:grid-cols-3">
          {[
            { href: "/live", label: "Talk to your avatar", desc: "2D and 3D, with your cloned voice", icon: Clapperboard },
            { href: "/voice-cloning", label: "Voice cloning", desc: "Record or upload a new sample", icon: Mic },
            { href: "/create", label: "Build an avatar", desc: "Photo plus voice, one pass", icon: Boxes },
          ].map(({ href, label, desc, icon: Icon }) => (
            <Link key={href} href={href} className="glass layer-pop-sm group rounded-2xl p-5">
              <Icon className="mb-3 h-5 w-5 text-primary" aria-hidden />
              <p className="font-semibold">{label}</p>
              <p className="mt-1 text-xs text-foreground-muted">{desc}</p>
            </Link>
          ))}
        </div>
      </section>

      {status && (
        <p className="mt-10 flex items-center gap-2 text-xs text-foreground-muted">
          <Cpu className="h-3.5 w-3.5" aria-hidden />
          Runtime {String(status.status ?? "unknown")}
          {typeof fleet?.ready === "number" &&
            ` — ${fleet.ready} of ${fleet.total} avatars ready across the deployment`}
        </p>
      )}
    </div>
  )
}
