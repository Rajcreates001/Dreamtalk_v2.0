"use client"

import { useState } from "react"
import { useTheme } from "next-themes"
import { Sun, Moon, Sparkles, Layers, Fingerprint, Mic, Video, Brain } from "lucide-react"
import { useIsHydrated } from "@/hooks/useReducedMotion"
import {
  AuroraField,
  GlassPanel,
  MagneticButton,
  NeoButton,
  NeoSegmented,
  NeoToggle,
  Parallax,
  ScrollReveal,
  Spotlight,
  TiltCard,
} from "@/components/depth"

/**
 * Living reference for the depth system.
 *
 * Not decoration — this is where the light/dark parity of every primitive gets
 * checked side by side. If something looks wrong here it is wrong everywhere,
 * because every surface in the app draws from these same tokens.
 */
export default function DesignSystemPage() {
  const { resolvedTheme, setTheme } = useTheme()
  const [notify, setNotify] = useState(true)
  const [mode, setMode] = useState<"2d" | "3d">("3d")

  // The server cannot know the visitor's theme, so `resolvedTheme` is undefined
  // during SSR and the first client render. Branching on it before hydration
  // makes the markup disagree with the server's and React throws the tree away.
  const hydrated = useIsHydrated()
  const isDark = hydrated && resolvedTheme === "dark"

  return (
    <main className="relative min-h-dvh px-6 py-16 md:px-12">
      <AuroraField intensity={2} />

      {/* ── Header ─────────────────────────────────────────────── */}
      <header className="mx-auto mb-16 flex max-w-6xl items-center justify-between">
        <div>
          <p className="text-sm font-medium tracking-widest text-primary uppercase">
            DreamTalk
          </p>
          <h1 className="font-[family-name:var(--font-display)] text-4xl font-bold tracking-tight text-foreground md:text-5xl">
            Depth system
          </h1>
          <p className="mt-2 max-w-xl text-foreground-muted">
            Glass, neumorphism, elevation and 3D — three depth languages kept to
            separate jobs. Toggle the theme; every surface below is defined
            independently for light and dark.
          </p>
        </div>
        <NeoButton
          aria-label={`Switch to ${isDark ? "light" : "dark"} mode`}
          onClick={() => setTheme(isDark ? "light" : "dark")}
          className="rounded-full !px-4"
        >
          {/* Both icons are rendered and cross-faded, so the markup is identical
              on the server and the client and only opacity differs. */}
          <span className="relative block size-5">
            <Sun
              className={`absolute inset-0 size-5 transition-opacity duration-200 ${isDark ? "opacity-100" : "opacity-0"}`}
            />
            <Moon
              className={`absolute inset-0 size-5 transition-opacity duration-200 ${isDark ? "opacity-0" : "opacity-100"}`}
            />
          </span>
        </NeoButton>
      </header>

      <div className="mx-auto max-w-6xl space-y-24">
        {/* ── Glass ────────────────────────────────────────────── */}
        <Section
          title="Glass"
          blurb="For chrome that floats above content. Needs something behind it to refract — over a flat background it is just a grey box."
        >
          <div className="grid gap-5 md:grid-cols-3">
            {(["subtle", "default", "strong"] as const).map((tone) => (
              <GlassPanel key={tone} tone={tone} className="p-6">
                <p className="text-xs font-semibold uppercase tracking-wider text-primary">
                  {tone}
                </p>
                <p className="mt-2 text-sm text-foreground">
                  Blur, saturation boost, specular rim, inner shadow and an outer
                  drop shadow. Skipping any one is why most glass reads flat.
                </p>
              </GlassPanel>
            ))}
          </div>
        </Section>

        {/* ── Neumorphism ──────────────────────────────────────── */}
        <Section
          title="Neumorphism"
          blurb="Tactile controls carved from the page. Restricted to press/toggle/pick — soft UI on text surfaces is the classic contrast failure, so each control keeps a real border, a colour signal and a focus ring."
        >
          <div className="neo grid gap-8 p-8 md:grid-cols-2">
            <div className="space-y-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                Buttons
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <NeoButton size="sm">Small</NeoButton>
                <NeoButton>
                  <Sparkles className="size-4" /> Generate
                </NeoButton>
                <NeoButton variant="accent" size="lg">
                  Create twin
                </NeoButton>
              </div>
              <p className="text-xs text-foreground-muted">
                Raised at rest, carved in on press. Try keyboard focus — the ring
                survives.
              </p>
            </div>

            <div className="space-y-5">
              <div>
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                  Toggle
                </p>
                <NeoToggle
                  checked={notify}
                  onCheckedChange={setNotify}
                  label="Email me when rendering finishes"
                  showLabel
                />
              </div>
              <div>
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                  Segmented (arrow keys work)
                </p>
                <NeoSegmented
                  label="Avatar mode"
                  value={mode}
                  onValueChange={setMode}
                  options={[
                    { value: "2d", label: "2D", icon: <Video className="size-4" /> },
                    { value: "3d", label: "3D", icon: <Layers className="size-4" /> },
                  ]}
                />
              </div>
            </div>
          </div>
        </Section>

        {/* ── 3D ───────────────────────────────────────────────── */}
        <Section
          title="3D response"
          blurb="Cards that tilt toward the cursor, with children lifted off the face for real parallax. Disabled for touch and reduced-motion, where they render flat and still."
        >
          <div className="grid gap-6 md:grid-cols-3">
            {[
              { icon: Fingerprint, title: "Your face", body: "FLAME mesh fitted from one photo, with baked identity texture." },
              { icon: Mic, title: "Your voice", body: "Cloned from a short sample. Verified to 0.3% pitch error." },
              { icon: Brain, title: "Your mind", body: "Conversation memory persisted across sessions." },
            ].map(({ icon: Icon, title, body }) => (
              <TiltCard key={title} className="h-full">
                <div className="glass glass-rim h-full rounded-2xl p-7">
                  <div className="layer-pop-sm">
                    <Icon className="size-8 text-primary" />
                  </div>
                  <h3 className="layer-pop mt-5 font-[family-name:var(--font-display)] text-xl font-semibold text-foreground">
                    {title}
                  </h3>
                  <p className="layer-pop-sm mt-2 text-sm text-foreground-muted">{body}</p>
                </div>
              </TiltCard>
            ))}
          </div>
        </Section>

        {/* ── Spotlight ────────────────────────────────────────── */}
        <Section
          title="Spotlight"
          blurb="A cursor-tracked light over a surface, lighting the fill and the border rim together. Purely decorative, so it is skipped on touch with no fallback needed."
        >
          <div className="grid gap-6 md:grid-cols-2">
            {["Self-hosted, always", "22 Indian languages"].map((t) => (
              <Spotlight key={t} className="rounded-2xl border border-border bg-card p-8 shadow-elev-2">
                <h3 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-foreground">
                  {t}
                </h3>
                <p className="mt-2 text-sm text-foreground-muted">
                  Move the cursor across this card.
                </p>
              </Spotlight>
            ))}
          </div>
        </Section>

        {/* ── Elevation ────────────────────────────────────────── */}
        <Section
          title="Elevation"
          blurb="Ordinary cards. Warm-tinted shadows rather than neutral black, so they sit inside the cream/charcoal palette instead of on top of it."
        >
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {/* Written out rather than interpolated — Tailwind extracts class
                names statically, so `shadow-elev-${n}` would emit nothing. */}
            {[
              { cls: "shadow-elev-1", name: "elev-1", use: "hairline" },
              { cls: "shadow-elev-2", name: "elev-2", use: "resting card" },
              { cls: "shadow-elev-3", name: "elev-3", use: "raised / hover" },
              { cls: "shadow-elev-4", name: "elev-4", use: "modal" },
            ].map(({ cls, name, use }) => (
              <div
                key={name}
                className={`rounded-2xl border border-border bg-card p-6 ${cls}`}
              >
                <p className="font-mono text-sm text-foreground">{name}</p>
                <p className="mt-1 text-xs text-foreground-muted">{use}</p>
              </div>
            ))}
          </div>
        </Section>

        {/* ── Motion ───────────────────────────────────────────── */}
        <Section
          title="Scroll motion"
          blurb="GSAP ScrollTrigger — one shared scroll listener for the whole page rather than an observer per element. Reduced motion lands content at its final state, never stranded at opacity 0."
        >
          <ScrollReveal stagger={0.09} className="grid gap-4 sm:grid-cols-3">
            {["Staggered", "on scroll", "with GSAP"].map((t) => (
              <div key={t} className="rounded-2xl border border-border bg-card p-8 text-center shadow-elev-2">
                <p className="font-[family-name:var(--font-display)] text-lg font-semibold text-foreground">
                  {t}
                </p>
              </div>
            ))}
          </ScrollReveal>

          <div className="relative mt-8 overflow-hidden rounded-2xl border border-border p-12">
            <Parallax speed={14} className="absolute inset-0 -z-10">
              <div className="size-full bg-[radial-gradient(60%_60%_at_50%_40%,var(--glow-primary),transparent_70%)]" />
            </Parallax>
            <p className="text-center text-sm text-foreground-muted">
              Background layer drifting against the scroll — decorative only,
              never text.
            </p>
          </div>

          <div className="mt-10 flex justify-center">
            <MagneticButton className="glass glass-rim rounded-full px-8 font-medium text-foreground">
              <Sparkles className="size-4 text-primary" />
              Magnetic call to action
            </MagneticButton>
          </div>
        </Section>
      </div>
    </main>
  )
}

function Section({
  title,
  blurb,
  children,
}: {
  title: string
  blurb: string
  children: React.ReactNode
}) {
  return (
    <section>
      <ScrollReveal>
        <h2 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-foreground">
          {title}
        </h2>
        <p className="mb-7 mt-1.5 max-w-2xl text-sm text-foreground-muted">{blurb}</p>
      </ScrollReveal>
      {children}
    </section>
  )
}
