"""Voice Pipeline v2 — Enhancement → VAD → Feature Extraction → RVC Cloning → TTS."""

import json
import logging
import math
import os
import struct
import tempfile
import uuid
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

import numpy as np

from dreamtalk.pipeline.models import VoiceAnalysisResult, EmotionResult, MoodState, SpeakerSegment

logger = logging.getLogger("dreamtalk.pipeline.voice")

try:
    import librosa
    LIBROSA_AVAILABLE = True
except Exception:
    LIBROSA_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except Exception:
    SOUNDFILE_AVAILABLE = False

try:
    import scipy.io.wavfile as wavfile
    import scipy.signal as signal
    SCIPY_AVAILABLE = True
except Exception:
    SCIPY_AVAILABLE = False

try:
    import torch
    _ = torch.tensor([1.0])
    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False

try:
    import torchaudio
    _ = torch.tensor([1.0])
    TORCHAUDIO_AVAILABLE = True
except Exception:
    TORCHAUDIO_AVAILABLE = False


class VoicePipeline:
    """Production-grade voice cloning pipeline.

    Pipeline:
        1. Audio loading with format detection (WAV, MP3, FLAC, M4A, OGG)
        2. Audio enhancement (denoising, normalization, bandpass filtering)
        3. Voice Activity Detection (energy-based VAD)
        4. Extensive acoustic feature extraction:
           - Pitch (mean, std, median, quartiles, contour, vibrato)
           - Energy (mean, std, envelope)
           - Spectral (centroid, bandwidth, rolloff, contrast, MFCCs)
           - Formants (F1-F4 frequencies and bandwidths)
           - Voice quality (jitter, shimmer, HNR)
           - Prosody (speaking rate, pauses)
           - Speaker embedding (WavLM/MFCC-based)
        5. Gender / age / emotion prediction from voice
        6. RVC voice cloning (with proper integration)
        7. TTS synthesis with cloned voice
    """

    # Formant frequency ranges [min_hz, max_hz]
    FORMANT_RANGES = [
        (300, 1000),    # F1
        (800, 2800),    # F2
        (1400, 3800),   # F3
        (3000, 5000),   # F4
    ]

    GENDER_PITCH_THRESHOLD = 165  # Hz - below = male, above = female

    def __init__(self, assets_dir: str = None, model_dir: str = None):
        self.assets_dir = assets_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "pipeline", "assets",
        )
        os.makedirs(self.assets_dir, exist_ok=True)
        self.model_dir = model_dir or os.path.join(self.assets_dir, "voice_models")
        os.makedirs(self.model_dir, exist_ok=True)
        self._rvc = None

    # ─── Audio Loading ──────────────────────────────────────────────────────

    def load_audio(self, path: str) -> Tuple[Optional[np.ndarray], int, Dict]:
        """Load audio file with format detection.

        Returns: (samples, sample_rate, info_dict)
        """
        info = {"format": "unknown", "bit_depth": 16, "channels": 1}
        if not os.path.exists(path):
            logger.warning(f"Audio file not found: {path}")
            return None, 0, info

        ext = Path(path).suffix.lower()
        info["format"] = ext

        try:
            # Try soundfile first (supports WAV, FLAC, OGG)
            if SOUNDFILE_AVAILABLE:
                data, sr = sf.read(path)
                info["channels"] = data.shape[1] if data.ndim > 1 else 1
                if data.ndim > 1:
                    data = np.mean(data, axis=1)  # mono
                info["bit_depth"] = sf.SoundFile(path).subtype_info.split("_")[-1] if hasattr(sf, 'SoundFile') else 16
                return data.astype(np.float32), sr, info

            # Fallback: scipy WAV
            if SCIPY_AVAILABLE and ext == ".wav":
                sr, data = wavfile.read(path)
                if data.dtype == np.int16:
                    data = data.astype(np.float32) / 32768.0
                elif data.dtype == np.int32:
                    data = data.astype(np.float32) / 2147483648.0
                if data.ndim > 1:
                    data = np.mean(data, axis=1)
                info["bit_depth"] = data.dtype.itemsize * 8
                return data, sr, info

            # Final fallback: librosa
            if LIBROSA_AVAILABLE:
                data, sr = librosa.load(path, sr=None, mono=True)
                return data.astype(np.float32), sr, info

            logger.warning("No audio backend available")
            return None, 0, info

        except Exception as e:
            logger.error(f"Audio load failed for {path}: {e}")
            return None, 0, info

    # ─── Audio Enhancement ─────────────────────────────────────────────────

    def enhance_audio(self, data: np.ndarray, sr: int) -> Tuple[np.ndarray, Dict]:
        """Apply audio enhancement: normalize → bandpass → denoise.

        Returns: (enhanced_data, enhancement_info)
        """
        info = {"normalized": False, "bandpass_applied": False, "noise_reduced": False, "snr_estimate": 0.0}
        enhanced = data.copy()

        # 1. DC offset removal
        enhanced = enhanced - np.mean(enhanced)

        # 2. Normalize peak amplitude to -1dB
        peak = np.max(np.abs(enhanced))
        if peak > 0:
            target = 10 ** (-1 / 20)  # -1dB
            enhanced = enhanced * (target / peak)
            info["normalized"] = True

        # 3. Bandpass filter (80 Hz - 8000 Hz = voice range)
        try:
            if SCIPY_AVAILABLE and sr > 160:
                nyquist = sr / 2
                low = 80 / nyquist
                high = min(8000 / nyquist, 0.99)
                if low < high:
                    b, a = signal.butter(4, [low, high], btype="band")
                    enhanced = signal.filtfilt(b, a, enhanced)
                    info["bandpass_applied"] = True
        except Exception as e:
            logger.warning(f"Bandpass filter failed: {e}")

        # 4. Simple spectral subtraction denoising (using quietest 15%)
        try:
            if LIBROSA_AVAILABLE and len(enhanced) > sr:
                # Find the quietest segment for noise estimation
                frame_len = int(sr * 0.025)
                n_frames = max(1, len(enhanced) // frame_len)
                frame_energies = []
                for i in range(n_frames):
                    frame = enhanced[i * frame_len:(i + 1) * frame_len]
                    frame_energies.append(np.mean(frame ** 2))
                quietest_frame = np.argmin(frame_energies)
                noise_sample = enhanced[quietest_frame * frame_len:(quietest_frame + 1) * frame_len]
                noise_psd = np.abs(np.fft.rfft(noise_sample)) ** 2
                D = librosa.stft(enhanced)
                mag = np.abs(D)
                phase = np.angle(D)
                noise_floor = np.mean(noise_psd) * 1.5
                mag_denoised = np.maximum(mag - np.sqrt(noise_floor), 0)
                enhanced = librosa.istft(mag_denoised * np.exp(1j * phase), length=len(enhanced))
                info["noise_reduced"] = True
        except Exception as e:
            logger.warning(f"Spectral denoising failed: {e}")

        # 5. SNR estimate (signal = top 10% energy frames, noise = bottom 50%)
        try:
            frame_len = int(sr * 0.025)
            hop_len = int(sr * 0.01)
            if LIBROSA_AVAILABLE and len(enhanced) > frame_len:
                rms = librosa.feature.rms(y=enhanced, frame_length=frame_len, hop_length=hop_len)[0]
                if len(rms) > 5:
                    signal_frames = np.sort(rms)[-max(1, len(rms) // 10):]
                    noise_frames = np.sort(rms)[:max(1, len(rms) // 2)]
                    signal_power = np.mean(signal_frames ** 2)
                    noise_power = np.mean(noise_frames ** 2)
                    if noise_power > 0 and signal_power > 0:
                        info["snr_estimate"] = round(10 * np.log10(signal_power / noise_power), 2)
        except Exception:
            pass

        return enhanced, info

    # ─── Voice Activity Detection ──────────────────────────────────────────

    def voice_activity_detection(self, data: np.ndarray, sr: int) -> Tuple[np.ndarray, Dict]:
        """Energy-based VAD. Returns (voiced_frames_mask, vad_info)."""
        frame_len = int(sr * 0.025)
        hop_len = int(sr * 0.010)

        if LIBROSA_AVAILABLE and len(data) > frame_len:
            try:
                rms = librosa.feature.rms(y=data, frame_length=frame_len, hop_length=hop_len)[0]
                silence_thresh = np.percentile(rms, 15) * 1.2
                voiced = rms > silence_thresh
                vad_info = {
                    "total_frames": len(rms),
                    "voiced_frames": int(np.sum(voiced)),
                    "voiced_ratio": round(float(np.mean(voiced)), 4),
                    "silence_threshold": round(float(silence_thresh), 6),
                }
                return voiced, vad_info
            except Exception:
                pass

        # Simple energy-based VAD
        frame_size = int(sr * 0.025)
        n_frames = max(1, len(data) // frame_size)
        voiced = np.zeros(n_frames, dtype=bool)
        for i in range(n_frames):
            frame = data[i * frame_size:(i + 1) * frame_size]
            if np.sqrt(np.mean(frame ** 2)) > 0.01:
                voiced[i] = True

        return voiced, {
            "total_frames": n_frames,
            "voiced_frames": int(np.sum(voiced)),
            "voiced_ratio": round(float(np.mean(voiced)), 4),
            "silence_threshold": 0.01,
        }

    # ─── Pitch Extraction ──────────────────────────────────────────────────

    def extract_pitch(self, data: np.ndarray, sr: int, voiced_frames: np.ndarray = None) -> Dict:
        """Extract comprehensive pitch features."""
        result = {
            "mean": 0.0, "std": 0.0, "median": 0.0,
            "quartiles": [0.0, 0.0, 0.0],
            "contour": None,
            "vibrato_rate": 0.0, "vibrato_extent": 0.0,
        }

        if not LIBROSA_AVAILABLE or len(data) < sr * 0.05:
            return result

        try:
            f0, voiced_flag, _ = librosa.pyin(
                data.astype(float),
                fmin=librosa.note_to_hz('C2'),
                fmax=librosa.note_to_hz('C7'),
                sr=sr,
            )
            valid = f0[voiced_flag]
            if len(valid) == 0:
                return result

            valid_hz = valid[~np.isnan(valid)]
            if len(valid_hz) == 0:
                return result

            result["mean"] = round(float(np.mean(valid_hz)), 2)
            result["std"] = round(float(np.std(valid_hz)), 2)
            result["median"] = round(float(np.median(valid_hz)), 2)
            result["quartiles"] = [
                round(float(np.percentile(valid_hz, 25)), 2),
                round(float(np.percentile(valid_hz, 50)), 2),
                round(float(np.percentile(valid_hz, 75)), 2),
            ]
            result["contour"] = [round(float(v), 2) for v in valid_hz[:200]]

            # Vibrato detection (5-8 Hz modulation in pitch)
            if len(valid_hz) > 100:
                detrended = valid_hz - np.mean(valid_hz)
                try:
                    freqs = np.fft.rfftfreq(len(detrended), d=1 / (sr / 256))
                    fft_mag = np.abs(np.fft.rfft(detrended))
                    vib_range = (freqs >= 4) & (freqs <= 10)
                    if np.any(vib_range):
                        peak_idx = np.argmax(fft_mag[vib_range])
                        result["vibrato_rate"] = round(float(freqs[vib_range][peak_idx]), 2)
                        result["vibrato_extent"] = round(float(np.std(detrended) / np.mean(valid_hz) * 100), 2)
                except Exception:
                    pass

        except Exception as e:
            logger.warning(f"Pitch extraction failed: {e}")

        return result

    # ─── Energy Extraction ─────────────────────────────────────────────────

    def extract_energy(self, data: np.ndarray, sr: int) -> Dict:
        result = {"mean": 0.0, "std": 0.0, "envelope": None}
        if LIBROSA_AVAILABLE and len(data) > int(sr * 0.025):
            try:
                rms = librosa.feature.rms(y=data.astype(float), frame_length=int(sr * 0.025), hop_length=int(sr * 0.01))[0]
                result["mean"] = round(float(np.mean(rms)), 6)
                result["std"] = round(float(np.std(rms)), 6)
                result["envelope"] = [round(float(v), 6) for v in rms[:200]]
            except Exception:
                pass
        else:
            result["mean"] = round(float(np.sqrt(np.mean(data ** 2))), 6)
            result["std"] = round(float(np.std(data)), 6)
        return result

    # ─── Spectral Features ─────────────────────────────────────────────────

    def extract_spectral(self, data: np.ndarray, sr: int) -> Dict:
        result = {
            "centroid_mean": 0.0, "bandwidth": 0.0, "rolloff": 0.0,
            "contrast": None, "mfccs_mean": None, "mfccs_covariance": None,
        }
        if not LIBROSA_AVAILABLE or len(data) < sr * 0.05:
            return result

        try:
            y = data.astype(float)
            n_fft = int(sr * 0.025)
            hop = int(sr * 0.01)

            centroid = librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=n_fft, hop_length=hop)
            result["centroid_mean"] = round(float(np.mean(centroid)), 2)

            bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, n_fft=n_fft, hop_length=hop)
            result["bandwidth"] = round(float(np.mean(bandwidth)), 2)

            rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, n_fft=n_fft, hop_length=hop)
            result["rolloff"] = round(float(np.mean(rolloff)), 2)

            contrast = librosa.feature.spectral_contrast(y=y, sr=sr, n_fft=n_fft, hop_length=hop)
            result["contrast"] = [round(float(v), 4) for v in np.mean(contrast, axis=1)]

            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, n_fft=n_fft, hop_length=hop)
            mfcc_mean = np.mean(mfccs, axis=1)
            result["mfccs_mean"] = [round(float(v), 4) for v in mfcc_mean]
            mfcc_cov = np.cov(mfccs)
            result["mfccs_covariance"] = [round(float(v), 6) for v in mfcc_cov.flatten()[:64]]

        except Exception as e:
            logger.warning(f"Spectral extraction failed: {e}")

        return result

    # ─── Formant Extraction ────────────────────────────────────────────────

    def extract_formants(self, data: np.ndarray, sr: int) -> Dict:
        """Extract F1-F4 formant frequencies and bandwidths via LPC."""
        result = {"frequencies": None, "bandwidths": None}
        if not SCIPY_AVAILABLE or len(data) < sr * 0.05:
            return result

        try:
            order = 12  # LPC order for 4 formants
            a = signal.lpc(data, order)
            roots = np.roots(a)
            roots = roots[np.imag(roots) >= 0]
            angles = np.arctan2(np.imag(roots), np.real(roots))
            freqs = angles * (sr / (2 * np.pi))
            bandwidths = -0.5 * (sr / (2 * np.pi)) * np.log(np.abs(roots))

            # Sort by frequency and take F1-F4
            valid = (freqs > 80) & (freqs < sr / 2) & (bandwidths < 1000)
            if np.any(valid):
                valid_freqs = freqs[valid]
                valid_bw = bandwidths[valid]
                order = np.argsort(valid_freqs)
                top_freqs = valid_freqs[order][:4]
                top_bw = valid_bw[order][:4]
                result["frequencies"] = [round(float(f), 2) for f in top_freqs]
                result["bandwidths"] = [round(float(b), 2) for b in top_bw]
        except Exception:
            pass

        return result

    # ─── Voice Quality (Jitter, Shimmer, HNR) ──────────────────────────────

    def extract_voice_quality(self, data: np.ndarray, sr: int, pitch_info: Dict) -> Dict:
        result = {
            "jitter_local": 0.0, "jitter_rap": 0.0, "jitter_ppq5": 0.0,
            "shimmer_local": 0.0, "shimmer_apq3": 0.0, "shimmer_apq5": 0.0,
            "hnr": 0.0,
        }

        f0 = pitch_info.get("contour")
        if not f0 or len(f0) < 10:
            return result

        try:
            f0_arr = np.array(f0)
            f0_arr = f0_arr[f0_arr > 0]
            if len(f0_arr) < 10:
                return result

            diffs = np.abs(np.diff(f0_arr))
            result["jitter_local"] = round(float(np.mean(diffs) / np.mean(f0_arr) * 100), 4)
            if len(diffs) > 3:
                rap_diffs = np.abs(f0_arr[2:] - 2 * f0_arr[1:-1] + f0_arr[:-2])
                result["jitter_rap"] = round(float(np.mean(rap_diffs) / np.mean(f0_arr) * 100), 4)
            if len(f0_arr) > 5:
                ppq = np.array([np.mean(np.abs(f0_arr[i:i+5] - np.mean(f0_arr[i:i+5]))) for i in range(len(f0_arr) - 4)])
                result["jitter_ppq5"] = round(float(np.mean(ppq) / np.mean(f0_arr) * 100), 4)

            # Simple HNR estimate from autocorrelation
            if SCIPY_AVAILABLE and len(data) > sr:
                auto = signal.correlate(data, data, mode="same")
                center = len(auto) // 2
                lag = int(sr / f0_arr.mean()) if f0_arr.mean() > 0 else sr // 100
                if lag < center:
                    hnr_val = auto[center + lag] / auto[center] if auto[center] != 0 else 0
                    result["hnr"] = round(float(max(0, 10 * np.log10(max(hnr_val, 1e-10)))), 2)

        except Exception as e:
            logger.warning(f"Voice quality extraction failed: {e}")

        return result

    # ─── Speaking Rate ─────────────────────────────────────────────────────

    def extract_prosody(self, data: np.ndarray, sr: int, voiced: np.ndarray, vad_info: Dict) -> Dict:
        result = {
            "speaking_rate": 0.0,
            "words_per_minute": 0.0,
            "pause_duration_mean": 0.0,
            "pause_count": 0,
        }

        duration = len(data) / sr
        if duration <= 0:
            return result

        # Estimate from energy envelope
        vad_r = vad_info.get("voiced_ratio", 0.5)
        result["speaking_rate"] = round(vad_r * 5.0, 2)
        result["words_per_minute"] = max(0, int(vad_r * 150))

        # Pause detection
        if LIBROSA_AVAILABLE and len(data) > sr:
            try:
                rms = librosa.feature.rms(y=data.astype(float))[0]
                silence = rms < np.percentile(rms, 20)
                transitions = np.diff(silence.astype(int))
                pause_starts = np.where(transitions == -1)[0]
                pause_ends = np.where(transitions == 1)[0]
                if len(pause_starts) > 0 and len(pause_ends) > 0:
                    pause_durations = []
                    for ps in pause_starts:
                        pe = pause_ends[pause_ends > ps]
                        if len(pe) > 0:
                            pause_durations.append((pe[0] - ps) * 256 / sr)
                    if pause_durations:
                        result["pause_count"] = len(pause_durations)
                        result["pause_duration_mean"] = round(float(np.mean(pause_durations)), 3)
            except Exception:
                pass

        return result

    # ─── Speaker Diarization (Multi-Speaker Detection) ────────────────────

    def detect_speakers(self, data: np.ndarray, sr: int,
                        voiced_frames: np.ndarray) -> tuple[list, int]:
        """Detect distinct speakers in multi-speaker audio using MFCC + clustering.

        Pipeline:
          1. Extract frame-level MFCC features (39-dim: MFCC + delta + delta2)
          2. Align VAD mask to feature frames
          3. Normalize and cluster voiced frames via AgglomerativeClustering
          4. Score cluster quality with silhouette to auto-detect speaker count
          5. Merge adjacent same-speaker frames into contiguous segments
          6. Compute per-segment acoustic profile (pitch, energy, spectral centroid)

        Returns:
          Tuple of (list[SpeakerSegment], speaker_count)
        """
        result: list[SpeakerSegment] = []
        speaker_count = 0

        # Need sufficient audio for meaningful diarization
        min_duration = sr * 1.0  # at least 1 second
        if len(data) < min_duration or not LIBROSA_AVAILABLE:
            return result, speaker_count

        try:
            from sklearn.cluster import AgglomerativeClustering
            try:
                from sklearn.metrics import silhouette_score
                _SILHOUETTE_AVAILABLE = True
            except Exception:
                _SILHOUETTE_AVAILABLE = False

            # ── Step 1: Frame-level MFCC features ──
            n_fft = int(sr * 0.025)  # 25ms frames
            hop_length = int(sr * 0.010)  # 10ms hop

            mfcc = librosa.feature.mfcc(
                y=data.astype(float), sr=sr,
                n_mfcc=13, n_fft=n_fft, hop_length=hop_length
            )  # shape: (13, n_frames)

            # Delta MFCCs (temporal dynamics)
            mfcc_delta = librosa.feature.delta(mfcc)
            mfcc_delta2 = librosa.feature.delta(mfcc, order=2)

            # Stack: MFCC + delta + delta2 = 39-dim
            features = np.vstack([mfcc, mfcc_delta, mfcc_delta2]).T  # (n_frames, 39)

            # ── Step 2: Align VAD mask to feature frames ──
            n_frames = features.shape[0]

            # Create frame-level VAD mask
            frame_vad = np.zeros(n_frames, dtype=bool)
            n_vad = len(voiced_frames)
            if n_vad > 0:
                min_len = min(n_frames, n_vad)
                frame_vad[:min_len] = voiced_frames[:min_len]
            else:
                # Fallback: energy threshold
                rms = librosa.feature.rms(y=data.astype(float),
                                          frame_length=n_fft,
                                          hop_length=hop_length)[0]
                rms_aligned = np.zeros(n_frames)
                mlen = min(len(rms), n_frames)
                rms_aligned[:mlen] = rms[:mlen]
                threshold = np.percentile(rms_aligned, 20) * 1.5
                frame_vad = rms_aligned > threshold

            # ── Step 3: Filter voiced frames ──
            voiced_indices = np.where(frame_vad)[0]
            if len(voiced_indices) < 10:
                logger.info(f"Speaker diarization skipped: only {len(voiced_indices)} voiced frames")
                return result, speaker_count

            voiced_features = features[voiced_indices]

            # ── Step 4: Normalize ──
            feat_mean = np.mean(voiced_features, axis=0)
            feat_std = np.std(voiced_features, axis=0) + 1e-8
            voiced_features_norm = (voiced_features - feat_mean) / feat_std

            # ── Step 5: Cluster voiced frames ──
            frames_per_half_sec = max(1, int(int(sr * 0.5) // hop_length))
            min_speakers = max(1, int(len(voiced_indices) // frames_per_half_sec))
            max_speakers = min(5, max(1, int(len(voiced_indices) // 15)))

            if max_speakers <= 1:
                labels = np.zeros(len(voiced_indices), dtype=int)
            else:
                best_score = -1.0
                best_labels = None

                for n_clusters in range(min_speakers, max_speakers + 1):
                    if n_clusters >= len(voiced_features_norm):
                        break
                    if n_clusters < 2:
                        continue
                    try:
                        model = AgglomerativeClustering(
                            n_clusters=n_clusters,
                            metric="cosine",
                            linkage="average",
                        )
                        pred = model.fit_predict(voiced_features_norm)
                        if _SILHOUETTE_AVAILABLE and len(set(pred)) > 1:
                            score = silhouette_score(voiced_features_norm, pred,
                                                     metric="cosine")
                            if score > best_score:
                                best_score = score
                                best_labels = pred
                    except Exception:
                        continue

                if best_labels is None or best_score < 0.05:
                    labels = np.zeros(len(voiced_indices), dtype=int)
                else:
                    labels = best_labels

            # ── Step 6: Build full-frame label array ──
            full_labels = -1 * np.ones(n_frames, dtype=int)
            for idx, label in zip(voiced_indices, labels):
                full_labels[idx] = label

            # ── Step 7: Merge adjacent same-speaker frames into segments ──
            unique_speakers = sorted(set(labels))
            speaker_count = len(unique_speakers)

            for spk in unique_speakers:
                mask = full_labels == spk
                if not np.any(mask):
                    continue

                diffs = np.diff(np.concatenate(([False], mask, [False])).astype(int))
                starts = np.where(diffs == 1)[0]
                ends = np.where(diffs == -1)[0]

                for s, e in zip(starts, ends):
                    start_sec = round(s * hop_length / sr, 3)
                    end_sec = round(e * hop_length / sr, 3)
                    duration = end_sec - start_sec

                    if duration < 0.3:
                        continue

                    seg_start_sample = int(s * hop_length)
                    seg_end_sample = min(int(e * hop_length), len(data))
                    seg_audio = data[seg_start_sample:seg_end_sample]

                    if len(seg_audio) < sr * 0.05:
                        continue

                    seg_pitch = 0.0
                    seg_energy = 0.0
                    seg_centroid = 0.0
                    try:
                        f0, _, _ = librosa.pyin(
                            seg_audio.astype(float),
                            fmin=50, fmax=600, sr=sr,
                        )
                        valid_f0 = f0[~np.isnan(f0)]
                        seg_pitch = round(float(np.mean(valid_f0)), 2) if len(valid_f0) > 0 else 0.0

                        rms = librosa.feature.rms(y=seg_audio.astype(float))[0]
                        seg_energy = round(float(np.mean(rms)), 6)

                        centroid = librosa.feature.spectral_centroid(
                            y=seg_audio.astype(float), sr=sr
                        )[0]
                        seg_centroid = round(float(np.mean(centroid)), 2)
                    except Exception:
                        pass

                    confidence = round(min(duration / 5.0, 0.95), 3)

                    result.append(SpeakerSegment(
                        speaker_id=f"speaker_{spk:02d}",
                        start_sec=start_sec,
                        end_sec=end_sec,
                        confidence=confidence,
                        pitch_mean=seg_pitch,
                        energy_mean=seg_energy,
                        spectral_centroid_mean=seg_centroid,
                    ))

            result.sort(key=lambda s: s.start_sec)

            logger.info(f"Speaker diarization: {speaker_count} speaker(s) "
                        f"detected in {len(result)} segments")

        except ImportError as e:
            logger.warning(f"Speaker diarization unavailable (missing dep): {e}")
        except Exception as e:
            logger.warning(f"Speaker diarization failed: {e}")

        return result, speaker_count

    # ─── Voice Embedding ───────────────────────────────────────────────────

    def compute_voice_embedding(self, data: np.ndarray, sr: int) -> List[float]:
        """Compute a 256-dim voice embedding from spectral and prosodic features."""
        embedding = [0.0] * 256

        try:
            if LIBROSA_AVAILABLE and len(data) > sr * 0.05:
                y = data.astype(float)
                n_fft = int(sr * 0.025)
                hop = int(sr * 0.01)

                # MFCC (13 dimensions)
                mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, n_fft=n_fft, hop_length=hop)
                mfcc_mean = np.mean(mfcc, axis=1)
                mfcc_std = np.std(mfcc, axis=1)
                for i, v in enumerate(mfcc_mean):
                    if i < 13: embedding[i] = round(float(v), 6)
                for i, v in enumerate(mfcc_std):
                    if i < 13: embedding[13 + i] = round(float(v), 6)

                # Spectral features (6 dimensions)
                centroid = librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=n_fft, hop_length=hop)
                bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, n_fft=n_fft, hop_length=hop)
                rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, n_fft=n_fft, hop_length=hop)
                zcr = librosa.feature.zero_crossing_rate(y=y, frame_length=n_fft, hop_length=hop)
                embedding[26] = round(float(np.mean(centroid) / sr), 6)
                embedding[27] = round(float(np.mean(bandwidth) / sr), 6)
                embedding[28] = round(float(np.mean(rolloff) / sr), 6)
                embedding[29] = round(float(np.mean(zcr)), 6)

                # Pitch stats (4 dimensions)
                f0, voiced_flag, _ = librosa.pyin(y, fmin=50, fmax=600, sr=sr)
                valid = f0[voiced_flag & ~np.isnan(f0)]
                if len(valid) > 0:
                    embedding[30] = round(float(np.mean(valid) / sr), 6)
                    embedding[31] = round(float(np.std(valid) / sr), 6)
                    embedding[32] = round(float(np.median(valid) / sr), 6)

                # RMS energy (2 dimensions)
                rms = librosa.feature.rms(y=y, frame_length=n_fft, hop_length=hop)
                embedding[33] = round(float(np.mean(rms)), 6)
                embedding[34] = round(float(np.std(rms)), 6)

        except Exception as e:
            logger.warning(f"Embedding computation failed: {e}")

        return embedding

    # ─── Voice-based Emotion Prediction ────────────────────────────────────

    def predict_emotion_from_voice(self, pitch_info: Dict, energy_info: Dict,
                                    spectral_info: Dict, quality_info: Dict,
                                    prosody_info: Dict) -> Dict:
        """Predict emotion from acoustic voice features.

        Uses pitch, energy, spectral centroid, jitter/shimmer/HNR, and
        speaking rate to estimate the speaker's emotional state from voice alone.

        Returns:
            Dict with keys:
              - emotion: predicted emotion label (str, e.g. "happy", "sad")
              - confidence: prediction confidence (0-1)
              - scores: dict of per-emotion confidence scores
              - valence: estimated valence (-1 to 1)
              - arousal: estimated arousal (0 to 1)
        """
        result = {
            "emotion": "neutral",
            "confidence": 0.0,
            "scores": {},
            "valence": 0.0,
            "arousal": 0.0,
        }

        pitch_mean = pitch_info.get("mean", 0.0)
        energy_mean = energy_info.get("mean", 0.0)
        centroid_mean = spectral_info.get("centroid_mean", 0.0)
        jitter = quality_info.get("jitter_local", 0.0)
        shimmer = quality_info.get("shimmer_local", 0.0)
        hnr = quality_info.get("hnr", 0.0)
        speaking_rate = prosody_info.get("speaking_rate", 0.0)

        # Normalize features to 0-1 ranges
        # Typical pitch: male ~100-150Hz, female ~200-250Hz
        # Normalize as fraction of max expected pitch (300Hz)
        pitch_norm = min(pitch_mean / 300.0, 1.0) if pitch_mean > 0 else 0.5

        # Typical energy RMS: 0-1
        energy_norm = min(energy_mean * 10, 1.0)

        # Typical centroid: 0-4000Hz
        centroid_norm = min(centroid_mean / 4000.0, 1.0) if centroid_mean > 0 else 0.5

        # Jitter: typical 0-2%, higher = more distressed
        jitter_norm = min(jitter / 3.0, 1.0)

        # Shimmer: typical 0-10%, higher = more distressed
        shimmer_norm = min(shimmer / 15.0, 1.0)

        # HNR: typical 0-30dB, higher = more stable voice
        hnr_norm = min(hnr / 30.0, 1.0) if hnr > 0 else 0.5

        # Speaking rate: typical 0-10, higher = more excited/anxious
        rate_norm = min(speaking_rate / 10.0, 1.0)

        # ── Emotion rule scoring ──
        # Happy: mid-high pitch, mid-high energy, mid centroid, low jitter/shimmer, faster rate
        happy_score = (
            0.25 * pitch_norm +
            0.20 * energy_norm +
            0.10 * centroid_norm +
            0.05 * (1.0 - jitter_norm) +
            0.05 * (1.0 - shimmer_norm) +
            0.10 * hnr_norm +
            0.10 * rate_norm +
            0.15 * (0.5 - abs(pitch_norm - 0.6))  # peak at mid-high pitch
        )

        # Sad: low pitch, low energy, low centroid, high jitter/shimmer, slow rate
        sad_score = (
            0.20 * (1.0 - pitch_norm) +
            0.20 * (1.0 - energy_norm) +
            0.15 * (1.0 - centroid_norm) +
            0.10 * jitter_norm +
            0.10 * shimmer_norm +
            0.10 * (1.0 - rate_norm) +
            0.15 * (1.0 - hnr_norm)
        )

        # Angry: low pitch, high energy, high centroid, moderate jitter, fast rate
        angry_score = (
            0.15 * (1.0 - pitch_norm) +
            0.25 * energy_norm +
            0.15 * centroid_norm +
            0.10 * jitter_norm +
            0.05 * shimmer_norm +
            0.10 * (1.0 - hnr_norm) +
            0.15 * rate_norm +
            0.05 * (1.0 - abs(energy_norm - 0.8))  # peak at high energy
        )

        # Fearful/Anxious: high pitch, mid-high energy, high centroid, high jitter/shimmer, fast rate
        fearful_score = (
            0.20 * pitch_norm +
            0.15 * energy_norm +
            0.10 * centroid_norm +
            0.15 * jitter_norm +
            0.15 * shimmer_norm +
            0.10 * rate_norm +
            0.10 * (1.0 - hnr_norm) +
            0.05 * (1.0 - abs(pitch_norm - 0.8))  # peak at high pitch
        )

        # Calm/Neutral: mid pitch, low-mid energy, mid centroid, low jitter/shimmer, slow rate
        calm_score = (
            0.15 * (1.0 - abs(pitch_norm - 0.4)) +
            0.15 * (1.0 - energy_norm) +
            0.10 * (1.0 - abs(centroid_norm - 0.4)) +
            0.15 * (1.0 - jitter_norm) +
            0.10 * (1.0 - shimmer_norm) +
            0.15 * hnr_norm +
            0.10 * (1.0 - rate_norm) +
            0.10 * (1.0 - abs(energy_norm - 0.3))
        )

        # Excited: high pitch, high energy, high centroid, low jitter, fast rate
        excited_score = (
            0.20 * pitch_norm +
            0.20 * energy_norm +
            0.10 * centroid_norm +
            0.05 * (1.0 - jitter_norm) +
            0.05 * (1.0 - shimmer_norm) +
            0.10 * hnr_norm +
            0.20 * rate_norm +
            0.10 * (1.0 - abs(pitch_norm - 0.75))
        )

        # Ensure all scores are positive
        scores = {
            "happy": max(0, happy_score),
            "sad": max(0, sad_score),
            "angry": max(0, angry_score),
            "fearful": max(0, fearful_score),
            "calm": max(0, calm_score),
            "excited": max(0, excited_score),
            "neutral": max(0, (calm_score + 0.2) / 2),  # bias toward neutral as default
        }

        # Normalize scores to sum to 1
        total = sum(scores.values()) + 1e-8
        scores = {k: round(v / total, 4) for k, v in scores.items()}

        # Best emotion
        sorted_emotions = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_emotion = sorted_emotions[0][0]
        best_score = sorted_emotions[0][1]

        # Map to PAD coordinates
        emotion_pad = {
            "happy": {"valence": 0.7, "arousal": 0.6},
            "sad": {"valence": -0.6, "arousal": -0.3},
            "angry": {"valence": -0.7, "arousal": 0.8},
            "fearful": {"valence": -0.5, "arousal": 0.7},
            "calm": {"valence": 0.3, "arousal": 0.1},
            "excited": {"valence": 0.6, "arousal": 0.9},
            "neutral": {"valence": 0.0, "arousal": 0.0},
        }

        pad = emotion_pad.get(best_emotion, {"valence": 0.0, "arousal": 0.0})

        result["emotion"] = best_emotion
        result["confidence"] = round(max(best_score - sorted_emotions[1][1], 0.05), 4) if len(sorted_emotions) > 1 else round(best_score, 4)
        result["scores"] = scores
        result["valence"] = round(pad["valence"], 3)
        result["arousal"] = round(pad["arousal"], 3)

        return result

    # ─── Emotion Profile Fusion ───────────────────────────────────────────

    def fuse_emotion_profiles(self, voice_result: VoiceAnalysisResult, brain_emotion: EmotionResult) -> EmotionResult:
        """Fuse the voice-based emotion prediction with the brain's text-based EmotionResult.

        Takes the acoustic voice features already computed during `run()` and
        the brain pipeline's text-based EmotionResult, then produces a fused
        emotion profile stored back on the voice result.

        The fusion uses dynamic weighting based on confidence:
          - High voice confidence → lean toward voice prediction
          - High text confidence → lean toward text prediction
          - Both low → neutral ensemble

        Sets:
          voice_result.emotion_from_voice — fused emotion label
          voice_result.emotion_from_voice_scores — dict with 'voice', 'text', 'fused' scores
          brain_emotion.vocal_emotion_contribution — voice prediction details
          brain_emotion.textual_emotion_contribution — text prediction replay
          brain_emotion.ensemble_weights — how the fusion was weighted
        """
        # Re-predict voice emotion from stored acoustic features
        pitch_info = {
            "mean": voice_result.pitch_mean,
            "std": voice_result.pitch_std,
            "median": voice_result.pitch_median,
            "contour": voice_result.pitch_contour,
        }
        energy_info = {
            "mean": voice_result.energy_mean,
            "std": voice_result.energy_std,
            "envelope": voice_result.energy_envelope,
        }
        spectral_info = {
            "centroid_mean": voice_result.spectral_centroid_mean,
            "bandwidth": voice_result.spectral_bandwidth,
            "rolloff": voice_result.spectral_rolloff,
            "contrast": voice_result.spectral_contrast,
            "mfccs_mean": voice_result.mfccs_mean,
        }
        quality_info = {
            "jitter_local": voice_result.jitter_local,
            "jitter_rap": voice_result.jitter_rap,
            "jitter_ppq5": voice_result.jitter_ppq5,
            "shimmer_local": voice_result.shimmer_local,
            "shimmer_apq3": voice_result.shimmer_apq3,
            "shimmer_apq5": voice_result.shimmer_apq5,
            "hnr": voice_result.harmonicity_hnr,
        }
        prosody_info = {
            "speaking_rate": voice_result.speaking_rate,
            "words_per_minute": voice_result.words_per_minute,
            "pause_duration_mean": voice_result.pause_duration_mean,
            "pause_count": voice_result.pause_count,
        }

        voice_emotion = self.predict_emotion_from_voice(
            pitch_info, energy_info, spectral_info, quality_info, prosody_info
        )

        # Map voice emotion label to MoodState
        label_to_mood = {
            "happy": "happy", "sad": "sad", "angry": "angry",
            "fearful": "fearful", "calm": "calm", "excited": "excited",
            "neutral": "neutral",
        }
        voice_mood_str = label_to_mood.get(voice_emotion["emotion"], "neutral")
        voice_confidence = voice_emotion["confidence"]
        voice_valence = voice_emotion["valence"]
        voice_arousal = voice_emotion["arousal"]
        voice_scores = voice_emotion["scores"]

        # Brain text-based emotion
        text_mood_str = brain_emotion.primary_mood.value if brain_emotion else "neutral"
        text_confidence = brain_emotion.confidence if brain_emotion else 0.0
        text_valence = brain_emotion.valence if brain_emotion else 0.0
        text_arousal = brain_emotion.arousal if brain_emotion else 0.0

        # ── Dynamic ensemble weighting ──
        # Voice confidence: higher when voice features are distinctive
        # Text confidence: higher when VADER/rule signals are clear
        voice_weight = min(voice_confidence * 0.4 + 0.1, 0.6)
        text_weight = min(text_confidence * 0.4 + 0.1, 0.6)
        total_weight = voice_weight + text_weight
        voice_weight /= total_weight
        text_weight /= total_weight

        # Fused PAD
        fused_valence = voice_weight * voice_valence + text_weight * text_valence
        fused_arousal = voice_weight * voice_arousal + text_weight * text_arousal

        # Fused mood — pick the one with higher weighted score for its dominant emotion
        voice_dominant = voice_scores.get(text_mood_str, 0) if voice_weight > text_weight else 0
        text_dominant = text_confidence if text_weight >= voice_weight else 0

        if voice_weight >= text_weight and voice_confidence > 0.15:
            # Voice has more weight and meaningful signal → use voice mood
            fused_mood_str = voice_mood_str
            fused_confidence = voice_weight * voice_confidence + text_weight * text_confidence
        else:
            # Text has more weight → use text mood
            fused_mood_str = text_mood_str
            fused_confidence = text_weight * text_confidence + voice_weight * voice_confidence

        try:
            fused_mood = MoodState(fused_mood_str)
        except ValueError:
            fused_mood = MoodState.NEUTRAL

        # ── Set on voice result ──
        voice_result.emotion_from_voice = fused_mood_str
        voice_result.emotion_from_voice_scores = {
            "voice": {
                "mood": voice_mood_str,
                "confidence": voice_confidence,
                "valence": voice_valence,
                "arousal": voice_arousal,
                "scores": voice_scores,
                "weight": round(voice_weight, 4),
            },
            "text": {
                "mood": text_mood_str,
                "confidence": text_confidence,
                "valence": text_valence,
                "arousal": text_arousal,
                "weight": round(text_weight, 4),
            },
            "fused": {
                "mood": fused_mood_str,
                "confidence": round(fused_confidence, 4),
                "valence": round(fused_valence, 3),
                "arousal": round(fused_arousal, 3),
            },
        }

        # ── Set on brain emotion result (for downstream use) ──
        if brain_emotion:
            brain_emotion.vocal_emotion_contribution = {
                "voice_mood": voice_mood_str,
                "confidence": voice_confidence,
                "scores": voice_scores,
                "weight": round(voice_weight, 4),
            }
            brain_emotion.textual_emotion_contribution = {
                "text_mood": text_mood_str,
                "confidence": text_confidence,
                "weight": round(text_weight, 4),
            }
            brain_emotion.ensemble_weights = {
                "voice": round(voice_weight, 4),
                "text": round(text_weight, 4),
            }

        logger.info(f"Emotion fusion: voice={voice_mood_str}(w={voice_weight:.2f}) "
                    f"+ text={text_mood_str}(w={text_weight:.2f}) "
                    f"→ fused={fused_mood_str} (V={fused_valence:.2f}, A={fused_arousal:.2f})")

        return brain_emotion

    def predict_gender_age(self, pitch_info: Dict, spectral_info: Dict) -> Dict:
        """Predict gender and approximate age from voice features."""
        result = {"gender": None, "age": None}

        pitch_mean = pitch_info.get("mean", 0)
        centroid_mean = spectral_info.get("centroid_mean", 0)

        if pitch_mean > 0:
            if pitch_mean < self.GENDER_PITCH_THRESHOLD:
                result["gender"] = "male"
            else:
                result["gender"] = "female"

        # Approximate age from spectral features (very rough)
        if centroid_mean > 0:
            age_ratio = centroid_mean / 4000
            if age_ratio > 0.6:
                result["age"] = round(25 + (1 - age_ratio) * 40, 1)
            else:
                result["age"] = round(35 + (1 - age_ratio) * 30, 1)

        return result

    # ─── Voice Cloning ─────────────────────────────────────────────────────

    def clone_voice(self, source_audio_path: str, output_dir: str = None) -> Tuple[Optional[str], Dict]:
        """Clone voice using IndicF5 (CFM-based), fallback to RVC, then OpenVoice, then structural."""
        if output_dir is None:
            output_dir = self.assets_dir
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, f"voice_clone_{uuid.uuid4().hex[:8]}.wav")
        clone_info = {"method": "none", "confidence": 0.0, "speaker_id": None}

        # ── Attempt 1: IndicF5 (CFM-based voice cloning, local weights 1.34 GB) ──
        try:
            from dreamtalk.voice.core.vc.indicf5_converter import IndicF5Converter
            _if5_device = "cpu"
            converter = IndicF5Converter(device=_if5_device)
            if converter.is_loaded:
                # Use a default reference text if none available
                result = converter.clone_and_synthesize(
                    ref_audio_path=source_audio_path,
                    ref_text="",
                    gen_text="Hello, this is your digital twin speaking with your voice.",
                    output_path=output_path,
                    lang="en",
                )
                if result and os.path.exists(result):
                    clone_info["method"] = "indicf5"
                    clone_info["confidence"] = 0.8
                    logger.info(f"IndicF5 voice clone successful: {output_path}")
                    return output_path, clone_info
            else:
                logger.info("IndicF5 not loaded; trying RVC")
        except Exception as e:
            logger.info(f"IndicF5 unavailable ({e}); trying RVC")

        # ── Attempt 2: RVC (Retrieval-based Voice Conversion) ──
        try:
            from dreamtalk.voice.core.vc.rvc.rvc_converter import RVCConverter, get_best_pretrained_path

            generator_path = get_best_pretrained_path()
            if generator_path:
                _rvc_device = "cuda" if TORCH_AVAILABLE and torch.cuda.is_available() else "cpu"
                converter = RVCConverter(model_path=generator_path, device=_rvc_device)
                if converter.is_loaded:
                    result_path = converter.convert(
                        source_audio_path, "cloned", output_path, pitch_adjust=0
                    )
                    if result_path and os.path.exists(result_path):
                        clone_info["method"] = "rvc"
                        clone_info["confidence"] = 0.85
                        clone_info["speaker_id"] = "default"
                        logger.info(f"RVC voice clone successful: {output_path}")
                        return output_path, clone_info
            else:
                logger.info("No RVC generator weights found; trying OpenVoice")
        except Exception as e:
            logger.info(f"RVC unavailable ({e}); trying OpenVoice")

        # ── Attempt 3: OpenVoice (tone color cloning) ──
        try:
            from dreamtalk.voice.core.tts.openvoice.tone_color_clone import ToneColorConverter
            _ov_available = True
        except Exception:
            _ov_available = False

        if _ov_available:
            try:
                ckpt_path = os.path.join(self.model_dir, "checkpoints", "convert.pth")
                if os.path.exists(ckpt_path):
                    _tcc_device = "cuda" if torch.cuda.is_available() else "cpu"
                    converter = ToneColorConverter(ckpt_path, device=_tcc_device)
                    src_se = self._extract_speaker_embedding(source_audio_path)
                    if src_se is not None:
                        tgt_se = src_se
                        converter.convert(
                            audio_src_path=source_audio_path,
                            src_se=src_se,
                            tgt_se=tgt_se,
                            output_path=output_path,
                            message="@DreamTalk",
                        )
                        if os.path.exists(output_path):
                            clone_info["method"] = "openvoice"
                            clone_info["confidence"] = 0.8
                            logger.info(f"OpenVoice clone: {output_path}")
                            return output_path, clone_info
            except Exception as e:
                logger.info(f"OpenVoice unavailable ({e}); using structural clone")

        # ── Fallback: Structural clone (enhance + normalize + save) ──
        data, sr, _ = self.load_audio(source_audio_path)
        if data is None:
            return None, clone_info

        enhanced, _ = self.enhance_audio(data, sr)
        if SOUNDFILE_AVAILABLE:
            sf.write(output_path, enhanced, sr)
        elif SCIPY_AVAILABLE:
            wavfile.write(output_path, sr, (enhanced * 32767).astype(np.int16))
        else:
            self._write_raw_wav(output_path, enhanced, sr)

        clone_info["method"] = "structural"
        clone_info["confidence"] = 0.5
        return output_path, clone_info

    def _extract_speaker_embedding(self, audio_path: str):
        """Extract speaker embedding from audio for voice cloning."""
        try:
            from dreamtalk.voice.core.tts.openvoice.se_extractor import SpeakerEncoder
            _se_device = "cuda" if torch.cuda.is_available() else "cpu"
            encoder = SpeakerEncoder(_se_device)
            emb = encoder.extract(audio_path)
            return emb
        except Exception as e:
            logger.info(f"Speaker embedding failed: {e}")
            return None

    def _write_raw_wav(self, path: str, data: np.ndarray, sr: int):
        int_data = (data * 32767).astype(np.int16)
        with open(path, "wb") as f:
            f.write(b"RIFF")
            f.write(struct.pack("<I", 36 + len(int_data) * 2))
            f.write(b"WAVE")
            f.write(b"fmt ")
            f.write(struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16))
            f.write(b"data")
            f.write(struct.pack("<I", len(int_data) * 2))
            f.write(int_data.tobytes())

    # ─── TTS Synthesis ─────────────────────────────────────────────────────

    def generate_tts(self, text: str, voice_embedding: List[float] = None, output_dir: str = None,
                     voice_name: str = 'af_heart', lang_code: str = 'a', speed: float = 1.0) -> Tuple[Optional[str], Dict]:
        """Generate TTS with voice characteristics. Uses Edge-TTS (no torch)."""
        if output_dir is None:
            output_dir = self.assets_dir
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, f"tts_sample_{uuid.uuid4().hex[:8]}.wav")
        tts_info = {"method": "none", "duration": 0.0}

        # Try Edge-TTS first (no torch dependencies, free, high quality)
        try:
            import edge_tts
            import asyncio

            # Choose voice based on gender
            edge_voice = "en-US-JennyNeural"
            if voice_embedding and len(voice_embedding) > 30:
                pitch_val = voice_embedding[30]
                if pitch_val > 0.008:
                    edge_voice = "en-US-GuyNeural"

            async def _edge():
                comm = edge_tts.Communicate(text, edge_voice, rate="-10%", pitch="+0Hz")
                await comm.save(output_path)

            asyncio.run(_edge())
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                data, sr, _ = self.load_audio(output_path)
                tts_info["method"] = f"edgetts_{edge_voice}"
                tts_info["duration"] = round(len(data) / sr, 3) if data is not None else 0.0
                logger.info(f"Edge-TTS: {output_path} ({tts_info['duration']}s)")
                return output_path, tts_info
        except Exception as e:
            logger.info(f"Edge-TTS unavailable ({e}); trying other TTS")

        # Try Kokoro TTS
        try:
            from dreamtalk.voice.core.tts.kokoro_engine import KokoroTTSEngine
            _kokoro_device = "cuda" if torch.cuda.is_available() else "cpu"
            engine = KokoroTTSEngine(device=_kokoro_device)
            audio_chunks = engine.synthesize(text, voice=voice_name, lang_code=lang_code, speed=speed)
            if audio_chunks:
                combined = np.concatenate(audio_chunks)
                sf.write(output_path, combined, 24000)
                tts_info["method"] = f"kokoro_{voice_name}"
                tts_info["duration"] = round(len(combined) / 24000, 3)
                logger.info(f"Kokoro TTS: {output_path} ({tts_info['duration']}s)")
                return output_path, tts_info
        except Exception as e:
            logger.info(f"Kokoro unavailable ({e})")

        # Try TTS engine
        try:
            from dreamtalk.voice.core.tts.engine import TTSEngine
            engine = TTSEngine()
            engine.synthesize(text, output_path, voice_embedding=voice_embedding)
            if os.path.exists(output_path):
                data, sr, _ = self.load_audio(output_path)
                tts_info["method"] = "engine"
                tts_info["duration"] = round(len(data) / sr, 3) if data is not None else 0.0
                return output_path, tts_info
        except Exception as e:
            logger.info(f"TTS engine unavailable ({e})")

        # Placeholder audio with voice characteristics
        try:
            duration = max(1.0, min(len(text) * 0.08, 10.0))
            sr = 22050
            t = np.linspace(0, duration, int(sr * duration), endpoint=False)

            if voice_embedding and len(voice_embedding) > 30:
                pitch = 120 + (voice_embedding[30] * sr) if voice_embedding[30] > 0 else 220
                timbre = voice_embedding[26] * sr if voice_embedding[26] > 0 else 2000
            else:
                pitch = 220.0
                timbre = 2000.0

            audio = 0.3 * np.sin(2 * np.pi * pitch * t)
            audio += 0.15 * np.sin(2 * np.pi * timbre * t)
            audio += 0.05 * np.sin(2 * np.pi * (pitch * 3) * t)
            fade = np.linspace(0, 1, int(sr * 0.05))
            audio[:len(fade)] *= fade
            audio[-len(fade):] *= fade[::-1]

            sf.write(output_path, audio, sr)
            tts_info["method"] = "placeholder"
            tts_info["duration"] = round(duration, 3)
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            return None, tts_info

        return output_path, tts_info

    # ─── Main Run ──────────────────────────────────────────────────────────

    async def run(self, voice_paths: List[str], text_input: str = "", output_dir: str = None, enable_enhancement: bool = True) -> VoiceAnalysisResult:
        if not voice_paths:
            return VoiceAnalysisResult(error="No voice paths provided")

        primary_path = voice_paths[0]

        if output_dir is None:
            output_dir = self.assets_dir

        result = VoiceAnalysisResult()

        # Step 0: Load audio
        data, sr, info = self.load_audio(primary_path)
        if data is None or sr == 0:
            result.error = f"Cannot load audio: {primary_path}"
            return result

        result.sample_rate = sr
        result.bit_depth = info.get("bit_depth", 16)
        result.channels = info.get("channels", 1)
        result.duration_seconds = round(len(data) / sr, 3)

        if len(data) < sr * 0.02:
            result.error = "Audio too short (< 20ms)"
            return result

        # Step 1: Audio enhancement
        if enable_enhancement:
            enhanced, enh_info = self.enhance_audio(data, sr)
            result.enhancement_applied = True
            result.noise_reduction_db = 0.0
            result.snr_estimate = enh_info.get("snr_estimate", 0.0)
            data = enhanced

        # Step 2: Voice Activity Detection
        voiced_frames, vad_info = self.voice_activity_detection(data, sr)
        result.voice_detected = vad_info["voiced_ratio"] > 0.05
        result.voice_activity_frames = vad_info["voiced_frames"]
        result.voice_activity_ratio = vad_info["voiced_ratio"]

        if not result.voice_detected:
            return result

        # Step 3: Speaker Diarization (multi-speaker detection)
        speaker_segments, speaker_count = self.detect_speakers(
            data, sr, voiced_frames
        )
        result.speaker_segments = speaker_segments
        result.speaker_count = speaker_count
        result.speaker_diarization_method = "mfcc_agglomerative" if speaker_count > 0 else "none"

        # Step 4: Pitch
        pitch_info = self.extract_pitch(data, sr)
        result.pitch_mean = pitch_info.get("mean", 0.0)
        result.pitch_std = pitch_info.get("std", 0.0)
        result.pitch_median = pitch_info.get("median", 0.0)
        result.pitch_quartiles = pitch_info.get("quartiles")
        result.pitch_contour = pitch_info.get("contour")
        result.vibrato_rate = pitch_info.get("vibrato_rate", 0.0)
        result.vibrato_extent = pitch_info.get("vibrato_extent", 0.0)

        # Step 4: Energy
        energy_info = self.extract_energy(data, sr)
        result.energy_mean = energy_info["mean"]
        result.energy_std = energy_info["std"]
        result.energy_envelope = energy_info["envelope"]

        # Step 5: Spectral
        spectral_info = self.extract_spectral(data, sr)
        result.spectral_centroid_mean = spectral_info["centroid_mean"]
        result.spectral_bandwidth = spectral_info["bandwidth"]
        result.spectral_rolloff = spectral_info["rolloff"]
        result.spectral_contrast = spectral_info["contrast"]
        result.mfccs_mean = spectral_info["mfccs_mean"]
        result.mfccs_covariance = spectral_info["mfccs_covariance"]

        # Step 6: Formants
        formant_info = self.extract_formants(data, sr)
        result.formant_frequencies = formant_info.get("frequencies")
        result.formant_bandwidths = formant_info.get("bandwidths")

        # Step 7: Voice quality
        quality_info = self.extract_voice_quality(data, sr, pitch_info)
        result.jitter_local = quality_info["jitter_local"]
        result.jitter_rap = quality_info["jitter_rap"]
        result.jitter_ppq5 = quality_info["jitter_ppq5"]
        result.shimmer_local = quality_info["shimmer_local"]
        result.shimmer_apq3 = quality_info["shimmer_apq3"]
        result.shimmer_apq5 = quality_info["shimmer_apq5"]
        result.harmonicity_hnr = quality_info["hnr"]

        # Step 8: Prosody
        prosody_info = self.extract_prosody(data, sr, voiced_frames, vad_info)
        result.speaking_rate = prosody_info["speaking_rate"]
        result.words_per_minute = prosody_info["words_per_minute"]
        result.pause_duration_mean = prosody_info["pause_duration_mean"]
        result.pause_count = prosody_info["pause_count"]

        # Step 9: Voice embedding
        result.voice_embedding = self.compute_voice_embedding(data, sr)
        result.embedding_dim = len(result.voice_embedding)
        result.timbre_embedding = result.voice_embedding

        # Step 10: Gender / age prediction
        pred = self.predict_gender_age(pitch_info, spectral_info)
        result.gender_prediction = pred["gender"]
        result.age_prediction = pred["age"]

        # Step 11: Clone voice
        cloned_path, clone_info = self.clone_voice(primary_path, output_dir)
        result.cloned_voice_path = cloned_path
        result.clone_method = clone_info["method"]
        result.clone_confidence = clone_info["confidence"]

        # Step 12: TTS
        if text_input:
            tts_path, tts_info = self.generate_tts(text_input, result.voice_embedding, output_dir)
            result.tts_sample_path = tts_path
            result.tts_method = tts_info["method"]
            result.tts_duration_seconds = tts_info["duration"]

        return result
