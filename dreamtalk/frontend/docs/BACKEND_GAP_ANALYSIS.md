# DreamTalk Astra — Backend gap analysis (for Codex)

Authored from the frontend side after reading the backend code. Goal: what's
missing to actually ship "a 3D avatar that looks like the person, speaks in
their cloned voice, and thinks like them." Priorities: **P0** = blocks a
believable demo, **P1** = needed for quality, **P2** = later.

Grounding (files read): `digital_twin/appearance.py`,
`identity/appearance.py`, `pipeline/flame_fitter.py`,
`digital_twin/voice_cloning.py`, `digital_twin/creation_pipeline.py`,
`backend/api/v1/endpoints/{digital_twins,avatar}.py`, `cognition/*`,
`avatar/core/body/idol/*`, new `services/{cloned_speech,multimodal_language}.py`.

---

## 1) 3D AVATAR — the biggest headache

**What exists today:** appearance upload → RetinaFace detect → quality check →
MediaPipe/PFLD landmarks → head pose → blendshape estimate → DeepFace embedding
→ **FLAME fit** (`flame_fitter.py`) → a `.obj` head mesh. The frontend viewer
(`vrm-viewer.tsx`) can load `.obj`/`.mtl` and VRM/GLB.

**Why it's painful — concrete gaps:**

- **P0 · It doesn't look like the person.** FLAME fits *shape* to the photo's
  2D landmarks, but textures with the **FLAME mean texture atlas** (a generic
  average face). No projection of the user's photo onto the mesh → a generic
  gray/averaged head. Fidelity to the individual is the whole product.
- **P0 · Single shared output file.** `flame_fitter` writes every twin to one
  global `static/current_mesh.obj`. Concurrent users overwrite each other; no
  per-twin persistence. Must be `media/<twin_id>/appearance/model.glb`.
- **P0 · Not riggable in the browser.** The delivered `.obj` has no skeleton
  and no exported blendshape morph targets, so the studio can't drive lipsync/
  expression in real time. FLAME's expression basis lives server-side only.
- **P1 · Face-only.** No eyes, teeth, hair, neck, shoulders/body → a floating
  head. FLAME is a face model.
- **P1 · Format mismatch.** Frontend/studio are VRM/GLB-oriented (humanoid rig,
  ARKit-style blendshapes/visemes). Backend emits FLAME `.obj`. `.obj` can't
  carry the rig the speech UI needs.
- **P1 · Reconstruction runs *synchronously* in the upload request.** No job/
  progress. The frontend already polls `appearance/result` and
  `pipeline/status` — make it a Celery job.
- **P2 · IDOL** full-body (SMPL-X + Gaussian) exists but is **orphaned** (not
  wired to the twin flow) and too heavy for real-time browser view.
- **Architectural muddle:** talking-head animation elsewhere uses
  LivePortrait/MuseTalk (2D video). Mixing 2D-video avatars and 3D-mesh avatars
  without a decision creates two half-built paths.

### Recommendation — pick ONE avatar paradigm

- **Option A (ship this first): 2D photoreal talking head.**
  Drive the user's actual photo with LivePortrait / SadTalker / MuseTalk using
  the cloned audio. It *is* their face → maximum identity fidelity, real
  lipsync + expressions, no rig headaches. Limitation: limited free-view head
  rotation. This is what most "digital human from one photo" products ship.
- **Option B (true 3D, weeks of work): rigged GLB/VRM.**
  Keep FLAME for identity *shape*, but add: (1) **photo texture** (DECA/EMOCA
  give a fitted albedo, or frontal UV projection), (2) eyes/teeth/generic body,
  (3) export **GLB with ARKit-52 blendshapes + humanoid bones**, visemes mapped
  to those blendshapes. Real-time-viable in-browser.
- **My call:** ship **A** as the product avatar now; expose FLAME 3D as an
  "experimental" view; only build **B** if free-viewpoint 3D is a hard
  requirement.

### 3D fixes to hand Codex (in order)
1. Per-twin mesh storage; stop writing `current_mesh.obj`. Return
   `model_url`/`texture_url` in `appearance/result`.
2. Move reconstruction (and any video gen) to a **background Celery job** with
   progress; keep the existing poll endpoints.
3. Add **photo→texture** so it resembles the person (DECA albedo or projection).
4. If going 3D: export **GLB** (not raw `.obj`) with morph targets; standardize
   on **ARKit-52** blendshape names shared with the studio's viseme/emotion map.
5. Return a stable **avatar contract** so the frontend picks the renderer:
   `{ model_url, texture_url, format: "glb"|"vrm"|"talkinghead2d", rig, visemes_supported }`.

---

## 2) VOICE — relatively healthy

**What exists:** cloning-first — IndicF5 → RVC fallback → synthetic → tone
fallback; IndicF5 microservice is up and healthy. Good foundation.

**Gaps:**
- **P1 · Lipsync alignment.** For any avatar, TTS must return **phoneme/viseme
  timestamps** (forced alignment) so animation follows `audio.currentTime`, not
  `setTimeout`. Confirm `cloned_speech.py` emits a timed viseme/word track.
- **P1 · Cross-lingual timbre consistency.** Does the *same* cloned voice carry
  across all 12 Indian languages, or does timbre drift per language? Needs an
  eval.
- **P1 · Streaming.** Real-time conversation wants streamed audio + visemes, not
  a batch WAV per turn.
- **P2 · Clone quality gating.** Detect a poor clone (too-short/noisy sample) and
  tell the user, rather than silently degrading to synthetic.

---

## 3) BRAIN — ambitious; watch for over-engineering

**What exists:** a large cognition stack — reasoning endpoint, `neurologique`
(brain regions), `cortex` Titans memory + recall, `aura` consciousness; LLM via
the GPU server.

**Opinion:** this is the area most at risk of elaborate scaffolding that never
grounds in the specific twin. The product only needs one thing to feel real: a
persona that **stays in character, remembers, and speaks**.

**Gaps to close (verify each is actually wired):**
- **P0 · Persona conditioning.** The LLM system prompt must be built from the
  twin's stored personality traits/relationship.
- **P0 · Memory grounding (RAG).** Retrieve the twin's knowledge sources +
  past-conversation memories (Weaviate/pg) into the prompt; write new memories
  back after each turn.
- **P0 · One coherent runtime endpoint.** The studio needs a single
  `respond(twin_id, message, context) → { text, emotion, audio_url, visemes }`
  that fuses persona + RAG + cloned TTS + emotion. Today the capability is
  spread across many modules.
- **P1 · Hallucination / consistency control**, and **emotion → prosody →
  face** wiring (emotion drives both TTS prosody and blendshapes).
- **Advice:** freeze new brain abstractions until this loop works end-to-end and
  is measured; depth ≠ believability.

---

## 4) Cross-cutting

- **P0 · One identity, versioned.** Link face embedding + voice speaker profile
  + persona to a single twin identity with a version, so pillars stay in sync.
- **P0 · Async everywhere heavy.** Reconstruction, cloning, video, first LLM
  load → Celery jobs with progress (frontend already polls).
- **P1 · Contract hygiene.** Reconcile `/api/avatar` vs `/api/v1/avatar` prefix,
  and the WS path (`/api/v1/avatar/ws/realtime` in compose vs `/ws/chat` in the
  router). The frontend needs one stable set.
- **P1 · Storage.** Per-twin media dirs, signed URLs, cleanup on delete.
- **P2 · Golden-sample eval.** One known face + voice in CI; assert mesh/texture/
  clone/lipsync/persona quality thresholds so regressions are caught.

---

### TL;DR for Codex
1. **Decide the avatar paradigm** (recommend 2D talking-head first). 2. **Per-twin
storage + async jobs** (kill `current_mesh.obj`). 3. **Make it look like the
person** (photo texture / real photo). 4. **Timed visemes** from TTS for lipsync.
5. **One `respond()` runtime** fusing persona + memory + voice + emotion. Get
that single loop believable before adding more brain depth.
