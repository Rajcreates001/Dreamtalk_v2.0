# Dreamtalk - Cognition Module
# Extracted from NeurologiqueTWIN (https://github.com/anomalyco/NeurologiqueTWIN)
# License: MIT

"""
EEG Signal Processor for NeurologiqueTWIN.

Implements the preprocessing pipeline used in the SeizeIT2 dataset preparation:
  1. Band-pass filtering (0.5 - 50 Hz)
  2. Notch filtering at 50/60 Hz
  3. Wavelet denoising (db4)
  4. Robust normalisation to [-1, 1]
  5. Epoch segmentation (sliding window)

Also includes time-series-to-image transforms:
  - GASF (Gramian Angular Summation Field)
  - MTF (Markov Transition Field)
  - RP (Recurrence Plot)
  - RGB fusion of all three
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

import numpy as np

try:
    from pywt import wavedec, threshold, waverec
    _PYWT_AVAILABLE = True
except ImportError:
    _PYWT_AVAILABLE = False

try:
    from pyts.image import GramianAngularField, MarkovTransitionField, RecurrencePlot
    _PYTS_AVAILABLE = True
except ImportError:
    _PYTS_AVAILABLE = False


# ==============================================================================
# EEG Signal Processor
# ==============================================================================

class EEGProcessor:
    """
    End-to-end EEG preprocessing pipeline.

    Parameters
    ----------
    fs : float — Sampling frequency in Hz (default 256 Hz)
    lowcut : float — Low-frequency cutoff for band-pass (default 0.5 Hz)
    highcut : float — High-frequency cutoff for band-pass (default 50 Hz)
    notch_freq : float — Notch filter frequency (default 50 Hz)
    epoch_len_s : float — Epoch length in seconds for segmentation (default 4 s)
    overlap : float — Fractional overlap between epochs (default 0.5)
    wavelet : str — PyWavelets wavelet family (default "db4")
    wavelet_level : int — Decomposition level (default 4)
    """

    def __init__(
        self,
        fs: float = 256.0,
        lowcut: float = 0.5,
        highcut: float = 50.0,
        notch_freq: float = 50.0,
        epoch_len_s: float = 4.0,
        overlap: float = 0.5,
        wavelet: str = "db4",
        wavelet_level: int = 4,
    ) -> None:
        self.fs = fs
        self.lowcut = lowcut
        self.highcut = highcut
        self.notch_freq = notch_freq
        self.epoch_len_s = epoch_len_s
        self.overlap = overlap
        self.wavelet = wavelet
        self.wavelet_level = wavelet_level
        self._epoch_samples = int(fs * epoch_len_s)
        self._step_samples = int(self._epoch_samples * (1 - overlap))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, raw: np.ndarray) -> np.ndarray:
        x = raw.astype(np.float64).copy()
        x = self._bandpass(x)
        x = self._notch(x)
        x = self._wavelet_denoise(x)
        x = self._normalise(x)
        return x.astype(np.float32)

    def segment(self, signal: np.ndarray) -> np.ndarray:
        epochs: List[np.ndarray] = []
        start = 0
        while start + self._epoch_samples <= len(signal):
            epochs.append(signal[start: start + self._epoch_samples])
            start += self._step_samples
        return np.stack(epochs) if epochs else np.empty((0, self._epoch_samples), dtype=np.float32)

    def process_and_segment(self, raw: np.ndarray) -> np.ndarray:
        return self.segment(self.process(raw))

    # ------------------------------------------------------------------
    # Spectral features
    # ------------------------------------------------------------------

    def spectral_energy(self, epoch: np.ndarray) -> float:
        fft = np.fft.rfft(epoch)
        freqs = np.fft.rfftfreq(len(epoch), d=1.0 / self.fs)
        mask = (freqs >= 1.0) & (freqs <= 30.0)
        power = np.abs(fft[mask]) ** 2
        total = np.abs(fft) ** 2
        return float(power.sum() / (total.sum() + 1e-12))

    def band_powers(self, epoch: np.ndarray) -> dict:
        fft = np.fft.rfft(epoch)
        freqs = np.fft.rfftfreq(len(epoch), d=1.0 / self.fs)
        power = np.abs(fft) ** 2
        total = power.sum() + 1e-12

        def bp(lo, hi):
            return float(power[(freqs >= lo) & (freqs < hi)].sum() / total)

        return {
            "delta": bp(0.5, 4.0),
            "theta": bp(4.0, 8.0),
            "alpha": bp(8.0, 13.0),
            "beta":  bp(13.0, 30.0),
            "gamma": bp(30.0, 50.0),
        }

    # ------------------------------------------------------------------
    # Private DSP helpers
    # ------------------------------------------------------------------

    def _bandpass(self, x: np.ndarray) -> np.ndarray:
        fft = np.fft.rfft(x)
        freqs = np.fft.rfftfreq(len(x), d=1.0 / self.fs)
        fft[(freqs < self.lowcut) | (freqs > self.highcut)] = 0.0
        return np.fft.irfft(fft, n=len(x))

    def _notch(self, x: np.ndarray, bw: float = 1.0) -> np.ndarray:
        fft = np.fft.rfft(x)
        freqs = np.fft.rfftfreq(len(x), d=1.0 / self.fs)
        fft[np.abs(freqs - self.notch_freq) < bw] = 0.0
        return np.fft.irfft(fft, n=len(x))

    def _wavelet_denoise(self, x: np.ndarray) -> np.ndarray:
        if _PYWT_AVAILABLE:
            coeffs = wavedec(x, self.wavelet, level=self.wavelet_level)
            sigma = np.median(np.abs(coeffs[-1])) / 0.6745
            thr = sigma * np.sqrt(2 * np.log(len(x)))
            coeffs_thr = [threshold(c, thr, mode="soft") for c in coeffs]
            return waverec(coeffs_thr, self.wavelet)[: len(x)]
        kernel = np.ones(5) / 5.0
        return np.convolve(x, kernel, mode="same")

    @staticmethod
    def _normalise(x: np.ndarray) -> np.ndarray:
        p5, p95 = np.percentile(x, [5, 95])
        denom = max(p95 - p5, 1e-8)
        return np.clip((x - p5) / denom * 2.0 - 1.0, -1.0, 1.0)


# ==============================================================================
# Time-Series to Image Transforms
# ==============================================================================

IMAGE_SIZE = 64


def gasf(signal: np.ndarray, image_size: int = IMAGE_SIZE) -> np.ndarray:
    if _PYTS_AVAILABLE:
        gaf = GramianAngularField(image_size=image_size, method="summation")
        return gaf.fit_transform(signal.reshape(1, -1))[0].astype(np.float32)

    x = _resize_1d(signal, image_size)
    x = _minmax_scale(x, -1.0, 1.0)
    x = np.clip(x, -1.0, 1.0)
    phi = np.arccos(x)
    result = np.cos(phi[:, None] + phi[None, :])
    return result.astype(np.float32)


def mtf(signal: np.ndarray, image_size: int = IMAGE_SIZE, n_bins: int = 8) -> np.ndarray:
    if _PYTS_AVAILABLE:
        mtf_ = MarkovTransitionField(image_size=image_size, n_bins=n_bins)
        return mtf_.fit_transform(signal.reshape(1, -1))[0].astype(np.float32)

    n = len(signal)
    bins = np.linspace(signal.min(), signal.max() + 1e-8, n_bins + 1)
    q = np.digitize(signal, bins) - 1
    q = np.clip(q, 0, n_bins - 1)

    W = np.zeros((n_bins, n_bins), dtype=np.float64)
    for a, b in zip(q[:-1], q[1:]):
        W[a, b] += 1.0
    row_sums = W.sum(axis=1, keepdims=True)
    W /= np.where(row_sums == 0, 1.0, row_sums)

    full_mtf = W[q[:, None], q[None, :]]
    result = _resize_2d(full_mtf, image_size)
    return result.astype(np.float32)


def recurrence_plot(
    signal: np.ndarray,
    image_size: int = IMAGE_SIZE,
    threshold: Optional[float] = None,
    percentage: float = 0.1,
) -> np.ndarray:
    if _PYTS_AVAILABLE:
        rp = RecurrencePlot(threshold=threshold, percentage=percentage * 100)
        raw = rp.fit_transform(signal.reshape(1, -1))[0].astype(np.float32)
        if raw.shape[0] != image_size:
            raw = _resize_2d(raw, image_size).astype(np.float32)
        return raw

    x = _resize_1d(signal, image_size)
    x = _minmax_scale(x, 0.0, 1.0)
    dist = np.abs(x[:, None] - x[None, :])

    if threshold is not None:
        result = (dist <= threshold).astype(np.float32)
    else:
        dmax = dist.max()
        result = 1.0 - dist / (dmax + 1e-8)
    return result.astype(np.float32)


def to_rgb(signal: np.ndarray, image_size: int = IMAGE_SIZE, n_bins: int = 8) -> np.ndarray:
    g = gasf(signal, image_size)
    m = mtf(signal, image_size, n_bins=n_bins)
    r = recurrence_plot(signal, image_size)

    def norm01(x):
        lo, hi = x.min(), x.max()
        return (x - lo) / (hi - lo + 1e-8)

    rgb = np.stack([norm01(g), norm01(m), norm01(r)], axis=-1)
    return rgb.astype(np.float32)


class TimeSeriesTransformer:
    def __init__(self, image_size: int = IMAGE_SIZE, n_bins: int = 8) -> None:
        self.image_size = image_size
        self.n_bins = n_bins

    def transform(self, signal: np.ndarray, method: Literal["gasf", "mtf", "rp", "rgb"] = "rgb") -> np.ndarray:
        if method == "gasf":
            return gasf(signal, self.image_size)
        if method == "mtf":
            return mtf(signal, self.image_size, n_bins=self.n_bins)
        if method == "rp":
            return recurrence_plot(signal, self.image_size)
        return to_rgb(signal, self.image_size, n_bins=self.n_bins)

    def transform_all(self, signal: np.ndarray) -> Dict[str, np.ndarray]:
        return {
            "gasf": gasf(signal, self.image_size),
            "mtf":  mtf(signal, self.image_size, self.n_bins),
            "rp":   recurrence_plot(signal, self.image_size),
            "rgb":  to_rgb(signal, self.image_size, self.n_bins),
        }


# ------------------------------------------------------------------
# Internal utilities
# ------------------------------------------------------------------

def _minmax_scale(x: np.ndarray, lo: float = 0.0, hi: float = 1.0) -> np.ndarray:
    x_min, x_max = x.min(), x.max()
    denom = x_max - x_min if x_max != x_min else 1.0
    return (x - x_min) / denom * (hi - lo) + lo


def _resize_1d(x: np.ndarray, n: int) -> np.ndarray:
    if len(x) == n:
        return x
    idx = np.linspace(0, len(x) - 1, n)
    return np.interp(idx, np.arange(len(x)), x)


def _resize_2d(x: np.ndarray, n: int) -> np.ndarray:
    h, w = x.shape
    row_idx = np.linspace(0, h - 1, n)
    col_idx = np.linspace(0, w - 1, n)
    ri = np.floor(row_idx).astype(int).clip(0, h - 2)
    ci = np.floor(col_idx).astype(int).clip(0, w - 2)
    dr = row_idx - ri
    dc = col_idx - ci
    result = (
        x[ri[:, None], ci[None, :]] * (1 - dr[:, None]) * (1 - dc[None, :])
        + x[ri[:, None] + 1, ci[None, :]] * dr[:, None] * (1 - dc[None, :])
        + x[ri[:, None], ci[None, :] + 1] * (1 - dr[:, None]) * dc[None, :]
        + x[ri[:, None] + 1, ci[None, :] + 1] * dr[:, None] * dc[None, :]
    )
    return result
