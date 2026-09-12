# DreamTalk — Realistic Head: Status & Plan

_Written 2026-09-12 after auditing the running stack and driving it end-to-end._

---

## 0. The headline

The architecture study you were given is sound, but it describes a system you
have **already largely built**. The audit found the gap is not "which repos to
clone" — it is that a few finished components were wired together wrongly, and
one is blocked by hardware, not code.

**Before this session:** the reconstructed head shipped to the browser as a
static bust with zero morph targets, while the API advertised
`arkit_blendshapes: true`. English speech returned HTTP 422. The 2D video
renderer died on CUDA OOM.

**After:** 22/22 end-to-end checks pass, including the MuseTalk video render.

---

## 1. What is actually built and working

Verified live, not read from code:

| Module | Stack | Status |
| --- | --- | --- |
| Face restoration / identity | GFPGAN + Real-ESRGAN + InsightFace | ✅ ready |
| Face detection + landmarks | RetinaFace / MediaPipe | ✅ ready |
| **3D head reconstruction** | **FLAME 2020 fitted from one photo** | ✅ 5023-vert textured head |
| **Head animation** | **10 GLB morph targets** | ✅ **new this session** |
| 2D talking head | MuseTalk (neural, CUDA) | ✅ renders (GPU permitting) |
| Portrait animation | LivePortrait | ✅ wired (`liveportrait_video`) |
| Voice cloning | IndicF5 — 11 Indic languages | ✅ ready |
| Language coverage | 22 scheduled + English via translation | ✅ 23 languages |
| Emotion | 12 labels → voice prosody + face | ✅ ready |
| ASR | IndicWhisper | ✅ available |
| Conversation | LLM + memory + Weaviate KB | ✅ ready |

You are **not** at the "clone five repos and POC it" stage. You are at the
"integrate, harden, and fix resource contention" stage.

---

## 2. What I changed to make the head real

### 2.1 The GLB exporter was silently broken

`AvatarExporter.obj_to_glb` had two defects that cancelled each other into a
quiet downgrade:

1. Its primary path required `pygltflib`, which **is not installed** → `ImportError`.
2. That path also contained a typo — `pygltltflib.Accessor` — so it would have
   raised `NameError` even with the package present. Only `ImportError` was
   caught, so the typo was latent.

Every export therefore fell through to **trimesh**, which cannot emit morph
targets and mishandled the texture (it was handed a *path* where an image was
expected). Evidence: exported GLBs carried trimesh's node names (`world`,
`generated_head.obj`), not the exporter's.

**Fix:** a dependency-free glTF 2.0 binary writer (`_export_glb_native`) that
emits POSITION/NORMAL/TEXCOORD_0, indices, an embedded texture, and **morph
targets**. Fallbacks now catch `Exception`, not just `ImportError`. Typo fixed.

### 2.2 The head had no blendshapes

FLAME's expression space is a 100-dim PCA basis with no semantic labels. The
repo ships a `bs2exp` matrix intended to map ARKit blendshapes → FLAME
expressions, but **its shape is (50, 100) while `BLENDSHAPE_NAMES` has 52
entries** — so `bs_array @ bs2exp` would raise, and the row semantics are
ambiguous. I did not build on it.

Instead I used `FLAME_masks.pkl` (already on disk), which gives unambiguous
vertex groups: `lips`, `left/right_eye_region`, `forehead`, `nose`, `face`,
`left/right_eyeball`, `neck`, `scalp`. `pipeline/face_blendshapes.py` deforms
those regions directly to build 10 targets:

```
visemes   aa  ih  ou  ee  oh
lids      blink
emotion   happy  sad  angry  surprised
```

Design choices that make this robust for *any* fitted face:

- **Axes are detected, not assumed** — up = the axis separating forehead from
  neck; forward = where the nose protrudes. No hardcoded Y-up.
- **Amplitudes are calibrated as a fraction of head height**, so a large or
  small fitted identity gets proportionate motion.
- **Eyeballs are excluded** from the movable shell so they never tear out.

**Verified numerically** (not by eye):

| shape | peak/H | lips | eyes | brow | eyeball | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| aa | 0.055 | 0.0152 | 0 | 0 | 0 | OK |
| oh | 0.045 | 0.0231 | 0 | 0 | 0 | OK |
| blink | 0.030 | 0 | 0.0026 | 0.0015 | 0 | OK |
| happy | 0.026 | 0.0116 | 0 | 0 | 0 | OK |
| angry | 0.018 | 0.0024 | 0.0002 | 0.0029 | 0 | OK |

Assertions: visemes move lips more than eyes; blink drives lids *downward*;
mouth corners lift for happy and drop for sad; brow moves for angry; eyeballs
never move; peak displacement ≤ 5.5% of head height.

**Result:** GLB 391 KB → 1139 KB, 5023 verts, 10 named morph targets, texture
and normals intact.

### 2.3 The manifest lied

`arkit_blendshapes` and `vrm_expressions` were hardcoded `True`. They are now
**derived** from what is actually baked into the GLB, and the manifest publishes
`blendshape_names` and `visemes`. `animation_driver` reports
`glb_morph_targets` when real, `timestamped_external_blendshapes` otherwise.

A capability flag the mesh cannot honour is worse than a missing one — the
frontend renders a head it cannot animate.

### 2.4 Frontend now renders *your* head

New `TwinHead3D.tsx` loads `profile.appearance.glb_url` and drives
`morphTargetInfluences` from the lipsync track off the cloned-voice audio clock,
plus idle blink and an emotion overlay. `AvatarRenderer` routes 3D there only
when the profile genuinely has blendshapes, falling back to the stand-in VRM
otherwise. Previously the 3D mode showed a hardcoded anime VRM — never the user.

### 2.5 English no longer 422s

IndicF5 covers 11 Indic languages, **not English**, and the frontend was sending
`strict_clone: true`, turning that capability gap into a hard error. The runtime
already had a graceful path. Now English returns speech with
`audio.cloned === false` plus a reason, surfaced honestly in the studio as
"Stand-in voice".

### 2.6 MuseTalk CUDA OOM

Not a code bug — **GPU contention**. Host Ollama (`llama3.1:8b`) holds ~5.3 GB
of an 8 GB card; MuseTalk wants essentially the whole GPU (measured: free drops
to ~0 after load). Proven by loading MuseTalk in isolation on a free GPU → `True`.

Fixed by reclaiming VRAM **before** loading (evict the host LLM via Ollama's
`keep_alive: 0`, then poll until the driver hands memory back). A post-OOM retry
does not work: PyTorch's caching allocator can be left in a state where even a
freed GPU fails with `INTERNAL ASSERT ... CUDACachingAllocator`.

---

## 3. Where realism is still limited, honestly

The head is now **geometrically yours and animatable**, but it is a
*FLAME-topology* head — smooth, no hair, no ears of your own, no teeth/tongue.
Ranked by impact on "looks like a real human":

| Gap | Impact | Fix |
| --- | --- | --- |
| No hair / ears / shoulders | **Highest** — reads as a mannequin | Hair strand card generation, or composite 2D for hero shots |
| Texture is photo-projected only on the visible side | High | Symmetry fill + inpainting for the unseen half |
| No teeth / tongue geometry | Medium — mouth is a void when `aa` opens | Add a static teeth mesh parented to the jaw |
| Blendshapes are geometric, not learned | Medium | Train proper `bs2exp` (fix the 50-vs-52 mismatch) |
| No jaw *rotation* (visemes are translations) | Medium | Apply FLAME pose via LBS, not just shapedirs |
| No eye specular / subsurface skin | Medium | Add an env map + SSS approximation in the shader |

**The single most effective next step is not a new model — it is teeth + hair +
a proper skin shader.** A FLAME head with those reads dramatically more human
than one without, and none of it requires new research.

---

## 4. The two-track recommendation

Do not try to make one renderer do everything.

**Track A — photoreal (2D):** MuseTalk on the user's actual photo. This *is*
their face, so identity fidelity is perfect. Use for "watch my twin speak".
Already working.

**Track B — interactive (3D):** the FLAME head with morph targets. Real-time,
free-view, zero latency, responds instantly while the 2D render is still
generating. Use as the live/idle state. Now working.

The frontend already switches between them behind one `AvatarRenderer`.

---

## 5. Free / open-source options, assessed against *your* stack

You already run the best-in-class free option in most rows. Where a swap is
worth it:

| Need | You run | Worth evaluating | Verdict |
| --- | --- | --- | --- |
| English + 22 langs cloned voice | IndicF5 (11) | **Indic-Mio** (Apache-2.0, 22+English) | **Yes — highest value.** Dockerfile + compose already written, never deployed |
| Lip-sync video | MuseTalk 1.5 | — | Keep |
| Portrait animation | LivePortrait | — | Keep |
| 3D head | FLAME + own fitter | DECA / 3DDFA-V2 | Only if you want learned detail maps |
| One-shot 3D talking | — | Real3D-Portrait, GeneFace++ | Research-grade; not needed given A+B |
| Restoration | GFPGAN + Real-ESRGAN | — | Keep |
| Real-time runtime | own FastAPI + WS | LiveTalking | Reference only — yours is further along |

**Licensing caution** that matters commercially: Wav2Lip is research/non-commercial;
PIFuHD is CC-BY-NC and archived; HunyuanPortrait is academic-use; F5-TTS code is
MIT but its pretrained weights carry CC-BY-NC. IndicF5, Indic-Mio, SadTalker,
OpenVoice and Chatterbox are permissive.

---

## 6. Recommended order of work

1. **Teeth + tongue mesh** parented to the jaw — removes the "void mouth" on
   open visemes. Cheap, high realism payoff.
2. **Deploy Indic-Mio** — unblocks *cloned* English and the full 22 languages.
   The service definitions already exist; it needs weights and VRAM headroom.
3. **Skin shader + env map** on `TwinHead3D` — subsurface approximation and eye
   specular. Pure frontend.
4. **Hair** — the hardest remaining realism gap.
5. **Fix `bs2exp`** (50 vs 52) and train a proper ARKit→FLAME mapping to replace
   the geometric blendshapes.
6. **Jaw pose via LBS** so `aa`/`oh` rotate the jaw rather than translating it.

---

## 7. Hardware reality

An 8 GB RTX 4060 Laptop **cannot** hold concurrently:

```
Ollama llama3.1:8b   5.3 GB
MuseTalk             ~6.5 GB (takes essentially the whole card)
FLAME + restoration  ~3.4 GB
```

The code now evicts the LLM before rendering, but this serialises the pipeline.
Options, cheapest first:

- Run the LLM on **CPU** or drop to `llama3.2:3b`, freeing the GPU for MuseTalk.
- Set `OLLAMA_KEEP_ALIVE=30s` so it releases promptly on its own.
- Tune `MUSETALK_MIN_FREE_VRAM_GB` (default 6.5) and `VRAM_RECLAIM_TIMEOUT` (25s).
- For production, a **16–24 GB GPU** removes the contention entirely.

Note: repeated OOM events can corrupt the process's CUDA context
(`cudaErrorInvalidDevice`), requiring a backend restart. Avoiding OOM up front —
which the new reclaim does — is what keeps the service stable.

---

## 8. Two smaller defects found

- `dreamtalk/tests/pipeline_test_data/test_voice.wav` is **2.0 s**, but the
  runtime requires ≥3 s of speech — the repo's own fixture cannot pass its own
  pipeline. `test_face.jpg` likewise has no detectable face.
- MuseTalk's **BiSeNet face-parser checkpoint does not match its model
  definition** (`spatial_path.*` expected vs `cp.*` present, plus a
  `ffm.convblk.conv.weight` size mismatch). It silently degrades to a geometric
  blend mask, which costs edge quality on the rendered video.
