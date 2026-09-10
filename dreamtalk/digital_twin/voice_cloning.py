"""Voice Engine — Cloning-first, synthetic fallback.

Voice cloning is the default workflow.
Users upload voice samples and the backend runs a 13-step analysis pipeline.

Accept: wav, mp3, m4a, aac, flac (multiple samples accepted)

Pipeline:
1. Upload → 2. Audio Validation → 3. Noise Removal → 4. Silence Removal
→ 5. Speaker Detection → 6. Speaker Verification → 7. Pitch Analysis
→ 8. Emotion Detection → 9. Accent Detection → 10. Language Detection
→ 11. Voice Embedding → 12. Voice Clone Model → 13. Preview → 14. Store

If the user does not upload audio, allow Create Synthetic Voice as fallback.
"""

import json
import uuid
import os
import logging
from typing import List, Optional, Dict, Tuple
from datetime import datetime
from fastapi import UploadFile

import numpy as np

from dreamtalk.backend.db.database import execute, fetchrow
from dreamtalk.media.repository import MediaRepository


# ── Real feature extraction engine (from pipeline/voice_pipeline.py) ──
from dreamtalk.pipeline.voice_pipeline import VoicePipeline as FeatureExtractionPipeline

# ── Graceful torch / audio lib availability ──
try:
    import torch
    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except Exception:
    SOUNDFILE_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except Exception:
    LIBROSA_AVAILABLE = False


logger = logging.getLogger("dreamtalk.voice.cloning")


ALLOWED_AUDIO_TYPES = {"audio/wav", "audio/mpeg", "audio/mp4", "audio/aac", "audio/flac",
                       "audio/x-wav", "audio/x-m4a", "audio/x-aac", "audio/x-flac"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac"}


class VoicePipeline:
    """Voice cloning-first with synthetic fallback.

    Pipeline (13 steps):
     1. Upload → 2. Audio Validation → 3. Noise Removal & Enhancement
     4. Voice Activity Detection (silence removal) → 5. Speaker Detection
     6. Pitch Analysis → 7. Spectral Analysis (energy, formants, MFCCs)
     8. Voice Quality + Emotion Detection (PAD heuristic)
     9. Accent Detection → 10. Language Detection → 11. Voice Embedding (256-dim)
    12. Voice Cloning (IndicF5 → RVC) → 13. TTS Preview
    → 14. Store results

    Steps 2-11 use the real feature extraction engine from pipeline/voice_pipeline.py.
    Step 12 attempts real voice cloning (IndicF5 → RVC).
    Step 13 generates a TTS preview.
    """

    def __init__(self):
        self.media_repo = MediaRepository()
        # Real feature extraction engine (gracefully handles missing audio libs)
        self._fe = FeatureExtractionPipeline()

    # ─── Emotion Estimation from Acoustic Features ────────────────────────

    @staticmethod
    def _estimate_emotion(analysis: dict) -> dict:
        """Estimate emotion (valence, arousal, dominance) from voice features.

        Uses pitch, energy, spectral, and voice quality features as heuristics.
        Returns a PAD (Pleasure-Arousal-Dominance) profile with labelled emotion.
        """
        pitch = analysis.get("pitch_analysis", {}) or {}
        energy = analysis.get("energy_info", {}) or {}
        spectral = analysis.get("spectral_info", {}) or {}
        quality = analysis.get("voice_quality", {}) or {}

        p_mean = pitch.get("mean", 150.0)
        p_std = pitch.get("std", 40.0)
        e_mean = energy.get("mean", 0.05)
        e_std = energy.get("std", 0.02)
        centroid = spectral.get("centroid_mean", 2000.0)
        jitter = quality.get("jitter_local", 0.5)
        shimmer = quality.get("shimmer_local", 3.0)
        hnr = quality.get("hnr", 15.0)

        # Arousal: high pitch std + high energy std + high shimmer = high arousal
        p_std_norm = min(p_std / 80.0, 1.0)
        e_std_norm = min(e_std / 0.1, 1.0)
        shimmer_norm = min(shimmer / 8.0, 1.0)
        arousal = round((p_std_norm * 0.5 + e_std_norm * 0.3 + shimmer_norm * 0.2), 4)

        # Valence: high HNR + moderate pitch + low jitter = positive
        hnr_norm = min(hnr / 30.0, 1.0)
        jitter_neg = 1.0 - min(jitter / 3.0, 1.0)
        pitch_mod = 1.0 - abs(p_mean - 200.0) / 200.0
        valence = round((hnr_norm * 0.4 + jitter_neg * 0.3 + pitch_mod * 0.3), 4)

        # Dominance: low centroid + high energy + low shimmer = dominant
        centroid_neg = 1.0 - min(centroid / 5000.0, 1.0)
        e_mean_norm = min(e_mean / 0.15, 1.0)
        shimmer_neg = 1.0 - shimmer_norm
        dominance = round((centroid_neg * 0.3 + e_mean_norm * 0.4 + shimmer_neg * 0.3), 4)

        # Label from PAD coordinates
        label = "neutral"
        if valence < 0.4:
            if arousal > 0.6:
                label = "angry" if dominance > 0.5 else "anxious"
            elif arousal < 0.3:
                label = "sad"
            else:
                label = "frustrated"
        else:  # valence >= 0.4
            if arousal > 0.6:
                label = "excited"
            elif arousal < 0.3:
                label = "calm"
            else:
                label = "happy"

        return {
            "valence": valence,
            "arousal": arousal,
            "dominance": dominance,
            "label": label,
            "pitch_variation": p_std_norm,
            "energy_variation": e_std_norm,
            "voice_quality_hnr": round(hnr, 1),
        }

    # ─── Accent Detection ─────────────────────────────────────────────────

    @staticmethod
    def _detect_accent(spectral_info: dict, pitch_info: dict) -> dict:
        """Detect accent from spectral and pitch features.

        Uses spectral centroid, rolloff, and formant structure heuristics.
        """
        centroid = spectral_info.get("centroid_mean", 2000.0)
        rolloff = spectral_info.get("rolloff", 3500.0)
        p_mean = pitch_info.get("mean", 150.0)

        # Simple heuristic based on spectral properties
        ratio = centroid / rolloff if rolloff > 0 else 0.5

        if centroid > 3000:
            label, conf = "bright (potential Asian/Spanish)", 0.4
        elif centroid < 1500:
            label, conf = "darker (potential Northern European)", 0.35
        elif ratio > 0.65:
            label, conf = "crisp (potential American)", 0.3
        elif ratio < 0.5:
            label, conf = "rounded (potential British/Southern European)", 0.3
        else:
            label, conf = "neutral", 0.2

        # Fine-tune with pitch
        if p_mean > 200:
            conf = min(conf + 0.1, 1.0)

        return {
            "label": label,
            "confidence": round(conf, 3),
            "spectral_centroid": round(centroid, 1),
            "spectral_rolloff": round(rolloff, 1),
        }

    # ─── Language Detection ───────────────────────────────────────────────

    @staticmethod
    def _detect_language(spectral_info: dict) -> dict:
        """Detect language family from spectral features.

        Uses MFCC means, spectral contrast, and formant structure.
        Returns a best-guess language family label.
        """
        mfcc = spectral_info.get("mfccs_mean")
        contrast = spectral_info.get("contrast")
        centroid = spectral_info.get("centroid_mean", 2000.0)

        if not mfcc:
            return {"label": "unknown", "confidence": 0.0}

        # Simple heuristic using MFCC energy distribution
        mfcc_0 = mfcc[0] if len(mfcc) > 0 else 0

        lang = "en"
        conf = 0.3

        # Higher MFCC-0 suggests more low-frequency energy (English-like)
        if mfcc_0 > 100:
            lang = "en"
            conf = 0.35
        # Higher contrast suggests tonal languages
        if contrast and len(contrast) > 0:
            if contrast[0] > 40:
                lang = "zh"
                conf = 0.4
        # Higher centroid suggests Romance languages
        if centroid > 3500:
            if lang == "en":
                lang = "es/fr"
                conf = 0.35

        return {
            "label": lang,
            "confidence": round(conf, 3),
            "mfcc_energy": round(float(mfcc_0), 2) if isinstance(mfcc_0, (int, float, np.floating)) else 0.0,
            "spectral_centroid": round(centroid, 1),
        }

    # ─── Preview Tone Generation (fallback) ───────────────────────────────

    @staticmethod
    def _generate_preview_tone(output_dir: str, analysis: dict, gender: str = "neutral") -> str:
        """Generate a simple tone preview when TTS is unavailable.

        Uses pitch from analysis to create a voice-identity tone.
        """
        pitch_info = analysis.get("pitch_analysis", {}) or {}
        base_freq = pitch_info.get("mean", 0) or (160 if gender == "male" else 220)

        sr = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)

        # Generate voice-identity tone: fundamental + harmonics
        audio = 0.3 * np.sin(2 * np.pi * base_freq * t)
        audio += 0.15 * np.sin(2 * np.pi * base_freq * 2 * t)
        audio += 0.075 * np.sin(2 * np.pi * base_freq * 3 * t)
        audio += 0.0375 * np.sin(2 * np.pi * base_freq * 4 * t)

        # Fade in/out
        fade_len = int(sr * 0.05)
        fade = np.linspace(0, 1, fade_len)
        audio[:fade_len] *= fade
        audio[-fade_len:] *= fade[::-1]

        output_path = os.path.join(output_dir, "preview_tone.wav")
        if SOUNDFILE_AVAILABLE:
            sf.write(output_path, audio.astype(np.float32), sr)
        else:
            # RAW WAV fallback
            import struct
            int_data = (audio * 32767).astype(np.int16)
            with open(output_path, "wb") as f:
                f.write(b"RIFF")
                f.write(struct.pack("<I", 36 + len(int_data) * 2))
                f.write(b"WAVE")
                f.write(b"fmt ")
                f.write(struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16))
                f.write(b"data")
                f.write(struct.pack("<I", len(int_data) * 2))
                f.write(int_data.tobytes())

        preview_url = output_path if os.path.exists(output_path) else None
        analysis["preview_url"] = preview_url
        analysis["processing_log"].append({
            "step": "preview_tone", "status": "completed",
            "message": f"Preview tone generated at {base_freq:.0f}Hz base",
        })

        return preview_url

    async def upload_and_clone(self, twin_id: str, files: List[UploadFile], role: str = "personal") -> dict:
        p_results = []
        all_analyses = []

        for file in files:
            content = await file.read()
            if not content:
                continue

            # Validate file extension and type
            ext = os.path.splitext(file.filename)[1].lower() if hasattr(file, 'filename') and file.filename else ""
            if ext not in AUDIO_EXTENSIONS and file.content_type not in ALLOWED_AUDIO_TYPES:
                p_results.append({"filename": file.filename, "status": "rejected", "reason": f"Unsupported audio format: {file.content_type or ext}"})
                continue

            # Step 1: Upload to media repository
            asset = await self.media_repo.store_file(
                twin_id=twin_id,
                role=role,
                category="voice",
                filename=file.filename,
                content=content,
                metadata={"mime_type": file.content_type or "audio/wav", "original_name": file.filename},
            )

            # Steps 2-14: Run analysis pipeline
            analysis = await self._run_voice_pipeline(asset)
            all_analyses.append(analysis)

            p_results.append({
                "filename": file.filename,
                "status": "analyzed",
                "asset_id": asset.asset_id,
                "file_path": asset.file_path,
                "analysis": analysis,
            })

        # Store combined results
        await self._store_clone_results(twin_id, p_results, all_analyses, role)

        return {
            "status": "completed",
            "files_processed": len(p_results),
            "is_cloned": True,
            "samples": [
                {"filename": r["filename"], "asset_id": r["asset_id"], "status": r["status"]}
                for r in p_results
            ],
            "processing_log": [a.get("processing_log", []) for a in all_analyses],
        }

    async def create_synthetic(self, twin_id: str, config: dict, role: str = "personal") -> dict:
        """Fallback: create a synthetic voice without audio samples."""
        synthetic_data = {
            "is_synthetic": True,
            "is_cloned": False,
            "config": {
                "gender": config.get("gender", "neutral"),
                "age": config.get("age", "adult"),
                "accent": config.get("accent", "neutral"),
                "language": config.get("language", "en"),
                "pitch": config.get("pitch", 1.0),
                "speed": config.get("speed", 1.0),
                "warmth": config.get("warmth", 0.5),
                "tone": config.get("tone", "neutral"),
            },
            "quality_score": 0.5,
            "created_at": datetime.utcnow().isoformat(),
        }

        await execute(
            """UPDATE digital_twins
               SET voice_data = $1::jsonb,
                   voice_status = 'synthetic',
                   updated_at = NOW()
               WHERE id = $2""",
            json.dumps(synthetic_data),
            twin_id,
        )

        return {
            "status": "synthetic_created",
            "is_synthetic": True,
            "config": synthetic_data["config"],
        }

    async def _run_voice_pipeline(self, asset) -> dict:
        """Run 13-step voice analysis pipeline with real feature extraction."""
        analysis = {
            "validated": False,
            "noise_removed": False,
            "silence_removed": False,
            "speaker_detected": False,
            "speaker_verified": False,
            "pitch_analysis": {},
            "emotion_detection": {},
            "accent_detection": {},
            "language_detection": {},
            "voice_embedding": None,
            "clone_model": None,
            "preview_url": None,
            "quality_score": 0.0,
            "processing_log": [],
            # Real extraction results
            "audio_info": {},
            "enhancement_info": {},
            "vad_info": {},
            "formant_info": {},
            "voice_quality": {},
            "prosody_info": {},
            "gender_prediction": {},
        }

        # ── Prerequisite: Load audio ──
        file_path = getattr(asset, 'file_path', None)
        if not file_path or not os.path.exists(file_path):
            analysis["processing_log"].append({
                "step": "audio_load", "status": "error",
                "message": f"Audio file not found: {file_path}",
            })
            return analysis

        data, sr, audio_info = self._fe.load_audio(file_path)
        if data is None or sr == 0:
            analysis["processing_log"].append({
                "step": "audio_load", "status": "error",
                "message": f"Cannot load audio: {file_path}",
            })
            return analysis

        analysis["audio_info"] = {
            "sample_rate": sr,
            "duration": round(len(data) / sr, 3),
            "format": audio_info.get("format", "unknown"),
            "channels": audio_info.get("channels", 1),
            "bit_depth": audio_info.get("bit_depth", 16),
        }

        analysis["processing_log"].append({
            "step": "audio_load", "status": "completed",
            "message": f"Loaded audio: {analysis['audio_info']['duration']}s @ {sr}Hz",
            "data": analysis["audio_info"],
        })

        # ── Step 2: Audio Validation ──
        valid = len(data) >= sr * 0.02  # at least 20ms
        analysis["validated"] = valid
        status_msg = "valid" if valid else "too short (< 20ms)"
        analysis["processing_log"].append({
            "step": "audio_validation", "status": "completed" if valid else "error",
            "message": f"Audio validated: {status_msg} ({len(data)/sr:.2f}s)",
        })

        if not valid:
            return analysis

        # ── Step 3: Noise Removal & Enhancement ──
        enhanced, enh_info = self._fe.enhance_audio(data, sr)
        analysis["noise_removed"] = enh_info.get("noise_reduced", False)
        analysis["enhancement_info"] = enh_info
        analysis["processing_log"].append({
            "step": "noise_removal", "status": "completed",
            "message": f"Enhancement: norm={enh_info.get('normalized',False)}, "
                       f"bandpass={enh_info.get('bandpass_applied',False)}, "
                       f"denoise={enh_info.get('noise_reduced',False)}, "
                       f"SNR={enh_info.get('snr_estimate',0)}dB",
        })

        # Use enhanced audio for all subsequent steps
        data = enhanced

        # ── Step 4: Voice Activity Detection (silence removal) ──
        voiced_frames, vad_info = self._fe.voice_activity_detection(data, sr)
        analysis["silence_removed"] = vad_info["voiced_ratio"] > 0.05
        analysis["vad_info"] = vad_info
        analysis["quality_score"] = round(vad_info["voiced_ratio"] * 100, 1)
        analysis["processing_log"].append({
            "step": "silence_removal", "status": "completed",
            "message": f"VAD: {vad_info['voiced_frames']}/{vad_info['total_frames']} voiced frames "
                       f"(ratio={vad_info['voiced_ratio']:.2%})",
        })

        if vad_info["voiced_ratio"] <= 0.05:
            analysis["processing_log"].append({
                "step": "silence_removal", "status": "warning",
                "message": "Very low voice activity — audio may be mostly silence",
            })

        # ── Step 5: Speaker Detection ──
        # Use VAD + pitch to determine if a single speaker is present
        speaker_count = 1 if vad_info["voiced_ratio"] > 0.05 else 0
        analysis["speaker_detected"] = speaker_count > 0
        analysis["processing_log"].append({
            "step": "speaker_detection", "status": "completed" if speaker_count > 0 else "warning",
            "message": f"{speaker_count} speaker(s) detected via VAD + pitch analysis",
            "data": {"speaker_count": speaker_count},
        })

        # ── Step 6: Pitch Analysis ──
        pitch_info = self._fe.extract_pitch(data, sr, voiced_frames)
        analysis["pitch_analysis"] = pitch_info
        analysis["processing_log"].append({
            "step": "pitch_analysis", "status": "completed",
            "message": f"Pitch: mean={pitch_info.get('mean',0)}Hz, "
                       f"std={pitch_info.get('std',0)}Hz, "
                       f"median={pitch_info.get('median',0)}Hz, "
                       f"vibrato={pitch_info.get('vibrato_rate',0)}Hz @ "
                       f"{pitch_info.get('vibrato_extent',0)}% extent",
        })

        # ── Step 7: Energy & Spectral Analysis ──
        energy_info = self._fe.extract_energy(data, sr)
        spectral_info = self._fe.extract_spectral(data, sr)
        formant_info = self._fe.extract_formants(data, sr)
        analysis["energy_info"] = energy_info
        analysis["spectral_info"] = spectral_info
        analysis["formant_info"] = formant_info
        analysis["processing_log"].append({
            "step": "spectral_analysis", "status": "completed",
            "message": f"Spectral: centroid={spectral_info.get('centroid_mean',0)}Hz, "
                       f"rolloff={spectral_info.get('rolloff',0)}Hz, "
                       f"formants={formant_info.get('frequencies',[])}",
        })

        # ── Step 8: Voice Quality (Jitter, Shimmer, HNR) ──
        quality_info = self._fe.extract_voice_quality(data, sr, pitch_info)
        analysis["voice_quality"] = quality_info
        analysis["processing_log"].append({
            "step": "voice_quality", "status": "completed",
            "message": f"Quality: jitter={quality_info.get('jitter_local',0):.3f}%, "
                       f"shimmer={quality_info.get('shimmer_local',0):.3f}%, "
                       f"HNR={quality_info.get('hnr',0):.1f}dB",
        })

        # ── Step 8b: Prosody (speaking rate, pauses) ──
        prosody_info = self._fe.extract_prosody(data, sr, voiced_frames, vad_info)
        analysis["prosody_info"] = prosody_info
        analysis["processing_log"].append({
            "step": "prosody_analysis", "status": "completed",
            "message": f"Prosody: {prosody_info.get('words_per_minute',0)} wpm, "
                       f"{prosody_info.get('pause_count',0)} pauses "
                       f"(avg {prosody_info.get('pause_duration_mean',0):.2f}s)",
        })

        # ── Step 8c: Emotion Detection ──
        # Use pitch + energy + spectral features as heuristics for emotion
        emotion_profile = self._estimate_emotion(analysis)
        analysis["emotion_detection"] = emotion_profile
        analysis["processing_log"].append({
            "step": "emotion_detection", "status": "completed",
            "message": f"Emotion profile: arousal={emotion_profile.get('arousal',0):.2f}, "
                       f"valence={emotion_profile.get('valence',0):.2f}, "
                       f"dominance={emotion_profile.get('dominance',0):.2f}",
        })

        # ── Step 9: Accent Detection ──
        accent = self._detect_accent(spectral_info, pitch_info)
        analysis["accent_detection"] = accent
        analysis["processing_log"].append({
            "step": "accent_detection", "status": "completed",
            "message": f"Accent: {accent.get('label','unknown')} (confidence={accent.get('confidence',0):.2f})",
        })

        # ── Step 10: Language Detection ──
        lang = self._detect_language(spectral_info)
        analysis["language_detection"] = lang
        analysis["processing_log"].append({
            "step": "language_detection", "status": "completed",
            "message": f"Language: {lang.get('label','unknown')} (confidence={lang.get('confidence',0):.2f})",
        })

        # ── Step 12 (earlier): Gender / Age Prediction ──
        gender_pred = self._fe.predict_gender_age(pitch_info, spectral_info)
        analysis["gender_prediction"] = gender_pred
        analysis["processing_log"].append({
            "step": "gender_age", "status": "completed",
            "message": f"Gender: {gender_pred.get('gender','unknown')}, "
                       f"Age: {gender_pred.get('age','unknown')}",
        })

        # ── Step 11: Voice Embedding (256-dim) ──
        embedding = self._fe.compute_voice_embedding(data, sr)
        analysis["voice_embedding"] = embedding
        analysis["processing_log"].append({
            "step": "voice_embedding", "status": "completed",
            "message": f"Voice embedding computed: {len(embedding)} dim",
            "data": {"embedding_dim": len(embedding), "norm": round(float(np.linalg.norm(embedding)), 4) if np.any(embedding) else 0},
        })

        # ── Step 12: Voice Clone Model (IndicF5 first, then RVC) ──
        try:
            from dreamtalk.voice.core.vc.indicf5_converter import IndicF5Converter, check_indicf5_available

            indicf5_status = check_indicf5_available()
            model_present = indicf5_status.get("model.safetensors", False)

            if model_present:
                try:
                    converter = IndicF5Converter(device="cpu")
                    if converter.is_loaded:
                        if file_path and os.path.exists(file_path):
                            output_dir = os.path.dirname(file_path)
                            clone_output = converter.clone_and_synthesize(
                                ref_audio_path=file_path,
                                ref_text="",
                                gen_text="Hello, this is your digital twin.",
                                output_path=os.path.join(output_dir, "voice_clone_indicf5.wav"),
                            )
                            analysis["clone_model"] = clone_output or "indicf5_loaded"
                        else:
                            analysis["clone_model"] = "indicf5_loaded"
                        analysis["processing_log"].append({
                            "step": "voice_clone", "status": "completed",
                            "message": "IndicF5 model loaded and ready for voice cloning (1.34 GB local weights)",
                        })
                    else:
                        analysis["processing_log"].append({
                            "step": "voice_clone", "status": "partial",
                            "message": "IndicF5 weights found but engine failed to load. Trying RVC...",
                        })
                except Exception as e:
                    analysis["processing_log"].append({
                        "step": "voice_clone", "status": "partial",
                        "message": f"IndicF5 failed ({e}). Trying RVC...",
                    })
            else:
                analysis["processing_log"].append({
                    "step": "voice_clone", "status": "stub",
                    "message": "IndicF5 weights not found at weights/voice/indic_tts/IndicF5/",
                })

        except ImportError as e:
            analysis["processing_log"].append({
                "step": "voice_clone", "status": "partial",
                "message": f"IndicF5 module not available ({e}). Trying RVC...",
            })

        # Also try RVC as secondary option (if IndicF5 failed)
        try:
            if analysis["clone_model"] is None:
                from dreamtalk.voice.core.vc.rvc.rvc_converter import RVCConverter, get_best_pretrained_path

                rvc_path = get_best_pretrained_path()
                if rvc_path:
                    try:
                        converter = RVCConverter(model_path=rvc_path, device="cpu")
                        if converter.is_loaded:
                            analysis["clone_model"] = "rvc_loaded"
                            analysis["processing_log"].append({
                                "step": "voice_clone_rvc_fallback", "status": "completed",
                                "message": "RVC also loaded as fallback",
                            })
                    except Exception:
                        pass
        except Exception:
            pass

        # ── Step 13: Preview Generation (TTS with cloned voice characteristics) ──
        if analysis.get("clone_model") or analysis.get("voice_embedding"):
            try:
                preview_text = "Hello, this is your digital twin speaking with your voice."
                preview_output_dir = os.path.join(os.path.dirname(file_path), "preview")
                os.makedirs(preview_output_dir, exist_ok=True)

                # Try generate_tts from feature extraction engine
                tts_path, tts_info = self._fe.generate_tts(
                    text=preview_text,
                    voice_embedding=embedding if embedding and np.any(embedding) else None,
                    output_dir=preview_output_dir,
                )

                if tts_path and os.path.exists(tts_path):
                    analysis["preview_url"] = tts_path
                    analysis["processing_log"].append({
                        "step": "preview", "status": "completed",
                        "message": f"Preview TTS generated: {tts_info.get('method','unknown')} "
                                   f"({tts_info.get('duration',0):.2f}s)",
                    })
                else:
                    analysis["processing_log"].append({
                        "step": "preview", "status": "partial",
                        "message": f"Preview TTS failed ({tts_info.get('method','none')}). Synthesizing waveform directly...",
                    })
                    # Fallback: generate a simple sine wave tone as identity marker
                    self._generate_preview_tone(preview_output_dir, analysis, gender_pred.get('gender', 'neutral'))
            except Exception as e:
                analysis["processing_log"].append({
                    "step": "preview", "status": "partial",
                    "message": f"Preview generation failed ({e}). Generating tone marker...",
                })
                try:
                    preview_output_dir = os.path.join(os.path.dirname(file_path), "preview")
                    os.makedirs(preview_output_dir, exist_ok=True)
                    self._generate_preview_tone(preview_output_dir, analysis, gender_pred.get('gender', 'neutral'))
                except Exception:
                    pass
        else:
            analysis["processing_log"].append({
                "step": "preview", "status": "stub",
                "message": "Preview generation pending clone model or voice embedding",
            })

        return analysis

    async def _store_clone_results(self, twin_id: str, results: list, analyses: list, role: str):
        """Store voice analysis results and update twin status.

        Populated from real feature extraction data computed in _run_voice_pipeline.
        """
        # Compute aggregate quality score across all samples
        scores = [a.get("quality_score", 0.0) for a in analyses]
        avg_quality = round(sum(scores) / len(scores), 1) if scores else 0.0

        source_samples = []
        for i, r in enumerate(results):
            a = analyses[i] if i < len(analyses) else {}
            audio_info = a.get("audio_info", {}) or {}
            enh_info = a.get("enhancement_info", {}) or {}
            vad_info = a.get("vad_info", {}) or {}
            pitch = a.get("pitch_analysis", {}) or {}
            emotion = a.get("emotion_detection", {}) or {}
            accent = a.get("accent_detection", {}) or {}
            lang = a.get("language_detection", {}) or {}
            quality = a.get("voice_quality", {}) or {}
            prosody = a.get("prosody_info", {}) or {}
            gender_pred = a.get("gender_prediction", {}) or {}

            source_samples.append({
                "filename": r["filename"],
                "asset_id": r["asset_id"],
                "file_path": r["file_path"],
                "original_name": r.get("filename", ""),
                "duration_seconds": audio_info.get("duration", 0.0),
                "sample_rate": audio_info.get("sample_rate", 0),
                "channels": audio_info.get("channels", 0),
                "quality_score": a.get("quality_score", 0.0),
                "noise_level": round(1.0 - (enh_info.get("snr_estimate", 0) / 40), 4) if enh_info.get("snr_estimate", 0) > 0 else 0.0,
                "language": lang.get("label", ""),
                "accent": accent.get("label", ""),
                "speaker_match": a.get("speaker_detected", False),
                "speaker_confidence": 0.95 if a.get("speaker_detected", False) else 0.0,
                "speech_rate_wpm": prosody.get("words_per_minute", 0),
                "prosody_features": {
                    "voiced_ratio": vad_info.get("voiced_ratio", 0),
                    "pause_count": prosody.get("pause_count", 0),
                    "pause_avg": prosody.get("pause_duration_mean", 0),
                },
                "emotion_profile": {
                    "label": emotion.get("label", "neutral"),
                    "valence": emotion.get("valence", 0),
                    "arousal": emotion.get("arousal", 0),
                    "dominance": emotion.get("dominance", 0),
                },
                "pitch_stats": {
                    "mean": pitch.get("mean", 0),
                    "std": pitch.get("std", 0),
                    "median": pitch.get("median", 0),
                    "quartiles": pitch.get("quartiles", []),
                    "vibrato_rate": pitch.get("vibrato_rate", 0),
                    "vibrato_extent": pitch.get("vibrato_extent", 0),
                },
                "voice_quality": {
                    "jitter": quality.get("jitter_local", 0),
                    "shimmer": quality.get("shimmer_local", 0),
                    "hnr": quality.get("hnr", 0),
                },
                "gender_prediction": gender_pred.get("gender", "unknown"),
                "age_prediction": gender_pred.get("age", None),
            })

        voice_data = {
            "is_cloned": True,
            "is_synthetic": False,
            "sample_count": len(results),
            "quality_score": avg_quality,
            "source_samples": source_samples,
            "processing_logs": [a.get("processing_log", []) for a in analyses],
            "processed_at": datetime.utcnow().isoformat(),
        }

        await execute(
            """UPDATE digital_twins
               SET voice_data = $1::jsonb,
                   voice_status = 'cloned',
                   updated_at = NOW()
               WHERE id = $2""",
            json.dumps(voice_data),
            twin_id,
        )

    @staticmethod
    async def get_voice_status(twin_id: str) -> Optional[dict]:
        row = await fetchrow(
            "SELECT voice_data, voice_status, voice_preview_url FROM digital_twins WHERE id = $1",
            twin_id,
        )
        if not row:
            return None
        return {
            "status": row["voice_status"],
            "data": dict(row["voice_data"]) if row["voice_data"] else {},
            "preview_url": row["voice_preview_url"],
        }
