# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Source: tools/cmd-denoise.py

import os
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks


class Denoiser:
    def __init__(self, model_path: str = None):
        if model_path is None:
            model_path = os.environ.get(
                "DENOISER_MODEL_PATH",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "models", "denoise", "speech_frcrn_ans_cirm_16k"),
            )
        if not os.path.exists(model_path):
            model_path = "damo/speech_frcrn_ans_cirm_16k"
        self.ans = pipeline(Tasks.acoustic_noise_suppression, model=model_path)

    def denoise(self, input_path: str, output_path: str = None):
        if output_path is None:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_denoised{ext}"
        self.ans(input_path, output_path=output_path)
        return output_path

    def denoise_batch(self, input_folder: str, output_folder: str):
        os.makedirs(output_folder, exist_ok=True)
        from tqdm import tqdm
        for name in tqdm(os.listdir(input_folder)):
            inp = os.path.join(input_folder, name)
            out = os.path.join(output_folder, name)
            self.ans(inp, output_path=out)
