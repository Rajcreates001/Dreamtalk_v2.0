# DreamTalk Frontend — Analysis & 3D Avatar Implementation Plan

_Written after auditing the frontend against Codex's new `/api/v1/avatar` runtime._

---

## 0. The headline finding

**Codex has shipped a complete real-time digital-human backend. The frontend
consumes none of it.**

`avatar_runtime` + `two_d_avatar` + `cloned_speech` now provide:

| Capability | Endpoint / field |
| --- | --- |
| Avatar profiles (create from photo+voice) | `POST/GET /api/v1/avatar/profiles` |
| Render manifest | `GET /profiles/{id}/manifest` |
| Converse (text) | `POST /profiles/{id}/respond` |
| Converse (audio in) | `POST /profiles/{id}/respond/audio` |
| Realtime stream | `WS /api/v1/avatar/ws/realtime` |
| Languages / status | `GET /languages`, `GET /status` |
| Signed media | `GET /assets/{path}?expires&signature` |

And `respond` returns exactly what a digital human needs:

```jsonc
{
  "text": "…",                 // LLM reply
  "language": { … },
  "emotion": "…",
  "audio_url": "…",            // cloned voice (IndicF5)
  "lipsync": { "duration": 3.4, "keyframes": [ … ] },   // ← VISEME TRACK
  "lipsync_duration": 3.4
}
```

Plus `two_d_avatar.py` renders a **MuseTalk MP4 of the user's actual photo
speaking**, with real lip-sync.

**Grep result: zero references to `profiles`, `lipsync`, `ws/realtime` or
`respond` anywhere in `src/`.** The frontend is now the bottleneck, not the
backend.

---

## 1. What's wrong with the frontend today

### 1.1 The avatar is an architectural dead end (most important)

`public/models/angelica.glb` is a **stock Sketchfab head**:

- **No morph targets, no skeleton** (verified: `max morph targets per prim: 0`,
  `skins: 0`). It is *physically incapable* of consuming the backend's
  `lipsync.keyframes`. This is why the lip-sync attempt produced a pink block —
  I was scaling an inner-mouth mesh because there was nothing else to drive.
- **It isn't anyone's twin.** The product promise is "your face, your voice."
  The hero currently shows a generic woman regardless of who signed up.
- Secondary issues (blank eyes, 4.7 MB, heavy) are symptoms of forcing a
  decorative asset to do a product job.

**Conclusion: the current 3D avatar cannot become the product. It must be
replaced by a rig that supports visemes, or by the 2D talking head.**

### 1.2 Performance

- One WebGL canvas rendering **every frame, permanently** while the hero is on
  screen (even when nothing is animating between blinks).
- **17** `Section3D` wrappers, each with a scroll-linked `useScroll` +
  transform chain firing on every scroll frame.
- Always-on CSS animations (aurora blobs with `blur()`, orbiting rings,
  particle fields) across ~16 sections, running even off-screen.
- Nothing uses `content-visibility`, so the browser lays out and paints all
  ~21 000 px of page height continuously.

### 1.3 Product surface vs. marketing surface

The landing page is **16 heavy marketing sections**, while the surfaces that
*are* the product are thin:

- `/studio` — no avatar-runtime wiring at all.
- `/create-twin` — drives the older `digital-twins` engine, not the new
  `avatar/profiles` runtime.
- No avatar library, no conversation UI bound to `respond`.

We are spending the performance budget and the design effort on the brochure,
not the app.

### 1.4 Design system

Tokens/typography are in good shape. Remaining: a few sections are still
dark-tuned in light mode, and the marketing sections repeat the same
card-in-a-glow pattern 16 times, which reads as one long texture rather than a
narrative.

---

## 2. The decision to make first: how do we represent the avatar?

| Tier | What it is | Identity fidelity | Lip-sync | Cost | Ready? |
| --- | --- | --- | --- | --- | --- |
| **A. 2D talking head** | Backend MuseTalk MP4 of the user's photo | **Exact** (it *is* their face) | **Real** (MuseTalk) | Low FE cost, server render | **Backend ready now** |
| **B. Rigged 3D** | GLB/VRM with ARKit blendshapes, driven by `lipsync.keyframes` | Generic/stylised face | **Real** (viseme-driven) | Cheap, interactive, real-time | Needs a rigged asset |
| **C. Photoreal 3D twin** | 3D reconstruction from the photo | Exact | Real | Research-grade | Not soon |

**Recommendation: build A and B behind one interface, ship A as the default.**

- **A** is the product promise and the backend already renders it.
- **B** gives the interactive, free-view, zero-latency idle state (turn, blink,
  look at cursor) that a video can't, and is the right "live" state between
  utterances.
- Do **not** invest further in the current stock GLB. Swap it for a rigged
  avatar (Ready Player Me exports with `ARKit` + `Oculus Visemes` morph targets
  are free, ~3 MB, male/female, and drop straight into the existing loader).

---

## 3. Implementation plan

### Phase 0 — Bind the frontend to the real runtime _(foundation)_

Add a typed client + hooks for `/api/v1/avatar`:

```
src/services/avatar/
  client.ts     profiles, manifest, respond, respondAudio, languages, status
  types.ts      AvatarProfile, RespondResult, LipsyncTrack, Viseme
  useAvatarProfile.ts / useAvatarChat.ts / useRealtimeAvatar.ts (WS)
```

Deliverable: `respond()` returns `{ text, audioUrl, lipsync, emotion }` typed.
Nothing renders yet — this unblocks everything else.

### Phase 1 — The avatar renderer abstraction + 2D player

```tsx
<AvatarRenderer mode="2d" | "3d" profile={…} speech={…} />
```

- `TalkingHeadVideo` — plays the MuseTalk MP4 / or photo+audio, with a still
  poster frame as the idle state.
- **Audio clock is the source of truth.** Drive everything from
  `audio.currentTime` (`requestAnimationFrame` loop), **never `setTimeout`**.
- States: `idle → thinking → speaking → idle`, with a crossfade so the switch
  from poster to video isn't jarring.

This alone makes the hero and studio show *the user's real twin speaking*.

### Phase 2 — Rigged 3D avatar with real visemes

- Replace `angelica.glb` with a **rigged GLB** (ARKit blendshapes + visemes).
- `VisemeDriver`: map `lipsync.keyframes` → morph target influences, sampled at
  `audio.currentTime`, with smoothing between keyframes.
- `ExpressionDriver`: map `emotion` → blendshape blend (happy/sad/thoughtful).
- Idle rig: blink (`eyeBlink*`), saccades, breathing, cursor look-at — all of
  which the current mesh can't do because it has no blendshapes.
- Keep horizontal-only orbit (already implemented), vertical locked.

### Phase 3 — Make the product surfaces real

- **Studio** (`/studio`) becomes the primary app: avatar stage + conversation
  panel + language/emotion controls, bound to `respond`/`ws/realtime`.
- **Create-twin** migrates from `digital-twins` to `avatar/profiles` so the
  thing you create is the thing the studio runs.
- **Avatar library** from `GET /profiles`.

### Phase 4 — Performance pass

1. `content-visibility: auto` + `contain-intrinsic-size` on marketing sections
   (biggest single win on a 21 000 px page).
2. **One WebGL canvas policy** — a single shared canvas; sections request it.
3. `frameloop="demand"` + `invalidate()` only while speaking/dragging/blinking,
   so an idle avatar costs ~0 GPU.
4. Pause off-screen CSS animations (`animation-play-state` via IntersectionObserver).
5. Cut `Section3D` from 17 → the 4–5 sections where it actually reads.

### Phase 5 — Design tightening

- Collapse 16 marketing sections → ~8 with a real narrative
  (You → Face → Voice → Mind → Twin → Languages → Privacy → CTA).
- Light/dark parity audit on the remaining dark-tuned sections.
- Replace the repeated "card in a glow" motif with 2–3 distinct section
  layouts so the page has rhythm.

---

## 4. Suggested order

1. **Phase 0** (client/types) — small, unblocks all.
2. **Phase 1** (2D talking head) — biggest product leap; uses what Codex built.
3. **Phase 4.1–4.3** (perf) — fixes the "10 fps" complaint properly.
4. **Phase 2** (rigged 3D) — once a rigged asset is chosen.
5. **Phase 3** (studio) → **Phase 5** (design).

## 5. Open questions for the team

1. **Avatar asset**: OK to drop the stock angelica model and use a rigged
   avatar (Ready Player Me style) for the 3D tier?
2. **Default mode**: 2D talking head as the product default, 3D as the
   interactive idle — agreed?
3. **Auth**: the runtime is auth-gated; should the marketing hero show a demo
   profile, or a non-personalised 3D idle avatar?
