# Dreamtalk - Face Engine
# Extracted from SadTalker
import torch
import numpy as np
import os
import scipy.io as scio


def get_facerender_data(coeff_path, pic_path, first_coeff_path, audio_path,
                        batch_size, input_yaw_list=None, input_pitch_list=None, input_roll_list=None,
                        expression_scale=1.0, still_mode=False, preprocess='crop', size=256):
    pic_name = os.path.splitext(os.path.split(pic_path)[-1])[0] if pic_path is not None else ''
    audio_name = os.path.splitext(os.path.split(audio_path)[-1])[0] if audio_path is not None else ''

    # Load coefficients
    coeff_dict = scio.loadmat(coeff_path)
    coeff_3dmm = coeff_dict['coeff_3dmm']
    coeff_3dmm = coeff_3dmm[0][0] if coeff_3dmm.ndim == 1 else coeff_3dmm

    # First frame coefficients
    first_coeff_dict = scio.loadmat(first_coeff_path)
    first_coeff = first_coeff_dict['coeff_3dmm']
    first_coeff = first_coeff[0][0] if first_coeff.ndim == 1 else first_coeff

    return {
        'pic_path': pic_path,
        'audio_path': audio_path,
        'pic_name': pic_name,
        'audio_name': audio_name,
        'coeff_3dmm': torch.FloatTensor(coeff_3dmm).unsqueeze(0),
        'first_coeff': torch.FloatTensor(first_coeff).unsqueeze(0),
        'batch_size': batch_size,
        'expression_scale': expression_scale,
        'still_mode': still_mode,
        'preprocess': preprocess,
        'size': size,
        'input_yaw_list': input_yaw_list,
        'input_pitch_list': input_pitch_list,
        'input_roll_list': input_roll_list,
    }
