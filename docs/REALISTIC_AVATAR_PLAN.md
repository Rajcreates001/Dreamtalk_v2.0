# Plan: generated geometry instead of a compressed template

## The diagnosis, stated plainly

The current 3D path fits **FLAME**, a pre-built statistical head model: ~300
shape coefficients deform a fixed 5023-vertex template, and the photograph is
projected onto it as texture. That is exactly "compressing the image onto a
pre-built 3D model", and it has a hard ceiling:

- the silhouette is the template's skull, so **hair has no volume**
- topology is fixed, so anything FLAME cannot express is simply absent
- one frontal photo leaves large parts of the atlas unseen (measured: 14.7%
  black + 8.8% flat grey on a real avatar's 1024² atlas)

No amount of texture work fixes a wrong silhouette.

## The constraint that decides the architecture

A generated mesh (TripoSR, InstantMesh, TRELLIS) has **arbitrary topology and
no blendshapes**. The avatar has to lip-sync, which needs morph targets
(aa/ih/ou/ee/oh + blink + emotions). FLAME's entire value here is that its
topology is *known*, which is what lets `face_blendshapes.py` synthesise those
targets deterministically.

So "replace FLAME with a generated mesh" as stated would produce a better
looking head that **cannot move its mouth**. The plan below keeps both
properties rather than trading one for the other.

## Candidate survey (licence-checked)

| Model | Code | Weights | Commercial | Speed | Notes |
|---|---|---|---|---|---|
| **TripoSR** | MIT | **MIT** | yes | <1s | feed-forward, Stability/Tripo |
| **InstantMesh** | Apache 2.0 | Apache 2.0 | yes | ~10s | multi-view diffusion + sparse recon, better topology |
| TRELLIS / TRELLIS.2 | MIT | check | check | 20s-4min | structured latents, PBR materials |
| Hunyuan3D-2 | — | Tencent **non-commercial** | **no** | — | excludes EU/UK/KR; rejected |
| PIFuHD | — | research-only terms | **no** | — | human-specific, licence blocks use |

Both TripoSR and InstantMesh clear the licence bar for code **and** weights,
which is the check that eliminated four candidates in an earlier survey.

## Phases

### Phase 0 — make iteration possible (DONE)
`AVATAR_GPU_UNLOAD_AFTER_RENDER` defaulted to true, so MuseTalk was discarded
after every render and the next paid a ~20 minute cold load. A 3s clip
measured 3482s end to end. Now false; verifying the warm path lands near 80s.
Without this, every experiment below costs an hour.

### Phase 1 — mesh service
Stand up TripoSR as its own Docker service (`dreamtalk-mesh3d`), HTTP
`POST /reconstruct` taking an image and returning a mesh. TripoSR first
because it is the smallest VRAM footprint and fastest to iterate against;
InstantMesh is the quality upgrade once the plumbing is proven.

VRAM budget on the 8188 MiB card: vLLM 3685 + MuseTalk ~2000 + context ~1092
leaves roughly 1.4 GB. Avatar creation is a batch operation, not realtime, so
the orchestrator may unload the others for the duration rather than trying to
fit everything at once.

### Phase 2 — measure, do not assume
`scripts/qa/mesh_compare.py` renders a mesh front-on and scores it two ways.

**FLAME baseline, measured on the KB profile:**

| metric | value | reading |
|---|---|---|
| identity (Facenet512) | **0.1445** vs 0.300 threshold | recognisably the right person |
| silhouette IoU | **0.5561** | |
| recall | **0.6143** | 39% of the photographed head is simply absent |
| precision | **0.8543** | what it does draw is mostly in the right place |
| area ratio | **0.7191** | the render covers 72% of the head's area |

That split is the whole argument in two numbers. Identity is fine because the
photograph is projected on as texture. The outline is not, and the missing
third is the crown and the hair — precision stays high while recall collapses,
which is the signature of a shape that is *too small*, not one that is
misplaced.

Two properties of the harness are load-bearing:

- Orientation is chosen by **detection confidence**, never by the identity
  score, so it cannot select the pose that flatters the number it reports.
- Pitch is a fallback, not part of the search. Including it let a −20° tilt
  win on 0.9997 against 0.9993 of detector noise and moved the reported
  identity from 0.1445 to 0.3494 — across the threshold. A search over poses
  will find one that breaks your metric if you let it.

Keep whichever model wins per metric. FLAME winning identity while losing
silhouette is the expected outcome, and it is the argument for the hybrid
below rather than a straight replacement.

### Phase 3 — animation transfer (the hard part)
Give the generated mesh FLAME's blendshapes:
1. fit FLAME to the generated mesh (or to the same photo)
2. for each generated vertex, find its correspondence on the FLAME surface
3. carry each FLAME blendshape delta across that correspondence, weighted by
   distance, so the generated mesh inherits aa/ih/ou/ee/oh/blink/emotions

Validation is the same measurement already used on the current head: blink
must close ≥95% of the eyeball diameter, and each viseme must move a non-zero
vertex set in the mouth region.

### Phase 4 — 2D mouth
Detail transfer (low frequencies from the generated patch, high frequencies
from the photograph) is committed and measured in isolation at 0.98 of source
sharpness for 9% of the motion. Needs confirming on a rendered video, which
is what Phase 0 makes affordable.

### Phase 5 — voice across 22 languages
All 22 synthesize through Indic-Mio with `cloned: true`, no edge-tts
fallback, no clipping, 2–24 s per request. That is the smoke test, and it
stays true if the voice belongs to somebody else — which is the actual
complaint. `scripts/qa/speaker_similarity.py` scores each output against the
enrolment with WavLM-base-plus-sv.

The first run of that harness reported an impostor control of **1.0000**. The
same recording had been enrolled under several profile ids, so the "different
speaker" was the subject. A control at 1.0 silently voids every other number
in the report while looking like a strong result, so impostor selection now
rejects candidates by content hash and again by similarity. The runtime does
hold one genuinely different speaker — median f0 263 Hz against 143 Hz — and
it scores **0.7447**. That is the line the cloned outputs have to clear.

The only three languages below the same-speaker threshold were also the only
three whose prompt was a single greeting word, synthesising to 0.64–0.72 s.
An x-vector on a sub-second clip measures phonetics, not speaker. Those clips
are now reported as unjudged rather than failed, and the prompts repeat the
greeting to reach a measurable length — repetition rather than invented
sentences, because a wrong sentence in a language nobody here can check tests
the wrong thing.

### Phase 6 — end to end
Login → build avatar → 3D → 2D → conversation in several languages, with the
measurements above attached to each step.

## What would make this fail

- **Blendshape transfer is the real risk.** If correspondence is poor the
  mouth will deform wrongly, which is worse than a static but correct head.
  Phase 2's numbers decide whether to proceed or to keep FLAME geometry and
  spend the effort on texture completion instead.
- 8 GB is tight for three models. Orchestrated unloading is the fallback.
- Generated meshes are often not watertight and can carry inverted normals;
  both break the renderer in ways that look like "the avatar is broken".
