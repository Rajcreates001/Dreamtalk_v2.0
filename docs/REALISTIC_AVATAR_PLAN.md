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
Reconstruct from the same source photo and compare against FLAME on:
- **identity**: Facenet512 distance vs the photo (FLAME baseline: 0.1445)
- **silhouette**: IoU of the rendered head against the BiSeNet head mask
  from the photo — this is the number that captures "hair has volume"
- geometry sanity: vertex count, watertightness, depth/width ratio

Keep whichever wins per metric. FLAME may still win on identity while losing
badly on silhouette; that result would itself decide the hybrid below.

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
Indic-Mio is deployed and reports 23 clone languages. Verify each end to end
rather than trusting the capability list: synthesize, confirm
`validation.cloned`, measure pitch against the reference, and keep the audio
for a human to judge accent.

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
