# Evaluation: HeyGem · ComfyUI · OmniVoice · Handy

_2026-09-14. All four repos cloned and inspected locally. Licence findings are
read from the repo's own LICENSE file and, where weights ship separately, from
the model host — not from the project's marketing copy._

**Headline: one is unusable, one is genuinely useful but licence-blocked on its
weights, one is usable with a caveat, one is the wrong shape.**

| Repo | Code licence | Weights licence | Free for commercial DreamTalk? | Verdict |
|---|---|---|---|---|
| **HeyGem** | Silicon Intelligence Community Licence | closed (opaque Docker images) | **No** — hard gate at 1,000 MAU | **Reject** |
| **ComfyUI** | GPL-3.0 | n/a (you supply models) | **Yes**, if run as a separate service | **Adopt, narrowly** |
| **OmniVoice** | Apache-2.0 | **CC-BY-NC** | **No** for the shipped weights | **Best tech fit, blocked** |
| **Handy** | MIT | model-dependent | Yes | **Reference only** |

---

## 1. HeyGem — reject

### Not free in any sense that matters to us

`LICENSE` is not an OSS licence. Section 2, *Additional Commercial Terms*:

> "If ... the monthly active users of the products or services made available by
> or for Licensee ... is greater than 1 thousand monthly active users in the
> preceding calendar month ... you must request a license from Silicon
> Intelligence, which Silicon Intelligence may grant to you in its sole
> discretion, and you are not authorized to exercise any of the rights under
> this Agreement unless or until Silicon Intelligence otherwise expressly grants
> you such rights."

**One thousand** monthly active users. For scale, the Llama licence — widely
considered restrictive — gates at 700 **million**. A 1,000-MAU ceiling is below
a successful pilot with a single enterprise customer. It also carries a NOTICE
attribution requirement and a patent-retaliation termination clause.

### There is no model source in the repo

I checked. The repository contains **zero Python files**:

```
src/main  src/preload  src/renderer      ← an Electron desktop app
```

Everything that actually does the work ships as prebuilt, opaque images:

```
guiji2025/heygem.ai          ← the digital-human engine
guiji2025/fish-speech-ziming ← TTS
guiji2025/fun-asr            ← ASR
```

So this is a closed binary product with an open front-end. We could not
inspect it, patch it, fine-tune it, or port it to Indic languages even if the
licence allowed it. That is the opposite of DreamTalk's self-hosted,
inspectable posture.

### It does not support our languages

Per its own README: *"Scripts support eight languages — English, Japanese,
Korean, Chinese, French, German, Arabic, and Spanish."* **Zero Indic
languages.** Our entire differentiator is the 22 scheduled languages.

### It does not fit our hardware

README minimum: **32 GB RAM, RTX 4070, 100 GB free disk, ~70 GB download.** We
develop on an RTX 4060 Laptop with 8 GB VRAM that already runs Ollama (5.3 GB)
and MuseTalk (~6.5 GB).

**Conclusion:** wrong licence, wrong languages, wrong hardware, no source.
Nothing to salvage.

---

## 2. ComfyUI — adopt, narrowly

`comfy-org/comfyui`, GPL-3.0. The earlier "noncommercial" grep hit was a false
positive — it is GPLv3's own §6 wording (`LICENSE:271`, "allowed only
occasionally and noncommercially"), a clause *about* distribution media, not a
restriction on us.

**Commercial use is permitted.** GPL-3 is copyleft, not non-commercial.

### The copyleft boundary

Copyleft only reaches code that forms a single work with ComfyUI. ComfyUI is a
standalone server with an HTTP API (`api_server/`, `main.py`). If DreamTalk's
FastAPI backend calls it over HTTP as a separate process — the way we already
call IndicF5 and MuseTalk — that is arm's-length aggregation, not a derivative
work, and DreamTalk's own source is unaffected. This is how essentially every
commercial ComfyUI deployment is structured.

What we must *not* do is vendor ComfyUI source into our backend or import it as
a Python library. (This is an engineering read of the licence, not legal advice
— worth a lawyer's eye before we ship commercially.)

### What it would actually buy us

Not the node GUI — we have FastAPI orchestration already, and replacing it
would be a regression. The value is the **node ecosystem**, which is the
fastest-moving distribution channel for exactly the models on our gap list:

- LivePortrait nodes → the **upper-body/gesture** gap (§3.3 of the competitive
  analysis), already wired but unused.
- Portrait/hair generation and matting nodes → the **hair** gap, our last open
  quality-audit finding.
- Image-restoration and face-detail nodes → could raise texture quality above
  the current 1024 atlas bake.

**Recommendation:** run it as a sixth compose service, GPU-gated, called over
HTTP for offline asset generation (hair, texture enhancement) — *not* in the
interactive reply path, where its model-loading cost would worsen our already
bad 16–23 s latency. Weights are our responsibility and must be licence-checked
individually; ComfyUI ships none.

---

## 3. OmniVoice — the best technical fit we have found, and we cannot ship its weights

This one hurts, because on capability it is close to ideal.

### The technology is exactly what §3.4 and §4.2 of the gap analysis ask for

`k2-fsa/OmniVoice`, 0.6B params, zero-shot TTS with voice cloning, 646
languages / 581k hours of training data, RTF as low as 0.025 (40× real-time).

**All 22 scheduled Indian languages are present, plus English** — verified
against `docs/languages.md`:

| Language | hours | | Language | hours |
|---|--:|---|---|--:|
| Tamil | 423.1 | | Marathi | 156.7 |
| Bengali | 271.8 | | Panjabi | 147.4 |
| Assamese | 270.9 | | Odia | 144.8 |
| Bodo | 231.6 | | Maithili | 131.4 |
| Telugu | 230.2 | | Kannada | 128.1 |
| Urdu | 211.3 | | Hindi | 117.2 |
| Nepali | 171.5 | | Dogri | 117.0 |
| Malayalam | 166.6 | | Konkani | 112.8 |
| Kashmiri | 110.4 | | Santali | 98.4 |
| Gujarati | 91.2 | | Sanskrit | 84.4 |
| Sindhi | 46.3 | | Manipuri | 44.5 |
| **English** | 206,061 | | | |

That is the *entire* Indic-Mio deployment goal — cloned voice in 22 languages
plus English — in one model we could run today, at 40× real-time, against our
current CPU-bound IndicF5 that covers 11.

### And then the licence

- Repo `LICENSE`: **Apache-2.0** — the *code*.
- Weights on HuggingFace `k2-fsa/OmniVoice`: **CC-BY-NC**.

The authors attribute this to their training data (Emilia). **CC-BY-NC forbids
commercial use of the weights.** Apache-2.0 on the code does not help; without
weights the code generates nothing.

**This is the fourth time this exact split has bitten this project** — Wav2Lip
(research-only), PIFuHD (CC-BY-NC), F5-TTS (MIT code / NC weights), now
OmniVoice. Code licence and weight licence must be checked separately, every
time. I would like to add that as a standing checklist item.

### The escape hatch, and its price

The repo ships **full training code** (`docs/training.md`, config and data
configs). So the weights are reproducible: retraining or fine-tuning on
permissively-licensed Indic corpora (AI4Bharat's Shrutilipi / IndicVoices, both
usable) would yield weights we own outright. That is a multi-GPU-week training
run, not a weekend — but it is the only path I see to cloned voice in all 22
languages, and it is strictly better than continuing to wait on Indic-Mio.

**Recommendation:** do **not** ship the CC-BY-NC weights. Do use OmniVoice now
for internal benchmarking (non-commercial evaluation is permitted) to measure
what Indic cloned-voice quality *could* be, then decide whether the retrain is
worth funding. Track it as the strategic answer to §3.4.

---

## 4. Handy — free, well-built, wrong shape

`cjpais/handy`, **MIT** — genuinely free, no weight problem in the code itself.

But it is a **Tauri desktop dictation app**: press a shortcut, speak, text
appears in whatever field has focus. Its own README says it "isn't trying to be
the best speech-to-text app — it's trying to be the most forkable one."
DreamTalk is a browser application; there is no seam where a desktop
global-hotkey app fits.

The reusable part is its *model choice*, not its code:

- `transcribe-cpp` — Whisper family via GGML/GGUF, GPU-accelerated
- `transcribe-rs` — **Parakeet V3**, CPU-optimised with automatic language
  detection

Parakeet V3 on CPU with auto language detection is a legitimately interesting
candidate if we ever add speech input to the twin conversation — it would free
GPU for MuseTalk, which is our actual bottleneck. But we would integrate the
model, not this repo.

**Recommendation:** bookmark as a reference for STT model selection. No
integration.

---

## 5. What I would actually do

1. **Drop HeyGem entirely.** Not a close call.
2. **Add ComfyUI as an HTTP-only compose service** for offline asset
   generation, targeted at the hair gap first. Keep it out of the reply path.
3. **Benchmark OmniVoice internally this week** — it answers the language
   question better than anything else available. Do not ship its weights.
   Scope the retrain on AI4Bharat corpora as a funded decision.
4. **Ignore Handy** except as a note on the STT roadmap.
5. **Adopt a standing rule:** for every third-party model, record code licence
   and weight licence as two separate fields. Four for four so far, the weight
   licence has been the restrictive one.

None of these four fixes our **top** problem, which remains latency (16–23 s
text, 123–300 s video) — that is still IndicF5-on-GPU and the WebSocket
streaming path. OmniVoice's 0.025 RTF would help enormously, which is precisely
why the retrain question is worth taking seriously.
