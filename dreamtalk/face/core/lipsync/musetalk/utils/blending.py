# Dreamtalk - Face Engine
# Extracted from MuseTalk
from PIL import Image
import numpy as np
import cv2


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
    mask_image = Image.fromarray(mask_array)
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
