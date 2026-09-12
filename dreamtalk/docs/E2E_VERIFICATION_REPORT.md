# DreamTalk — Deep E2E Verification Report

_Run 2026-09-12 against the live Docker stack, using
`local_upload_testing/Image_local/Maharaj Profile.jpg` +
`local_upload_testing/Voice_local/sample1.wav` (11.1s)._

---

## 0. Method, and one honest limitation

**I cannot screen-record or capture audio.** There is no recorder or speaker in
this environment. Rather than claim "I watched it and it looked right", every
claim below is a *measurement*:

- video → frames decoded, **facial landmarks tracked on every frame**, lip
  aperture correlated against the audio envelope
- audio → pitch (F0), RMS, MFCC speaker descriptors, cosine similarity
- 3D → GLB parsed byte-wise (morph targets, topology, texture atlas extracted)
- backend → live API, Postgres queried directly
- frontend → real browser, screenshots at each step

Harness: `scripts/deep_e2e.py`, `deep_e2e2.py`, `analyse_lipsync.py`,
`lipsync_correlation.py`. Artifacts in `dreamtalk/e2e_deep/` (gitignored).

---

## 1. Headline

The avatar works in both 2D and 3D, and the voice clone is genuinely the
sample speaker. Getting there required fixing **five defects found by this
run**, three of which made the product visibly broken.

| Area | Verdict |
| --- | --- |
| 2D talking head | ✅ real, measured lip-sync (r=0.60, 40ms A/V offset) |
| 3D head geometry | ✅ recognisable person (was a mangled blob — fixed) |
| 3D head texture | ✅ real skin + features (was a grey smear — fixed) |
| 3D mouth animation | ✅ 80 visemes/utterance (was **1** — fixed) |
| Voice cloning | ✅ pitch match 142.1 → 141.7 Hz on 11 Indic languages |
| Non-Indic voice | ⚠️ stand-in voice, correctly flagged `cloned=false` |
| Brain memory | ✅ now persists to Postgres (was **not wired at all** — fixed) |
| Emotions | ✅ all 12 synthesize, prosody measurably varies (2 caveats) |
| Avatar persistence | ⚠️ JSON registry + disk; the `media_assets` table is unused |
| Profile status | ✅ `ready` (every English-sample profile was **degraded** — fixed) |

---

## 2. Defects found and fixed in this run

### 2.1 FLAME identity fit had diverged — the root cause of the broken 3D head

The shape solve was unregularised in real units and **explicitly unbounded**
(`bounds = [(None, None)]`, commented "identity unbounded"). The optimiser
bought a few pixels of landmark accuracy with absurd deformation.

Compounding it, `identity_coeffs = opt_coeffs / basis_std` *amplifies*
components with little landmark influence — so penalising the raw normalised
value left exactly those unconstrained.

|  | before | after |
| --- | --- | --- |
| identity \|max\| | **36.65 σ** | 3.00 σ |
| coefficients beyond 10 σ | 11 / 300 | 0 / 300 |
| max vertex displacement | **97.6 %** of head height | 16.9 % |
| texture atlas variance | 1428 (grey smear) | 3011 (skin + features) |

This one defect produced *both* visible failures: the mangled mesh, and the
garbage texture (deformed vertices sampled hair, suit and background instead
of skin). Fixed by regularising in FLAME σ units and clamping to ±3 σ.

### 2.2 Raw photo was used as the mesh texture

`generate_3d_mesh` wrote the **input photograph** as `texture_path` and
returned it even when the fitter had produced a proper UV atlas. FLAME's UV
layout does not index a photo, so the head was painted with foliage and
clothing. Now prefers the fitter's projected atlas.

### 2.3 3D avatar's mouth was frozen

`_extract_phoneme_segments` emitted **one segment per contiguous voiced run**.
Synthesized speech has almost no internal silence, so a whole utterance was a
single run: **1 keyframe for 7.5 seconds** — a lone `UH` held at
`mouth_open 0.4`. The 3D head opened its mouth once and held it.

Long runs are now subdivided into ~90 ms windows:

| | before | after |
| --- | --- | --- |
| keyframes (7.5 s utterance) | **1** | 80 (10.6 /sec) |
| distinct visemes | 1 (`UH`) | 6 (`DD E IH OH UH nn`) |
| `mouth_open` | frozen 0.40 | varies 0.10 – 0.60 |

2D was unaffected — MuseTalk runs its own neural lip-sync.

### 2.4 The brain had no memory at all

`ConversationMemory` was fully implemented (`create_interaction`,
`save_message`, `get_history`, `format_for_llm`) but **never called** from the
avatar runtime. `interactions` and `interaction_messages` were empty; the twin
only knew what the client resent in `history`, so closing the tab erased
everything.

Now: one long-lived interaction per profile, history recalled when the caller
supplies none, both turns written back with emotions.

### 2.5 Every English-sample profile was marked "degraded"

Enrollment validated the clone by synthesizing a preview **in the sample's own
language**. IndicF5 covers 11 Indic languages but not English, so an English
sample always threw and the profile was marked degraded — despite the clone
being good. Validation now runs in a covered language and records
`validated_language` plus an honest coverage warning.

### 2.6 Dead LLM endpoint cost ~60 s per reply

The configured primary (`144.79.62.242:8002`) is unreachable. A single reply
makes several LLM calls, each paying the full connect timeout before falling
back to Ollama — the source of the 60 s+ responses and the intermittent 503s
seen while sweeping languages. Added a circuit breaker: a failed endpoint is
skipped for a cooldown instead of re-probed every call.

---

## 3. 2D talking head — measured, not eyeballed

Rendered MP4: 756×768, **280 frames @ 25 fps**, h264 + **aac audio muxed**,
11.2 s, audio RMS 0.166 (not silent).

Landmarks tracked on **280/280 frames**. Lip aperture (inner-lip distance,
normalised by mouth width) vs the audio envelope:

```
correlation r = +0.603  at lag -1 frame (-40 ms)
aperture while speaking  0.0219
aperture while quiet     0.0151   (+45 % relative)
mouth vs forehead motion 2.89x    (lip-sync repaints the mouth, not the frame)
```

**Verdict: genuine, well-synchronised lip-sync.** A −40 ms offset is one frame —
effectively perfect A/V alignment. Articulation amplitude is on the subtle side
(aperture range 0.007–0.053, a 7× swing) but clearly speech-driven.

---

## 4. Voice cloning — is it really the same voice?

Speaker descriptor = 20 MFCC means + stds (cosine), plus median F0.

| | engine | `cloned` | F0 median | MFCC cos |
| --- | --- | --- | --- | --- |
| **reference sample** | — | — | **142.1 Hz** | 1.000 |
| Hindi reply | indicf5 | **true** | **141.7 Hz** | **0.983** |
| English reply | edge-tts | false | 275.7 Hz | 0.883 |

**Pitch is the discriminative evidence.** The cloned Hindi voice reproduces the
speaker's pitch to within **0.3 %** (142.1 → 141.7 Hz). The English stand-in
sits at 275.7 Hz — nearly double, a different voice entirely — and the runtime
labels it `cloned=false` with a reason, which the studio UI surfaces as
"Stand-in voice".

(Treat the 0.883 MFCC figure for the stand-in with care: MFCC means capture a
lot of channel commonality, so the cosine stays high across different speakers.
F0 is the signal that separates them.)

---

## 5. Languages — 23 advertised

| outcome | count | languages |
| --- | --- | --- |
| **cloned voice** (IndicF5) | **11** | as bn gu hi kn ml mr or pa ta te |
| stand-in (kokoro) | 2 | brx doi |
| stand-in (edge-tts) | 1 | en |
| transient 503 under load | 9 | kok ks mai mni ne sa sat sd ur |

The 9 failures were **not** missing language support — the same languages
return 200 on retry. They were load-shedding caused by defect 2.6 (each request
burning ~60 s on the dead LLM endpoint during a long sequential sweep).

**Cloned-voice coverage is 11/23 and is reported honestly per reply.** Full
22-language cloned coverage needs Indic-Mio, whose service definitions already
exist in compose but have never been deployed.

---

## 5b. Emotions — all 12, prosody measured

Every emotion synthesized successfully. Prosody genuinely varies (it is not a
label attached to identical audio):

| emotion | F0 median | RMS | dur |
| --- | --- | --- | --- |
| neutral | 157.5 Hz | 0.1767 | 6.0 s |
| calm | 139.9 | 0.0532 | 6.4 |
| happy | 151.1 | 0.1279 | 5.2 |
| excited | 141.5 | 0.1520 | 9.1 |
| sad | 173.0 | 0.1154 | 15.8 |
| angry | 135.6 | 0.1280 | 18.4 |
| surprised | 156.0 | 0.1253 | 14.8 |
| fearful | 144.5 | 0.0864 | 8.9 |
| disgusted | 149.0 | 0.1641 | 12.2 |
| loving | 151.7 | 0.0705 | 16.4 |
| frustrated | 116.8 | 0.1006 | **0.6** |
| confused | 155.3 | 0.1419 | 17.7 |

F0 spread 116.8–173.0 Hz (σ 13.2); RMS spread 0.053–0.177 (3.3× range).

**Two caveats worth acting on:**

1. The *direction* of the mapping looks off against normal prosody — `sad` has
   the **highest** pitch (173 Hz) and `angry` nearly the lowest (135.6 Hz),
   which is backwards from what listeners expect. Worth reviewing
   `PROSODY_PRESETS`.
2. `frustrated` produced only **0.6 s** of audio — almost certainly a truncated
   or failed generation, not a real reply.

---

## 6. Brain / self-learning

Multi-turn recall, then the decisive test — asking again with an **empty
history array**, so recall can only come from the server:

```
turn 1  "My favourite colour is turquoise and my dog is called Bruno."
turn 2  "What is my dog's name?"            -> "Your dog's name is Bruno!"
turn 3  "And what colour did I say?"        -> "You said turquoise..."
turn 4  (history=[]) "Remember my dog?"     -> "Bruno's his name, I remember."
```

Postgres went from 0 → 1 interaction, 16 messages with roles and emotions.

Then, in a **fresh browser session** with a different client, "Namaste, mera
naam Maharaj hai." drew the reply *"…meri shubhkamnayein aapko aur **Bruno**
se…"* — it volunteered the dog's name from the earlier API-driven conversation.
Memory crosses sessions and clients.

**Caveat on "self-learning":** this is conversational *memory*, not model
training. The `learning_logs` and `evolution_log` tables are still empty — no
weights or personality parameters are being updated. Nothing in the system
currently trains on your conversations.

---

## 7. Persistence — "save the avatar so I can view it anytime"

**It does persist**, and survived 6+ backend restarts during this run. Every
stored asset was re-fetched from a cold manifest read:

```
profile listed for the user              1 profile
manifest returns asset URLs              glb, mesh, texture, primary_image — all present
every stored asset re-downloads          glb 1168KB · mesh 844KB · texture 302KB · photo 1879KB
blendshape names persisted               all 10 (aa ih ou ee oh blink happy sad angry surprised)
```

- profiles in `results/avatar_runtime_profiles.json` (registry)
- assets on disk under `media/avatar_runtime/<profile_id>/{appearance,voice,responses}`
- manifest re-serves them behind signed URLs

**But not in the database.** `media_assets`, `voice_profiles` and
`identity_profiles` are all **0 rows** — the tables exist and are unused by the
avatar runtime. Storage is file-based.

That is durable on one host, but it will not survive a container rebuild that
drops the volume, and it does not replicate. Moving asset metadata into
`media_assets` is the remaining gap against the stated requirement.

---

## 8. What is still not right

1. **Cloned voice covers 11 of 22 languages.** Deploy Indic-Mio to close it.
2. **Avatar assets are not in the DB** (`media_assets` unused).
3. **No actual learning** — memory only; `learning_logs` empty.
4. **3D head has no hair, teeth or ears of its own** — FLAME is a face model.
   An open mouth shows a void. Teeth + hair are the biggest remaining realism
   gaps; see `REALISTIC_HEAD_PLAN.md`.
5. **Latency**: ~90 s per spoken reply on this box (IndicF5 runs on **CPU**,
   MuseTalk needs ~6.5 GB VRAM and contends with the 5.3 GB Ollama model on an
   8 GB card). Repeated OOM can corrupt the CUDA context and need a restart.
6. **Lip articulation is subtle** rather than pronounced.
7. **Emotion→prosody mapping looks inverted** for `sad`/`angry`, and
   `frustrated` generated a 0.6 s clip (see §5b).
