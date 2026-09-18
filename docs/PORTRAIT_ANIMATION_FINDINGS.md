# Portrait animation: what works, what does not, and what was ruled out

## The complaint

The 2D render does not look alive. Measured on a 4 second clip rather than
described:

    region        motion    blinks
    left eye       0.000       0
    right eye      0.000       0
    brows          0.002       -
    forehead       0.007       -
    mouth          5.017    moving
    background     0.000       -

    65.3% of every frame is bit-identical to the source photograph

A person blinks 15-20 times a minute and never holds still. This is a
photograph with a moving mouth. No amount of mouth work reaches it, and the
lip-sync QA was written to *require* it - "PASS mouth moves, rest is still"
was the verdict on every run.

## Three real faults found and fixed in LivePortrait

It is vendored here with 608MB of weights and returned a saturated blob for
every portrait. The identity pass - warping a portrait with its own keypoints,
which must reproduce the input - was the test that localised each fault.

| fault | was | should be | effect |
|---|---|---|---|
| headpose offset | `* 3 - 1` | `* 3 - 97.5` | frontal face read as pitch 100°, yaw 96°, roll 97°; every head rotated a quarter turn before warping |
| SPADE normalization | `out = x * (1+gamma) + beta` | normalize x first | not SPADE at all. Silent because `param_free_norm` has no parameters, so a strict `load_state_dict` still passed |
| eye landmark indices | points 96..120, 6-point convention | points 0..47, 24-point contours | aperture read as 1.34 for an open eye; true value 0.225 |

    identity pass error   before 149.4 grey levels   after 1.9

LivePortrait now renders the subject photographically. That is the repair.

## Four routes to a blink, all measured, none sufficient

| route | result |
|---|---|
| `retarget_eye` module | delta 0.0008; driving it 4x lowers the lids and does not close them |
| transformed keypoints | entangled. kp 4 and kp 14 smear the whole upper face into grey rather than moving a lid |
| shipped emotion templates | `neutral.pkl` is empty - nothing varies across its 60 frames. `happy` and `sad` distort the head and shoulders instead of producing an expression. No template carries blink or head-translation data |
| expression space `exp[k]` | of 21 directions only 7 and 8 move the eyes without damage, and neither closes them at any amplitude up to 0.16, where artefacts begin |

The keypoint-to-region map, derived from this checkpoint rather than assumed:

    exp 7, 8     eyes, clean
    exp 4, 14    strong eye effect, destroys the face
    kp 7         mouth, 49%
    kp 20        jaw and mouth
    kp 2, 5, 16  jaw, large

## What a blink actually needs

LivePortrait is designed to transfer motion from a **driving video**, and every
route above is a way of faking that from a single still. The missing asset is a
short driving clip of any face blinking; with one, the repaired pipeline
transfers it onto the portrait as intended.

Until then the 2D path cannot blink. Note that the 3D path already can: the
FLAME head's blink closes 104.7% of the eyeball diameter, verified on the
shipped GLB, so the product does have a blinking avatar today - just not the
photo-realistic one.

## Do not re-litigate

`pipeline/portrait_blink.py` holds the compositor this was for: closure levels
synthesised once per render, an irregular schedule around 17 blinks a minute,
and difference-based compositing so photographic skin is kept everywhere except
the lids. It is deliberately not wired into the render path, because a lid that
lowers without closing is not a blink worth shipping.
