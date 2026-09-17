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

### Phase 2 — RESULT: the generated mesh does not win

`dreamtalk-mesh3d` runs TripoSR and reconstructs from the same photograph in
165s: 60,697 vertices against FLAME's 5,023. Measured side by side:

| model | verts | identity | verdict | IoU | recall | precision | area |
|---|---|---|---|---|---|---|---|
| FLAME head only | 5,023 | 0.2235 | same person | 0.5538 | 0.6134 | 0.8508 | 0.72x |
| **FLAME + hair shell** | 5,764 | **0.1953** | same person | **0.6606** | **0.7161** | 0.8949 | 0.80x |
| TripoSR generated | 60,697 | **0.3260** | **not recognised** | 0.1847 | 0.6087 | 0.2096 | **2.90x** |

Two caveats first, because both are real:

- **Identity is measured on vertex colours, not a baked texture.** Baking needs
  an OpenGL context and the container is headless
  (`XOpenDisplay: cannot open display`), so 60,697 colour samples stand in for
  a 2048² atlas. A baked texture would likely improve on 0.3260.
- **The silhouette metric asks about the head.** TripoSR reconstructs the bust,
  so precision 0.21 is partly the mask excluding neck and shoulders rather than
  the mesh being wrong. Area 2.90x says the same thing.

Neither rescues it, because **recall depends on neither**. Recall is pure
coverage of the photographed head: FLAME with the hair shell reaches
**0.7161**, TripoSR **0.6087**. Ignoring everything it draws outside the head,
the generated mesh still captures less of the actual head than the template fit
does — while being unrecognisable as the subject and carrying twelve times the
geometry.

**Decision: keep FLAME geometry.** The complaint that started this work —
"you are compressing the image onto a pre-built 3D model" — is answered better
by the hair shell, generated from the subject's own segmented hair and worth
0.5538 to 0.6606 of IoU, than by replacing the topology with something that
scores worse on every measurement surviving its own caveats.

mesh3d stays deployed. It is the honest way to re-test this once the texture
bake works headless, and reconstruction is the right tool if the product ever
needs a bust rather than an animatable head.


### Phase 3 — NOT REQUIRED

Blendshape transfer onto generated topology was the plan's stated main risk,
and Phase 2 removes the reason to take it. There is no point carrying FLAME's
blendshapes onto a mesh that is a worse likeness of the subject than FLAME is.

The animation the head already has is measured on the shipped GLB: blink
closes 104.7% of the eyeball diameter, all five visemes are centred at 16-28%
of head height against blink's 63%, and the most similar viseme pair (aa/ih)
sits at cosine 0.959 — distinct, if only just.

### Phase 4 — 2D mouth (DONE, by measurement)

The crossover between the generated patch's low frequencies and the
photograph's high frequencies is a weight, not a switch, and it was set by
rendering the same clip four times:

    weight   sharpness   motion   aperture spread   interior SD
     0.00      0.112      3.163       0.1012           8.27
     0.50      0.248      2.884       0.1031           7.77
     0.85      0.662      2.725       0.1039           7.42   <- default
     1.00      0.906      2.664       0.1006           7.29

The worry that drove this to 0.00 - that a still photograph's lips get
imprinted over a generated open mouth - is testable, and aperture spread is
the test: it would fall if the mouth were being held shut. It does not fall
anywhere in the range. Motion and interior variation do, by 14%, which is the
static donor fighting the animation and is the actual price paid.

Isolation of the patch is unchanged and verified on every render: mouth
motion 2.7, forehead and eyes 0.0, background 0.0.

### Phase 5 — voice across 22 languages (DONE)

All 22 synthesize through Indic-Mio with `cloned: true`, no edge-tts fallback,
no clipping. That was always the easy half. The hard half is whether the audio
is the enrolled speaker, and it is now measured on every request rather than
sampled by a harness: `speaker_verify` scores each take with
WavLM-base-plus-sv, resynthesises anything below 0.80, and returns the best of
up to three with the score attached.

Definitive sweep on the current avatar:

    22/22 scored, min 0.8765 (bn), mean 0.9197, max 0.9524 (kn)
    22/22 above the 0.86 same-speaker line
    every one on the FIRST attempt - 22 syntheses for 22 requests
    impostor control 0.7447, from a genuinely different speaker
    (median f0 263 Hz against the subject's 143 Hz)

Two findings that only a gate makes visible:

- The engine samples. One sentence synthesised five times spans 0.19 of
  similarity, and single takes have landed at 0.5684 - below what an unrelated
  speaker scores. A report that averages this reads "22 of 22 cloned"; a
  listener hears one utterance.
- Kashmiri is the weak language. It has needed all three attempts and still
  come back at 0.7622, at which point the reply carries a quality warning
  saying it may not sound like the speaker rather than being shipped quietly.

The impostor control is the reason any of these numbers mean anything, and it
had to be fixed before it did: the first version picked another profile's
reference and scored exactly 1.0000, because the same recording had been
enrolled under several ids. Candidates are now rejected by content hash and
again by similarity.

### Phase 6 — end to end (DONE)

Measured on avatar `a489f6f4`, built through the production creation endpoint
from one photograph and one 11-second recording.

    3D    Head, teeth, tongue and hair in the GLB
          identity 0.1953 against a 0.300 threshold
          silhouette IoU 0.6606, covering 72% of the photographed head
          blink closes 104.7% of the eyeball
          five visemes at 16-28% of head height, blink at 63%
          closest viseme pair aa/ih at cosine 0.959

    2D    mouth motion 2.7, forehead and eyes 0.0, background 0.0
          mouth keeps 66% of the source photo's sharpness
          aperture varies over 10.4% of the mouth box
          untouched cheek control at 99%, so the codec costs 1%

    voice 22/22 languages, every one on the first attempt
          mean 0.9197 against the enrolled speaker, min 0.8765
          impostor control 0.7447

    stack nine services healthy, mesh3d included

## What is still open

- **Texture baking is not available in the container.** TripoSR's bake wants
  an OpenGL context and gets `XOpenDisplay: cannot open display`, so the
  generated mesh is scored on 60,697 vertex colours rather than a 2048²
  atlas. Fixing it needs libEGL in the runtime stage, the graphics driver
  capability on the container, and `create_context(standalone=True,
  backend="egl")`. It is the one change that could move Phase 2's identity
  number of 0.3260, and until it is done that number carries an asterisk.
- **Kashmiri does not clone reliably.** It is the only language that has
  needed all three attempts and still failed the floor. The reply says so; it
  is not fixed.
- **aa and ih are 96% the same shape.** They pass the distinctness check, but
  only just, and `ih` should be the narrower mouth.
