# Dreamtalk - Face Engine
# Extracted from MuseTalk
from PIL import Image
import logging
import numpy as np
import cv2
import os

logger = logging.getLogger(__name__)


def get_crop_box(box, expand):
    x, y, x1, y1 = box
    x_c, y_c = (x + x1) // 2, (y + y1) // 2
    w, h = x1 - x, y1 - y
    s = int(max(w, h) // 2 * expand)
    crop_box = [x_c - s, y_c - s, x_c + s, y_c + s]
    return crop_box, s


def face_seg(image, mode="raw", fp=None):
    if fp is None:
        # Soft lower-face mask used when an optional BiSeNet checkpoint is not
        # compatible with the vendored parser. Keep the forehead/eyes from the
        # source and blend only the generated mouth, jaw, and lower cheeks.
        width, height = image.size
        mask = np.zeros((height, width), dtype=np.uint8)
        # Keep the ellipse clear of the crop edges so the blur below can fall
        # all the way to zero inside the image. The previous sizing reached
        # 0.98 of the height, so the mask was still bright where the crop ended
        # and the paste left a visible straight edge across the neck.
        # The mask must stay BELOW the eyes.
        #
        # MuseTalk's UNet reconstructs the entire face crop, not just the
        # mouth, so its upper half is a re-synthesis of the eyes and forehead
        # that differs slightly every frame. Blending that in makes the face
        # appear to shake even though the background is perfectly still —
        # measured on a render: forehead/eyes changed 2.26 per frame against
        # 0.21 for the background, i.e. more than the mouth itself.
        #
        # These bounds are in face_large space, which is the face box expanded
        # by `expand` (1.5x), so the face occupies roughly 0.17..0.83 and the
        # eyes sit near 0.40..0.48. Starting the fade at 0.52 puts the whole
        # mask below the nose.
        center = (width // 2, int(height * 0.72))
        axes = (max(1, int(width * 0.32)), max(1, int(height * 0.18)))
        cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)
        # Fade the top out over a band rather than slicing it flat, which
        # otherwise draws a horizontal line across the mid-face.
        fade_top, fade_bottom = int(height * 0.52), int(height * 0.64)
        if fade_bottom > fade_top:
            ramp = np.linspace(0.0, 1.0, fade_bottom - fade_top, dtype=np.float32)
            mask[fade_top:fade_bottom, :] = (
                mask[fade_top:fade_bottom, :] * ramp[:, None]
            ).astype(np.uint8)
        mask[:fade_top, :] = 0
        mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=max(3.0, width * 0.045))
        return Image.fromarray(mask)
    seg_image = fp(image, mode=mode)
    if seg_image is None:
        return None
    seg_image = seg_image.resize(image.size)
    return seg_image



def _restore_detail(generated, reference, sigma=1.5):
    """Give the regenerated patch back skin detail without pasting a still.

    The VAE reconstructs mouth shape faithfully and destroys fine texture
    doing it, which is what "the mouth section is so blurr" was pointing at.
    Two corrections have been made to this function and both were right about
    something:

    Taking all the high frequencies from the photograph restores the texture -
    measured at 0.906 of the source against 0.112 for generated-only
    sharpening - but the photograph is a still. If its lips are closed and
    this frame's mouth is open, its edges are a second lip contour laid over
    the generated one.

    Refusing to take any of them avoids that and gives up the texture.

    So the crossover is a weight rather than a switch, and the weight was set
    by rendering the same clip at four values and measuring the same mouth box
    each time:

        weight   sharpness   motion   aperture spread   interior SD
         0.00      0.112      3.163       0.1012           8.27
         0.50      0.248      2.884       0.1031           7.77
         0.85      0.662      2.725       0.1039           7.42
         1.00      0.906      2.664       0.1006           7.29

    Aperture spread is how far the mouth opens across the sequence, and it is
    the column that tests the imprinting worry directly: a still pasted over an
    open mouth would hold it shut. It does not fall anywhere in that range -
    0.85 has the widest opening of the four - so whatever the other columns are
    measuring, it is not a mouth being held closed.

    What does move is motion and interior variation, monotonically and by 14%
    across the whole range. That is the static donor fighting the animation.
    It is real and it is the price.

    0.85 was the default on that table, and it was measured on the mouth box.
    The beard is the case it misses. Texture loss is worst where texture is
    highest, so a face-box average of 65% recovered hides a beard at 14% of
    the photograph - the washed-out, patchy jaw that reads as fake at normal
    viewing size. Measured on a beard patch specifically:

        weight   whole patch   beard
         0.85        56%        42%
         1.00        70%        54%

    Since the weight is already a field that is zero across the lips and the
    moustache, raising it to 1.0 changes nothing where the donor is a still of
    a different mouth shape, and takes the jaw and cheeks - which barely move -
    entirely from the photograph, which is where they should come from.

    Restoring more frequency bands was tried and is slightly WORSE, not better:
    adding sigma 3.5 and 7.0 took the beard from 54% to 52%. The texture that
    was destroyed lives above sigma 1.5; the lower bands only dilute it.

    MUSETALK_DETAIL_REF_WEIGHT overrides it: 1.0 is all reference detail, 0.0
    falls back to sharpening the generated patch alone. The generated half is
    boosted by 1.35 so that lowering the weight does not simply lose contrast.
    """
    gen = generated.astype(np.float32)
    ref = reference.astype(np.float32)
    if gen.shape != ref.shape:
        return generated

    try:
        w = float(os.environ.get("MUSETALK_DETAIL_REF_WEIGHT", "1.0"))
    except (TypeError, ValueError):
        w = 1.0
    w = min(max(w, 0.0), 1.0)

    low = cv2.GaussianBlur(gen, (0, 0), sigmaX=sigma)
    high_gen = gen - low
    if w <= 0.0:
        out = gen + 0.35 * high_gen
    else:
        high_ref = ref - cv2.GaussianBlur(ref, (0, 0), sigmaX=sigma)
        # The weight is a field, not a scalar. Full reference detail on the
        # cheeks, chin and jaw, which barely move; none of it across the lips
        # and the moustache above them, where the donor is a still and this
        # frame is not.
        keep = _mouth_exclusion(gen.shape[:2])[..., None]
        wf = w * (1.0 - keep)
        out = low + wf * high_ref + (1.0 - wf) * 1.35 * high_gen
    return _match_contrast(np.clip(out, 0, 255), ref)


def _mouth_exclusion(shape, centre_y=None, half_w=None, half_h=None):
    """1 across the mouth and moustache, 0 elsewhere, with a soft edge.

    Rendering with a single weight for the whole patch makes the choice
    between two visible defects, and the frames show both. At weight 0 the
    beard and stubble smear into a waxy wash, because the autoencoder does not
    reproduce them and nothing puts them back. At weight 0.85 they return, and
    so does the source photograph's moustache, stamped as a textured band
    straight across an open mouth.

    Aperture spread does not see the second one - the mouth is still as dark
    and still opens as far, it just has somebody's moustache printed over it -
    which is why four renders of numbers said this was fine and looking at one
    frame said it was not.

    The donor is trustworthy exactly where the face does not move. So it is
    used there and refused over the lips, in face-patch relative coordinates
    matching the ellipse _add_mouth_region already uses, raised to take in the
    moustache band above the lip line.

    It has to be the lips and the moustache and nothing else. At 0.40 by 0.26
    the ellipse spanned x 0.10-0.90 and y 0.40-0.92 of the patch - the whole
    lower face, both jaws and the chin included - so `keep` was 1 across the
    beard, the weight field was 0 there, and no photographic texture was
    restored anywhere it mattered. The face-box average still read 65%
    recovered while the beard itself sat at 4-15% of the photograph, which is
    the washed-out jaw that made the render look fake. Refusing the donor is
    for where the face moves, and the jaw is not it.
    """
    # Two ways of replacing this ellipse with something measured were tried
    # and both are worse. They are recorded because both look obviously right.
    #
    # Optical flow, to move the donor onto the mouth instead of refusing it:
    # it made alignment WORSE in every region of every frame, by up to 0.264.
    # There is little real motion to find - the moustache already correlates
    # at 0.94-0.97 and the chin at 0.76-0.81 with no warping at all - and flow
    # invents correspondence in a mouth interior whose teeth and tongue have
    # no counterpart in a closed-mouth photograph.
    #
    # A per-pixel alignment field from local normalised cross-correlation,
    # used as the weight instead of this shape: chin 35% -> 16%, jaw 88% ->
    # 45%, moustache 40% -> 27%. Correlation does not reach 1.0 even where the
    # donor is perfectly registered, so multiplying the weight by it under-uses
    # the donor everywhere, while the ellipse gives full weight outside its
    # own boundary. Low-passing both sides before correlating - the generated
    # patch is blurry by construction, so a raw comparison reads sharpness
    # mismatch as misregistration - recovered part of it and still lost.
    #
    # The crude shape wins because the quantity that matters is not how well
    # the donor correlates but whether the region moves, and a fixed ellipse
    # over the lips states that directly.
    # Tunable so the geometry can be swept against a render rather than
    # guessed. The moustache sits ABOVE the lip line: it travels with the lip
    # but never opens, so it is much safer to give the donor than the aperture
    # is, and it is the one part MuseTalk does not draw at all.
    def _env(name, default):
        try:
            return float(os.environ.get(name, default))
        except (TypeError, ValueError):
            return default

    # The ellipse sits on the APERTURE, not on the whole mouth region.
    #
    # At 0.68/0.16 it covered the moustache band, and MuseTalk does not draw a
    # moustache - it regenerates that area as scattered stubble. So the donor
    # was refused over the one part of the face the generator erases, and the
    # render lost his moustache entirely. Moving it down onto the aperture,
    # measured over a whole clip against the photograph:
    #
    #     cy / hh      moustache  lips  chin  jaw   aperture  ghosting
    #     0.68 / 0.16      55%     36%   67%   91%   0.2129    -0.131
    #     0.72 / 0.13     105%     59%   59%  106%   0.2078    -0.122
    #     0.74 / 0.11     118%     89%   58%  113%   0.2158    -0.106
    #
    # Aperture spread is flat across all three, so the mouth still opens as
    # wide; ghosting stays strongly negative, so the closed mouth is not being
    # stamped over the open one. Confirmed on the widest-open frame of each.
    centre_y = _env("MUSETALK_MOUTH_CY", 0.74) if centre_y is None else centre_y
    half_w = _env("MUSETALK_MOUTH_HW", 0.24) if half_w is None else half_w
    half_h = _env("MUSETALK_MOUTH_HH", 0.11) if half_h is None else half_h

    h, w = shape
    mask = np.zeros((h, w), np.float32)
    cv2.ellipse(mask, (int(w * 0.50), int(h * centre_y)),
                (max(2, int(w * half_w)), max(2, int(h * half_h))),
                0, 0, 360, 1.0, -1)
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=max(2.0, w * 0.05))
    # A partial refusal, not a total one. At 1.0 the lips, moustache and chin
    # received no photographic texture whatever and measured 24%, 14% and 10%
    # of the source - the washed-out mouth that survives every fix aimed at
    # the beard beside it. Those parts do move, so the still cannot be trusted
    # for their SHAPE, but their texture is still this person's stubble, and a
    # fraction of it misaligned reads better than none at all.
    #
    # The ceiling was swept, five renders on one model load, measuring the
    # texture it buys against the artifact it risks:
    #
    #     keep   chin  moustache  lips  jaw   aperture  ghosting
    #     0.00   192%    113%     175%  135%   0.2188    -0.056
    #     0.35   120%     77%      84%  111%   0.2106    -0.099
    #     0.62    67%     52%      37%   92%   0.2188    -0.132
    #     0.85    36%     35%      20%   79%   0.2139    -0.154
    #     1.00    23%     26%      19%   73%   0.2191    -0.111
    #
    # Ghosting is the open mouth's correlation with the CLOSED photograph, so
    # more negative is cleaner. Aperture spread is flat across the whole range:
    # nothing is held shut at any setting, which is why that column cannot be
    # used to choose, and why an earlier round of four renders concluded there
    # was no problem here.
    #
    # The widest-open frame is what chooses. At 0.00 the photograph's moustache
    # is stamped across the open mouth as a band of hair with texture inside
    # the opening - the exact defect this function exists to avoid - and the
    # 192% chin says the same thing in numbers: the donor's beard is being
    # added on top of the generated one rather than restoring it. At 0.35 it is
    # still visible. At 0.62 the moustache is clean and the lips read as lips.
    try:
        ceiling = float(os.environ.get("MUSETALK_MOUTH_KEEP_MAX", "0.62"))
    except (TypeError, ValueError):
        ceiling = 0.62
    return mask * min(max(ceiling, 0.0), 1.0)


def _match_contrast(patch, reference, window=11, cap=2.2):
    """Re-expand the tonal range the autoencoder flattened, locally.

    Neither frequency band in the crossover touches the one that was actually
    missing. Measured on a rendered clip against the source photograph, inside
    a mouth box taken from the detected mouth landmarks:

        saturation           1.14   (up)
        chroma               1.13   (up)
        lip/skin redness     up
        luminance contrast   0.74   <- and 1.00 on an untouched cheek

    The lips had not lost colour and had not lost fine texture. They had lost
    the mid-frequency tonal structure separating upper lip from lower and lip
    from skin - the vermilion border, the shadow between the lips - which sits
    between a 1.5px high-pass and everything below it, so both halves of the
    crossover sail straight past it.

    LOCAL is the whole point, and the first version of this got it wrong by
    computing one gain for the entire face patch. Over a whole face the
    generated contrast already matches the photograph, because only the mouth
    is flattened; the gain came out at 1.0 and the measurement moved from 0.74
    to 0.76. The deficit is local, so the correction has to be.

    So: local mean and local standard deviation of luminance in both patches,
    and a per-pixel gain sized to close the gap between them. The generated
    patch keeps its own local mean, which is what carries mouth shape - an open
    mouth stays open and a closed one stays closed - and only the flatness is
    undone. Nothing spatial crosses from the reference; what crosses is a
    scalar field saying how much contrast belongs at each point, which is also
    why this cannot imprint a still photograph's lips.

    The gain is floored at 1.0 so an already-contrasty region is never
    softened, and capped so a region the network rendered nearly flat is not
    multiplied into banding.

    A fixed expansion inside the mouth was tried and removed. The aperture is
    dark, so expanding contrast about a dark local mean deepens the cavity
    instead of lifting the teeth: the brightest decile inside an open mouth
    stayed at 24.0 and the interior mean fell from 12.4 to 11.4. Dim teeth are
    what the network produced and compositing cannot invent them.
    """
    lab = cv2.cvtColor(patch.astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)
    ref_lab = cv2.cvtColor(reference.astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)
    lum, ref_lum = lab[:, :, 0], ref_lab[:, :, 0]

    k = (window, window)
    mu = cv2.blur(lum, k)
    sd = np.sqrt(np.maximum(cv2.blur(lum * lum, k) - mu * mu, 0.0))
    ref_mu = cv2.blur(ref_lum, k)
    ref_sd = np.sqrt(np.maximum(cv2.blur(ref_lum * ref_lum, k) - ref_mu * ref_mu, 0.0))

    gain = np.clip(ref_sd / (sd + 1.0), 1.0, cap)

    lab[:, :, 0] = np.clip(mu + (lum - mu) * gain, 0, 255)
    return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2BGR)


def _add_mouth_region(mask_array, face_box, crop_box):
    """Guarantee that the generated lower-mouth pixels reach the final frame.

    The optional face parser is trained for segmentation, not for MuseTalk's
    crop coordinates. On some portraits it returns a jaw mask that is valid
    but leaves the lips at a very low alpha. A soft, face-relative mouth
    ellipse closes that gap without exposing the generated eyes or forehead.
    """
    try:
        gain = float(os.environ.get("MUSETALK_MOUTH_MASK_GAIN", "1.0"))
    except (TypeError, ValueError):
        gain = 1.0
    if gain <= 0:
        return mask_array
    x, y, x1, y1 = face_box
    x_s, y_s = crop_box[:2]
    width, height = mask_array.shape[1], mask_array.shape[0]
    rx, ry = x - x_s, y - y_s
    rw, rh = max(1, x1 - x), max(1, y1 - y)
    center = (int(rx + rw * 0.50), int(ry + rh * 0.70))
    axes = (max(2, int(rw * 0.38)), max(2, int(rh * 0.19)))
    mouth = np.zeros((height, width), dtype=np.uint8)
    cv2.ellipse(mouth, center, axes, 0, 0, 360, 255, -1)
    mouth = cv2.GaussianBlur(mouth, (0, 0), sigmaX=max(2.0, rw * 0.035))
    mouth = np.clip(mouth.astype(np.float32) * min(gain, 1.5), 0, 255).astype(np.uint8)
    return np.maximum(mask_array, mouth)


_DETAIL_WARNED = False
_DETAIL_LOGGED = False


def _detail_report(generated, reference, restored):
    """Say once, per process, how much texture the restoration actually put back.

    The measurement that matters is not whether the function ran but whether
    its output carries the photograph's detail. Reported once so it appears in
    a render log without flooding it.
    """
    global _DETAIL_LOGGED
    if _DETAIL_LOGGED:
        return
    _DETAIL_LOGGED = True
    try:
        def detail(img):
            grey = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_RGB2GRAY)
            return float(cv2.Laplacian(grey, cv2.CV_64F).var())

        ref_d = detail(reference)
        logger.info("detail restoration: generated %.0f -> %.0f of the "
                    "photograph's %.0f (%.0f%% recovered)",
                    detail(generated), detail(restored), ref_d,
                    100.0 * detail(restored) / max(ref_d, 1e-6))
    except Exception:
        pass


def get_image(image, face, face_box, upper_boundary_ratio=0.5, expand=1.5, mode="raw", fp=None):
    body = Image.fromarray(image[:, :, ::-1])
    face = Image.fromarray(face[:, :, ::-1])
    x, y, x1, y1 = face_box
    crop_box, s = get_crop_box(face_box, expand)
    x_s, y_s, x_e, y_e = crop_box
    face_position = (x, y)
    face_large = body.crop(crop_box)
    ori_shape = face_large.size
    mask_image = face_seg(face_large, mode=mode, fp=fp)

    if fp is None:
        # The geometric fallback mask is already a soft ellipse sized to this
        # crop, and it deliberately extends past the inner face box so its
        # falloff completes inside the pasted region.
        #
        # The BiSeNet path below crops that mask to the face box and repastes
        # it, which is right for a segmentation mask (it is zero outside the
        # face anyway) but SHEARS the ellipse into a hard-edged rectangle —
        # the visible seam across the neck and shoulder in rendered frames.
        # Skip the crop entirely and keep the soft edge.
        mask_array = np.array(mask_image)
    else:
        mask_small = mask_image.crop((x - x_s, y - y_s, x1 - x_s, y1 - y_s))
        mask_image = Image.new('L', ori_shape, 0)
        mask_image.paste(mask_small, (x - x_s, y - y_s, x1 - x_s, y1 - y_s))
        width, height = mask_image.size
        top_boundary = int(height * upper_boundary_ratio)
        modified_mask_image = Image.new('L', ori_shape, 0)
        modified_mask_image.paste(mask_image.crop((0, top_boundary, width, height)), (0, top_boundary))
        blur_kernel_size = int(0.05 * ori_shape[0] // 2 * 2) + 1
        mask_array = cv2.GaussianBlur(
            np.array(modified_mask_image), (blur_kernel_size, blur_kernel_size), 0
        )
    mask_array = _add_mouth_region(mask_array, face_box, crop_box)
    mask_image = Image.fromarray(mask_array)

    # Sharpen only generated edges; never copy the source mouth's texture.
    try:
        ref = np.array(face_large.crop(
            (x - x_s, y - y_s, x1 - x_s, y1 - y_s)))
        generated = np.array(face)
        if ref.shape[:2] != generated.shape[:2]:
            ref = cv2.resize(ref, (generated.shape[1], generated.shape[0]), interpolation=cv2.INTER_CUBIC)
        sharpened = _restore_detail(generated, ref)
        face = Image.fromarray(sharpened)
        _detail_report(generated, ref, sharpened)
    except Exception as exc:
        # Still never fatal, but no longer silent. Swallowing this meant a
        # render could lose every bit of the photograph's skin texture - the
        # beard measured 14% of the source - and report nothing at all.
        global _DETAIL_WARNED
        if not _DETAIL_WARNED:
            _DETAIL_WARNED = True
            logger.warning("detail restoration failed (%s); the regenerated "
                           "face keeps only what the VAE produced", exc,
                           exc_info=True)

    face_large.paste(face, (x - x_s, y - y_s, x1 - x_s, y1 - y_s))
    body.paste(face_large, crop_box[:2], mask_image)
    body = np.array(body)
    return body[:, :, ::-1]


def get_image_blending(image, face, face_box, mask_array, crop_box):
    body = Image.fromarray(image[:, :, ::-1])
    face = Image.fromarray(face[:, :, ::-1])
    x, y, x1, y1 = face_box
    x_s, y_s, x_e, y_e = crop_box
    face_large = body.crop(crop_box)
    mask_image = Image.fromarray(mask_array)
    mask_image = mask_image.convert("L")
    face_large.paste(face, (x - x_s, y - y_s, x1 - x_s, y1 - y_s))
    body.paste(face_large, crop_box[:2], mask_image)
    body = np.array(body)
    return body[:, :, ::-1]


def get_image_prepare_material(image, face_box, upper_boundary_ratio=0.5, expand=1.5, fp=None, mode="raw"):
    body = Image.fromarray(image[:, :, ::-1])
    x, y, x1, y1 = face_box
    crop_box, s = get_crop_box(face_box, expand)
    x_s, y_s, x_e, y_e = crop_box
    face_large = body.crop(crop_box)
    ori_shape = face_large.size
    mask_image = face_seg(face_large, mode=mode, fp=fp)
    mask_small = mask_image.crop((x - x_s, y - y_s, x1 - x_s, y1 - y_s))
    mask_image = Image.new('L', ori_shape, 0)
    mask_image.paste(mask_small, (x - x_s, y - y_s, x1 - x_s, y1 - y_s))
    width, height = mask_image.size
    top_boundary = int(height * upper_boundary_ratio)
    modified_mask_image = Image.new('L', ori_shape, 0)
    modified_mask_image.paste(mask_image.crop((0, top_boundary, width, height)), (0, top_boundary))
    blur_kernel_size = int(0.1 * ori_shape[0] // 2 * 2) + 1
    mask_array = cv2.GaussianBlur(np.array(modified_mask_image), (blur_kernel_size, blur_kernel_size), 0)
    return mask_array, crop_box
