# Dreamtalk - Face Engine
# Extracted from LivePortrait
import numpy as np
import cv2


def prepare_paste_back(mask_crop, M_c2o, dsize):
    """
    Prepare the mask for paste-back operation.
    mask_crop: HxWx3 mask in crop space
    M_c2o: 2x3 affine matrix from crop to original
    dsize: (width, height) of original image
    """
    mask_ori = cv2.warpAffine(mask_crop, M_c2o, dsize, flags=cv2.INTER_LINEAR)
    mask_ori_float = mask_ori.astype(np.float32) / 255.
    return mask_ori_float


def paste_back(I_p_i, M_c2o, img_ori, mask_ori_float):
    """
    Paste the generated face back to the original image.
    I_p_i: HxWx3 generated face (uint8, 256x256)
    M_c2o: 2x3 affine matrix
    img_ori: HxWx3 original image
    mask_ori_float: HxWx3 float mask
    """
    I_p_i_warped = cv2.warpAffine(I_p_i, M_c2o, (img_ori.shape[1], img_ori.shape[0]), flags=cv2.INTER_LINEAR)
    I_p_pstbk = (I_p_i_warped * mask_ori_float + img_ori * (1 - mask_ori_float)).astype(np.uint8)
    return I_p_pstbk
