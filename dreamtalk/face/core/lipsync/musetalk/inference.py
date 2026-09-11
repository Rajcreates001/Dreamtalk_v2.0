# Dreamtalk - Face Engine
# Extracted from MuseTalk
import os
import cv2
import math
import copy
import torch
import glob
import shutil
import pickle
import argparse
import logging
import numpy as np
import subprocess
from tqdm import tqdm
from omegaconf import OmegaConf
from transformers import WhisperConfig, WhisperModel

logger = logging.getLogger("dreamtalk.face.musetalk.inference")

from dreamtalk.face.core.lipsync.musetalk.utils.blending import get_image
from dreamtalk.face.core.lipsync.musetalk.utils.face_parsing.model import FaceParsing
from dreamtalk.face.core.lipsync.musetalk.utils.audio_processor import AudioProcessor
from dreamtalk.face.core.lipsync.musetalk.utils.utils import get_file_type, get_video_fps, datagen, load_all_model
from dreamtalk.face.core.lipsync.musetalk.utils.preprocessing import get_landmark_and_bbox, read_imgs, coord_placeholder


class MuseTalkInference:
    def __init__(self, config=None):
        self.config = config
        self.vae = None
        self.unet = None
        self.pe = None
        self.audio_processor = None
        self.whisper = None
        self.fp = None
        self.timesteps = None
        self.weight_dtype = None
        self.device = None

    def load_models(self, unet_model_path, vae_type, unet_config, whisper_dir, device, use_float16=False, version="v15"):
        self.device = device
        vae, unet, pe = load_all_model(
            unet_model_path=unet_model_path,
            vae_type=vae_type,
            unet_config=unet_config,
            device=device
        )
        self.timesteps = torch.tensor([0], device=device)

        if use_float16:
            pe = pe.half()
            vae.vae = vae.vae.half()
            unet.model = unet.model.half()

        pe = pe.to(device)
        vae.vae = vae.vae.to(device)
        unet.model = unet.model.to(device)

        self.vae = vae
        self.unet = unet
        self.pe = pe
        self.weight_dtype = unet.model.dtype

        self.audio_processor = AudioProcessor(feature_extractor_path=whisper_dir)
        try:
            self.whisper = WhisperModel.from_pretrained(whisper_dir, local_files_only=True)
        except (OSError, ValueError):
            checkpoint = os.path.join(whisper_dir, "pytorch_model.bin")
            if not os.path.exists(checkpoint):
                raise
            self.whisper = WhisperModel(WhisperConfig())
            state = torch.load(checkpoint, map_location="cpu", weights_only=True)
            if state and all(key.startswith("model.") for key in state):
                state = {key.removeprefix("model."): value for key, value in state.items()}
            self.whisper.load_state_dict(state)
        self.whisper = self.whisper.to(device=device, dtype=self.weight_dtype).eval()
        self.whisper.requires_grad_(False)

        try:
            if version == "v15":
                self.fp = FaceParsing(
                    left_cheek_width=self.config.left_cheek_width if self.config else 90,
                    right_cheek_width=self.config.right_cheek_width if self.config else 90
                )
            else:
                self.fp = FaceParsing()
        except Exception as exc:
            # Some older MuseTalk bundles include a BiSeNet checkpoint for a
            # different face-parser architecture. Lip generation remains
            # valid; blending.py supplies a soft geometric jaw mask.
            logger.warning("MuseTalk face parser unavailable; using geometric blend mask: %s", exc)
            self.fp = None

    def _run_ffmpeg(self, cmd: list, desc: str = "") -> None:
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg {desc} failed: {e.stderr}")
            raise

    @torch.no_grad()
    def inference(self, video_path, audio_path, bbox_shift=0, fps=25, batch_size=8,
                  extra_margin=10, parsing_mode="jaw", version="v15",
                  audio_padding_length_left=2, audio_padding_length_right=2,
                  result_dir="./results", output_vid_name=None, use_saved_coord=False,
                  saved_coord=False, hw_video_encode=False):

        input_basename = os.path.basename(video_path).split('.')[0]
        audio_basename = os.path.basename(audio_path).split('.')[0]
        output_basename = f"{input_basename}_{audio_basename}"

        temp_dir = os.path.join(result_dir, version)
        os.makedirs(temp_dir, exist_ok=True)

        result_img_save_path = os.path.join(temp_dir, output_basename)
        crop_coord_save_path = os.path.join(result_dir, "../", input_basename + ".pkl")
        os.makedirs(result_img_save_path, exist_ok=True)

        if output_vid_name is None:
            output_vid_name = os.path.join(temp_dir, output_basename + ".mp4")
        else:
            output_vid_name = os.path.join(temp_dir, output_vid_name)

        # Extract frames
        save_dir_full = None
        if get_file_type(video_path) == "video":
            save_dir_full = os.path.join(temp_dir, input_basename)
            os.makedirs(save_dir_full, exist_ok=True)
            self._run_ffmpeg(
                ["ffmpeg", "-v", "fatal", "-i", video_path, "-start_number", "0",
                 f"{save_dir_full}/%08d.png"],
                "frame extraction",
            )
            input_img_list = sorted(glob.glob(os.path.join(save_dir_full, '*.[jpJP][pnPN]*[gG]')))
            fps = get_video_fps(video_path)
        elif get_file_type(video_path) == "image":
            input_img_list = [video_path]
        elif os.path.isdir(video_path):
            input_img_list = glob.glob(os.path.join(video_path, '*.[jpJP][pnPN]*[gG]'))
            input_img_list = sorted(input_img_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
        else:
            raise ValueError(f"{video_path} should be a video file, an image file or a directory of images")

        # Audio features
        whisper_input_features, librosa_length = self.audio_processor.get_audio_feature(audio_path)
        whisper_chunks = self.audio_processor.get_whisper_chunk(
            whisper_input_features, self.device, self.weight_dtype, self.whisper, librosa_length,
            fps=fps, audio_padding_length_left=audio_padding_length_left,
            audio_padding_length_right=audio_padding_length_right,
        )

        # Preprocess
        if os.path.exists(crop_coord_save_path) and use_saved_coord:
            with open(crop_coord_save_path, 'rb') as f:
                coord_list = pickle.load(f)
            frame_list = read_imgs(input_img_list)
        else:
            coord_list, frame_list = get_landmark_and_bbox(input_img_list, bbox_shift)
            if saved_coord:
                with open(crop_coord_save_path, 'wb') as f:
                    pickle.dump(coord_list, f)

        input_latent_list = []
        for bbox, frame in zip(coord_list, frame_list):
            if bbox == coord_placeholder:
                continue
            x1, y1, x2, y2 = bbox
            if version == "v15":
                y2 = y2 + extra_margin
                y2 = min(y2, frame.shape[0])
            crop_frame = frame[y1:y2, x1:x2]
            crop_frame = cv2.resize(crop_frame, (256, 256), interpolation=cv2.INTER_LANCZOS4)
            latents = self.vae.get_latents_for_unet(crop_frame)
            input_latent_list.append(latents)

        # Smooth first/last frames
        frame_list_cycle = frame_list + frame_list[::-1]
        coord_list_cycle = coord_list + coord_list[::-1]
        input_latent_list_cycle = input_latent_list + input_latent_list[::-1]

        # Batch inference
        video_num = len(whisper_chunks)
        gen = datagen(
            whisper_chunks=whisper_chunks,
            vae_encode_latents=input_latent_list_cycle,
            batch_size=batch_size,
            delay_frame=0,
            device=self.device,
        )

        res_frame_list = []
        for whisper_batch, latent_batch in tqdm(gen, total=int(np.ceil(float(video_num) / batch_size))):
            audio_feature_batch = self.pe(whisper_batch)
            latent_batch = latent_batch.to(dtype=self.weight_dtype)
            pred_latents = self.unet.model(latent_batch, self.timesteps, encoder_hidden_states=audio_feature_batch).sample
            recon = self.vae.decode_latents(pred_latents)
            for res_frame in recon:
                res_frame_list.append(res_frame)

        # Pad to original
        for i, res_frame in enumerate(tqdm(res_frame_list)):
            bbox = coord_list_cycle[i % len(coord_list_cycle)]
            ori_frame = copy.deepcopy(frame_list_cycle[i % len(frame_list_cycle)])
            x1, y1, x2, y2 = bbox
            if version == "v15":
                y2 = y2 + extra_margin
                y2 = min(y2, frame_list[0].shape[0])
            try:
                res_frame = cv2.resize(res_frame.astype(np.uint8), (x2 - x1, y2 - y1))
            except:
                continue
            if version == "v15":
                combine_frame = get_image(ori_frame, res_frame, [x1, y1, x2, y2], mode=parsing_mode, fp=self.fp)
            else:
                combine_frame = get_image(ori_frame, res_frame, [x1, y1, x2, y2], fp=self.fp)
            cv2.imwrite(f"{result_img_save_path}/{str(i).zfill(8)}.png", combine_frame)

        # Assemble video with optional HW encoding
        temp_vid_path = f"{temp_dir}/temp_{input_basename}_{audio_basename}.mp4"
        codec = "h264_nvenc" if hw_video_encode else "libx264"
        preset = "p4" if hw_video_encode else "medium"
        self._run_ffmpeg(
            ["ffmpeg", "-y", "-v", "warning", "-r", str(fps), "-f", "image2",
             "-i", f"{result_img_save_path}/%08d.png",
             "-vcodec", codec, "-preset", preset, "-vf", "format=yuv420p", "-crf", "18",
             temp_vid_path],
            "video assembly",
        )

        self._run_ffmpeg(
            ["ffmpeg", "-y", "-v", "warning", "-i", audio_path, "-i", temp_vid_path,
             "-c:v", "copy", "-c:a", "aac", "-map", "0:a:0", "-map", "1:v:0", "-shortest",
             output_vid_name],
            "audio muxing",
        )

        shutil.rmtree(result_img_save_path)
        os.remove(temp_vid_path)
        if save_dir_full and os.path.exists(save_dir_full):
            shutil.rmtree(save_dir_full)

        return output_vid_name
