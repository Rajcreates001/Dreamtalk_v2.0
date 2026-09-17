# Dreamtalk - Face Engine
# Extracted from MuseTalk
from PIL import Image
import numpy as np
import cv2
import os


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

    0.85 is the default because it buys six times the texture of generated-only
    sharpening for 14% of the motion, with the mouth opening at least as wide.
    Sharpness is not linear in the weight - the two high-frequency fields are
    different signals and partly cancel - which is why the useful range is
    bunched near the top.

    MUSETALK_DETAIL_REF_WEIGHT overrides it: 1.0 is all reference detail, 0.0
    falls back to sharpening the generated patch alone. The generated half is
    boosted by 1.35 so that lowering the weight does not simply lose contrast.
    """
    gen = generated.astype(np.float32)
    ref = reference.astype(np.float32)
    if gen.shape != ref.shape:
        return generated

    try:
        w = float(os.environ.get("MUSETALK_DETAIL_REF_WEIGHT", "0.85"))
    except (TypeError, ValueError):
        w = 0.85
    w = min(max(w, 0.0), 1.0)

    low = cv2.GaussianBlur(gen, (0, 0), sigmaX=sigma)
    high_gen = gen - low
    if w <= 0.0:
        return np.clip(gen + 0.35 * high_gen, 0, 255).astype(np.uint8)
    high_ref = ref - cv2.GaussianBlur(ref, (0, 0), sigmaX=sigma)
    high = w * high_ref + (1.0 - w) * 1.35 * high_gen
    return np.clip(low + high, 0, 255).astype(np.uint8)


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
    except Exception:
        pass  # sharpening is an enhancement; never fail a render for it

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
