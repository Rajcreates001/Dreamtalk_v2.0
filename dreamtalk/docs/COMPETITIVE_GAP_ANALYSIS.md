# DreamTalk vs the market — what's missing, and what we have that they don't

_2026-09-13. Competitor capabilities from public 2026 comparisons; DreamTalk
figures are **measured on this stack**, not claimed._

---

## 1. Honest scorecard

| | **DreamTalk** | HeyGen | D-ID | Synthesia |
| --- | --- | --- | --- | --- |
| Languages | **23** (11 with cloned voice) | 175+ | ~100 | 140+ |
| Real-time interactive | ❌ (WS endpoint exists, unproven) | ✅ Streaming Avatar API | ✅ **WebRTC <200 ms** | ❌ |
| Reply latency | **16–23 s** text · **123–300 s** with video | seconds | **sub-200 ms** | minutes |
| Voice cloning | ✅ IndicF5, verified 0.3 % pitch error | ✅ | ✅ | ✅ |
| Real 3D head (browser mesh) | ✅ **GLB + 10 blendshapes** | ❌ video only | ❌ video only | ❌ video only |
| Conversational memory | ✅ persisted to Postgres | ❌ stateless | partial (agents) | ❌ |
| Gestures / body | ❌ head only | ✅ | ✅ | ✅ gesture control |
| Emotion control | ✅ 12, prosody measured | limited | limited | ✅ |
| Self-hosted / data residency | ✅ **fully** | ❌ SaaS | ❌ SaaS | ❌ SaaS |
| Per-minute cost | **none** | per-credit | per-minute | per-minute |

---

## 2. Where we genuinely win

These are not marketing lines — they're structural and the incumbents can't
easily match them.

1. **Fully self-hosted.** Nothing leaves the customer's infrastructure. For
   Indian healthcare, BFSI and government, that is often a hard procurement
   requirement that disqualifies all three competitors outright.
2. **No per-minute economics.** They meter minutes; we meter GPU we already own.
   At volume this inverts the cost model.
3. **A real 3D head, not a video.** We ship a GLB with 10 morph targets the
   browser animates at zero marginal cost. HeyGen/D-ID/Synthesia all return
   *video* — they cannot be turned, relit, or embedded in a 3D scene.
4. **Indian-language depth over breadth.** 175 languages sounds better than 23
   until you need Bodo or Santali. We carry all 22 scheduled languages, with
   true cloned voice in 11.
5. **Persistent memory.** The twin remembers across sessions (verified: recalled
   a fact with an empty history array, and again in a fresh browser). The others
   are largely stateless generators.

---

## 3. Where we are genuinely behind

Ordered by how much they cost us.

### 3.1 Latency — the one that matters

D-ID does **sub-200 ms** over WebRTC. We do **16–23 s** for a text reply and
**123–300 s** with rendered video. That is not "slower", it is a different
product category: they can hold a conversation, we can answer a question.

Measured causes, in order:
- IndicF5 runs on **CPU** (`device: cpu` in `/status`) — dominates the text path.
- MuseTalk needs ~6.5 GB VRAM and contends with Ollama's 5.3 GB on an 8 GB card.
- A dead primary LLM endpoint used to add ~60 s/reply (fixed — circuit breaker).

**What would close it, and what I found trying:**

I attempted the IndicF5-on-GPU move and it is **not** a compose flag. The
service already selects CUDA when it can see a device, but
`docker/Dockerfile.indicf5` builds on `python:3.11-slim` and installs torch
from the `/whl/cpu` index — the image ships **`torch 2.5.1+cpu`** and cannot
use a GPU at all. Verified inside the container:

```
torch 2.5.1+cpu | cuda available: False | device count: 0
/dev/nvidia*    : none
```

So it needs a CUDA runtime base image, cu124 wheels (~2.5 GB rebuild), and
~2 GB of VRAM budgeted against MuseTalk's ~6.5 GB on this 8 GB card. Worth
doing, but it is an infrastructure change with a real memory tradeoff, not a
one-line fix. I left the compose file documenting the requirement rather than
adding a `gpus:` key that silently does nothing.

Beyond that: a streaming TTS that emits audio in chunks rather than whole
utterances, and driving the existing `/api/v1/avatar/ws/realtime` socket so the
3D head speaks from the viseme track as audio arrives — the 3D path needs no
server-side render, so it can be genuinely interactive long before the 2D path
can.

### 3.2 The 3D head is bald

FLAME is a face model. The last open gap from the quality audit. Teeth and
tongue are now solved; hair is the remaining thing that makes it read as a
mannequin.

### 3.3 No gestures or body

All three competitors animate shoulders and hands. We render a floating head.
LivePortrait is already wired and could drive upper-body motion from a driving
video.

### 3.4 Language breadth

23 vs 140–175. Indic-Mio closes the *cloned-voice* half of this (11 → 22);
matching 175 means a different TTS strategy.

---

## 4. What to do, in order

1. **IndicF5 on GPU** — biggest single latency win. NOT a config flag: needs a
   CUDA base image + cu124 wheels in `Dockerfile.indicf5` (see §3.1).
2. **Deploy Indic-Mio** — cloned English + all 22 languages. Compose service
   definitions already exist and have never been run.
3. **Make the WebSocket path real** — stream audio chunks + visemes to the 3D
   head. This is the credible route to conversational latency *without*
   matching D-ID's video pipeline.
4. **Hair** — closes the last audit gap.
5. **Upper-body via LivePortrait** — already integrated, unused for this.

**Positioning, honestly:** we should not sell against HeyGen on realism or
against D-ID on latency today. The defensible pitch is *"your digital twin,
on your own infrastructure, in your own Indian language, that remembers you"* —
and every clause of that is now measured and true.
