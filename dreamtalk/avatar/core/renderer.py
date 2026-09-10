import os
import cv2
import torch
import numpy as np
from dreamtalk.avatar.core.pipeline import settings


class ImageProcessingService:
    def __init__(self, device='cuda' if torch.cuda.is_available() else 'cpu'):
        self.device = device
        self.USE_GFPGAN = False
        self.upsampler = None
        self.face_enhancer = None
        self._init_upsampler()

    def _init_upsampler(self):
        try:
            from realesrgan import RealESRGANer
            from basicsr.archs.rrdbnet_arch import RRDBNet
            model = RRDBNet(
                num_in_ch=3, num_out_ch=3,
                num_feat=64, num_block=23,
                num_grow_ch=32, scale=2
            )
            model_path = os.path.join(settings.WEIGHTS_DIR, "realesrgan/RealESRGAN_x2plus.pth")
            if os.path.exists(model_path):
                self.upsampler = RealESRGANer(
                    scale=2, model_path=model_path, model=model,
                    tile=16, tile_pad=10, pre_pad=0,
                    half=False, device=self.device,
                )
        except Exception:
            pass

    def _init_gfpgan(self):
        try:
            from gfpgan import GFPGANer
            model_path = os.path.join(settings.WEIGHTS_DIR, "gfpgan/GFPGANv1.3.pth")
            if os.path.exists(model_path) and self.upsampler is not None:
                return GFPGANer(
                    model_path=model_path, upscale=2, arch='clean',
                    channel_multiplier=2, bg_upsampler=self.upsampler,
                    device=self.device,
                )
        except Exception:
            pass
        return None

    async def enhance_face(self, image_path: str, output_path: str = None):
        if output_path is None:
            filename = os.path.basename(image_path)
            output_path = os.path.join(settings.ASSETS_OUTPUTS_DIR, f"enhanced_{filename}")

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image at {image_path}")

        h, w = img.shape[:2]
        if max(h, w) > 512:
            scale = 512 / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)))

        if self.USE_GFPGAN and self.face_enhancer is not None:
            try:
                _, _, restored_img = self.face_enhancer.enhance(
                    img, has_aligned=False, only_center_face=False, paste_back=True,
                )
                cv2.imwrite(output_path, restored_img)
                return output_path
            except Exception:
                pass

        if self.upsampler is not None:
            try:
                output, _ = self.upsampler.enhance(img, outscale=2)
                cv2.imwrite(output_path, output)
                return output_path
            except Exception:
                pass

        cv2.imwrite(output_path, img)
        return output_path

    async def align_face(self, image_path: str):
        return image_path
