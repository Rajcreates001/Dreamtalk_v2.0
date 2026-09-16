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
    """Give the regenerated patch back the skin texture the VAE removed.

    MuseTalk is pasted at native resolution - the patch is 256x256 and the
    detected face box measures 231x258 on a real source - so this is not a
    resampling artefact. The autoencoder reconstructs shape and motion
    faithfully and destroys fine texture doing it. Measured against untouched
    regions of the same rendered frame, the lower face came back at 239.6
    laplacian variance against the source's 502.6: 0.46x, and it was reported
    as "smudged and not like avatar".

    Sharpening cannot fix that. An unsharp mask only amplifies edges that
    survived, and the measurement says it tops out around 0.87 of the source.
    Detail transfer instead keeps the low frequencies from the generated
    patch, which carry the new mouth shape, and takes the high frequencies
    from the original photograph, which still has the real skin.

    sigma is the crossover, and it is a genuine trade-off rather than a free
    win: the donor frame is static, so the more of it you take the harder it
    fights the animation. Measured over a rendered sequence, sharpness as a
    fraction of the source against mouth motion as a fraction of the raw
    generated output:

        generated as-is          motion 1.00   sharpness 0.46
        unsharp mask 0.448       motion 1.05   sharpness 0.87
        detail transfer s=1.5    motion 0.91   sharpness 0.98
        detail transfer s=2.5    motion 0.84   sharpness 1.00
        detail transfer s=4.0    motion 0.74   sharpness 1.00

    s=1.5 buys essentially all the sharpness for 9% of the motion. s=4.0
    reaches the same sharpness and costs a quarter of the movement, which is
    the ghosting showing up as a number.
    """
    gen = generated.astype(np.float32)
    ref = reference.astype(np.float32)
    if gen.shape != ref.shape:
        return generated
    low = cv2.GaussianBlur(gen, (0, 0), sigmaX=sigma)
    high = ref - cv2.GaussianBlur(ref, (0, 0), sigmaX=sigma)
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

    # Match the generated patch's sharpness to the face it is being pasted
    # into, using the untouched crop as the reference. Done before the paste
    # so the soft patch never reaches the frame.
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
