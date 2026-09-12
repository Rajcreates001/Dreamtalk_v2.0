# DreamTalk — Design Upgrade Plan

_From studying gsap.com, spline.design, bklit.com and manus.im (2026-09-13)._

> `manus.in` is a parked GoDaddy domain — I used **manus.im**, the AI agent
> product, which is almost certainly what you meant.

---

## What each reference actually teaches us

| Site | The one idea worth stealing |
| --- | --- |
| **gsap.com** | Motion as a *system*, not per-component hacks. Character-level text reveals, scroll as choreography. |
| **spline.design** | The hero **is** a 3D scene with depth — grid floor, floating bodies, glossy materials — not an object in a box. |
| **bklit.com** | A committed "design-engineered" blueprint layer: crosshair grid, ruler gutters, mono labels with a trailing `_`. |
| **manus.im** | **Prompt-first, chrome-last.** The product's core action is the entire hero. No marketing scaffolding. |

The two dark-technical references (GSAP, Bklit) and the two product references
(Spline, Manus) pull in different directions. DreamTalk should take **motion +
depth** from the first pair and **restraint** from the second.

---

## 1. GSAP is now free — and it solves a problem we already have

GSAP's entire toolset (ScrollTrigger, SplitText, MorphSVG, DrawSVG, Flip,
Observer, Inertia, CustomEase) went **free for everyone** under Webflow. There
is no longer a licensing reason to hand-roll this.

**The problem it solves.** The landing page currently wraps 17 sections in
`Section3D`, each running its own `useScroll` + four `useTransform` chains on
every scroll frame — this is the measured cause of the "10 fps" feel. That is
17 independent subscriptions doing work the browser has to reconcile.

ScrollTrigger runs **one** ticker for all of them, batches reads/writes, and
kills off-screen work automatically.

```
npm i gsap @gsap/react
```

| Where | Change |
| --- | --- |
| `components/motion/Section3D.tsx` | Replace `useScroll/useTransform` with a single `ScrollTrigger` per section, registered through `useGSAP()` |
| `components/hero/CinematicText.tsx` | `SplitText` char-level reveal for "The Operating System / for Digital Humans" — this is the exact effect on gsap.com's own hero |
| Avatar showcase | `ScrollTrigger` **pin** — hold the avatar while copy scrolls past it, instead of 17 separate tilt/swing/rise/zoom variants |
| `PremiumFAQ`, `MetricsCounter` | `Flip` for layout transitions; ScrollTrigger `once: true` counters |

**Keep `motion` (framer) for component-level enter/exit** — it's better at
that. Use GSAP for scroll choreography. They coexist fine.

---

## 2. Spline: make the hero a scene, not a portrait in a box

Today `DigitalChamber` renders the avatar inside a `max-w-[620px] aspect-square`
with a radial glow behind it. Spline's hero has **depth**: a perspective grid
floor receding to the horizon, soft-bodied objects floating at different Z,
glossy gradient materials, and a character standing *in* the space.

We already have React Three Fiber — we don't need Spline the tool, we need the
look. Concretely, in `GLBAvatar`/`TwinHead3D`:

1. **Grid floor.** drei's `<Grid>` with fade, or a shader plane. Instantly
   reads as "3D space" rather than "cut-out PNG".
2. **Depth cueing.** A few low-poly rounded forms at varied Z with slow
   drift, blurred by distance. Spline's magenta/blue/green bodies against near
   black — ours become the Astra palette (`#CC3A63`, `#A2AB73`, `#853953`).
3. **Contact shadow.** drei `<ContactShadows>` under the bust. This single
   addition does more for "it exists in a room" than any lighting change.
4. **Glossy material pass.** Spline's objects read as soft plastic: high
   roughness gradient + a subtle env map. We disabled metalness to fix the
   black-avatar bug; an `<Environment preset="city">` restores specular life
   without reintroducing it.

**Cost control:** all of the above is one extra draw pass. Keep the existing
off-screen `frameloop` pause and the dpr cap.

---

## 3. Bklit: a blueprint layer that suits a "Digital Twin OS"

Bklit's aesthetic is *engineering drawing* — and it fits a product that claims
to be an operating system far better than the current "card in a glow" motif
repeated 16 times.

Borrowable, cheaply, in `SectionWrapper`:

- **Crosshair grid.** A `background-image` of 1px lines at ~180px with small
  `+` marks at intersections, at ~4% opacity. Pure CSS, zero JS.
- **Ruler gutter.** Fixed left column with tick marks and numbers that count
  page depth. Bklit shows `200 / 400 / 600 / 800`.
- **Mono labels with a blinking `_`.** We already have `label-mono`; add the
  trailing underscore cursor — `DIGITAL HUMAN — LIVE_`.
- **Hatch-filled cells.** Diagonal stripe fills on a few grid cells to break
  the flatness.

**Also practical:** Bklit is a genuine chart library (area, candlestick,
sankey, gauge, heatmap, radar). `/dashboard/analytics` currently has no real
charting. This is a direct, free fit.

---

## 4. Manus: the honest one — our hero is doing too much

Manus's entire landing hero is **one input box** on warm off-white, with
suggestion chips and a quiet line: *"Less structure, more intelligence."* No
illustration. No stats bar. No 16 sections.

DreamTalk's hero currently carries: badge, two-line headline, paragraph, two
CTAs, a 4-metric stat row, a 3D avatar, and a status pill — then **sixteen**
marketing sections follow.

**The strongest single change available: make the hero the product.**

```
        Say something to your digital human
   ┌──────────────────────────────────────────────┐
   │  Type a message…                        [→]  │
   └──────────────────────────────────────────────┘
     [ Namaste ]  [ Tell me about yourself ]  [ हिन्दी में बात करो ]
```

Type → a real avatar answers in a cloned voice with real lip-sync. That
demonstrates everything the 16 sections *describe*. We already have `/talk`
working; the hero is a trimmed instance of it against a demo profile.

This also fixes the "is it real?" problem no amount of copy solves.

---

## 5. Suggested order

1. **GSAP ScrollTrigger migration** — biggest perf win, fixes a measured defect.
2. **Prompt-first hero** — biggest product win, uses what already works.
3. **Spline depth pass** (grid + contact shadows + env map) — biggest "premium" win.
4. **Bklit blueprint layer** — cheap, distinctive, CSS-only.
5. **Bklit charts** in `/dashboard/analytics`.
6. Collapse 16 marketing sections → ~8 once the hero carries the demo.

---

## 6. What I would *not* copy

- **Spline's saturated primary palette** — ours is warm and specific
  (pink/olive/burgundy). Borrow the depth, not the colours.
- **Manus's light minimalism wholesale** — a digital-human product needs to
  show a face. Take the prompt-first idea, keep our dark cinematic stage.
- **Bklit's near-monochrome** — the blueprint layer should sit *under* our
  palette at low opacity, not replace it.
