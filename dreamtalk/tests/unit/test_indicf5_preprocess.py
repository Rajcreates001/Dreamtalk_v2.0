"""Unit tests for the vendored IndicF5 reference-audio preprocessing.

Covers the numpy/soundfile port in
``dreamtalk/voice/core/tts/indicf5/infer/utils_infer.py`` that replaced the
pydub/ffprobe pipeline (which crashed on machines without ffprobe) and the
soundfile load path that replaced ``torchaudio.load`` (broken without
torchcodec).

Run:
    dt_venv/Scripts/python.exe -m pytest dreamtalk/tests/unit/test_indicf5_preprocess.py -v

Notes:
- No model weights are needed: only pure preprocessing functions are tested.
- ``transcribe()`` is never triggered because every call passes explicit
  ``ref_text`` (the ASR path would pull transformers, which is broken on this
  box by design of earlier sessions).
- The heavy module import (torch/matplotlib/vocos) happens once per session
  via a module-scoped fixture.
"""

import os
import pathlib
import sys

import numpy as np
import pytest
import soundfile as sf

# Must be set before torch is imported anywhere in the chain.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

_HERE = pathlib.Path(__file__).resolve()
_DREAMTALK = _HERE.parents[2]  # .../dreamtalk
_TTS_DIR = _DREAMTALK / "voice" / "core" / "tts"

SR = 24000


@pytest.fixture(scope="module")
def uvi():
    """Import the vendored utils_infer once; returns the module."""
    if str(_TTS_DIR) not in sys.path:
        sys.path.insert(0, str(_TTS_DIR))
    from indicf5.infer import utils_infer as m

    return m


@pytest.fixture()
def keep_paths():
    """Collect temp wav paths produced by preprocess_ref_audio_text for cleanup."""
    paths = []
    yield paths.append
    for p in paths:
        try:
            os.unlink(p)
        except OSError:
            pass


def burst(sec: float, sr: int = SR, amp: float = 0.4) -> np.ndarray:
    """Amplitude-modulated tone standing in for voiced speech."""
    t = np.linspace(0, sec, int(sr * sec), endpoint=False)
    return (amp * np.sin(2 * np.pi * 220 * t) * (1 + np.sin(2 * np.pi * 3 * t))).astype(np.float32)


def silence(sec: float, sr: int = SR) -> np.ndarray:
    return np.zeros(int(sr * sec), dtype=np.float32)


def write_wav(tmp_path, data: np.ndarray, sr: int = SR) -> str:
    path = str(tmp_path / f"ref_{abs(hash(data.tobytes())) % 10**8}.wav")
    sf.write(path, data, sr)
    return path


# ---------------------------------------------------------------------------
# _frame_dbfs
# ---------------------------------------------------------------------------


def test_frame_dbfs_loud_vs_silent(uvi):
    dbfs, frame_len = uvi._frame_dbfs(burst(1.0), SR)
    assert frame_len == SR // 100  # 10 ms frames at 24 kHz
    assert dbfs.size == 100
    assert dbfs.max() == pytest.approx(20 * np.log10(0.8), abs=0.5)  # peak ~0.4*2


def test_frame_dbfs_all_silent_floor(uvi):
    dbfs, _ = uvi._frame_dbfs(silence(0.5), SR)
    assert dbfs.size > 0
    assert (dbfs < -60).all()


# ---------------------------------------------------------------------------
# _split_on_silence_np
# ---------------------------------------------------------------------------


def test_split_on_silence_two_chunks(uvi):
    wav = np.concatenate([burst(2), silence(2), burst(3)])
    chunks = uvi._split_on_silence_np(wav, SR, min_silence_ms=1000,
                                      silence_thresh_dbfs=-50, keep_silence_ms=1000)
    assert len(chunks) == 2
    # Each chunk padded by keep_silence on both sides.
    for start, end in chunks:
        assert end > start


def test_split_on_silence_short_gap_stays_one_chunk(uvi):
    wav = np.concatenate([burst(2), silence(0.3), burst(2)])
    chunks = uvi._split_on_silence_np(wav, SR, min_silence_ms=1000,
                                      silence_thresh_dbfs=-50, keep_silence_ms=1000)
    assert len(chunks) == 1


# ---------------------------------------------------------------------------
# _clip_reference_short
# ---------------------------------------------------------------------------


def test_clip_keeps_short_reference_whole(uvi):
    wav = np.concatenate([burst(2), silence(2), burst(3)])
    out = uvi._clip_reference_short(wav, SR, show_info=lambda *_: None)
    # Both speech chunks fit well under 15 s -> essentially everything kept.
    assert out.shape[0] / SR >= 6.5
    assert out.shape[0] <= wav.shape[0]


def test_clip_hard_caps_oversized_continuous_speech(uvi):
    out = uvi._clip_reference_short(burst(20), SR, show_info=lambda *_: None)
    # Falls through both detection passes to the hard clip at exactly 15 s.
    assert out.shape[0] == int(15.0 * SR)


def test_clip_early_break_on_many_bursts(uvi):
    segs = []
    for _ in range(8):
        segs.append(burst(3))
        segs.append(silence(1.2))
    raw = np.concatenate(segs)
    out = uvi._clip_reference_short(raw, SR, show_info=lambda *_: None)
    dur = out.shape[0] / SR
    assert 8.0 < dur <= 15.05   # stopped accumulating before 15 s
    assert dur < raw.shape[0] / SR / 2  # far less than all 24 s of speech


# ---------------------------------------------------------------------------
# remove_silence_edges
# ---------------------------------------------------------------------------


def test_remove_silence_edges_trims_both_ends(uvi):
    wav = np.concatenate([silence(0.5), burst(1.0), silence(0.5)])
    out = uvi.remove_silence_edges(wav, SR)
    assert out.shape[0] / SR == pytest.approx(1.0, abs=0.02)


def test_remove_silence_edges_all_silent_returns_input(uvi):
    wav = silence(1.0)
    out = uvi.remove_silence_edges(wav, SR)
    assert out.shape[0] == wav.shape[0]


# ---------------------------------------------------------------------------
# _load_audio_any
# ---------------------------------------------------------------------------


def test_load_audio_any_downmixes_stereo(uvi, tmp_path):
    left = burst(1.0)
    right = np.zeros_like(left)
    path = str(tmp_path / "stereo.wav")
    sf.write(path, np.stack([left, right], axis=1), SR)

    mono, sr = uvi._load_audio_any(path)
    assert sr == SR
    assert mono.dtype == np.float32
    # (tone + 0) / 2 -> half amplitude
    assert np.abs(mono).max() == pytest.approx(np.abs(left).max() / 2, rel=0.01)


# ---------------------------------------------------------------------------
# preprocess_ref_audio_text — the full pipeline
# ---------------------------------------------------------------------------


def test_preprocess_multichunk_roundtrip(uvi, tmp_path, keep_paths):
    src = write_wav(tmp_path, np.concatenate([burst(2), silence(2), burst(3)]))
    out, text = uvi.preprocess_ref_audio_text(src, "reference text here.")
    keep_paths(out)

    data, sr = sf.read(out)
    assert sr == SR
    # bursts (2+3 s) + keep-silence pads between/after chunks + 50 ms tail
    assert len(data) / SR == pytest.approx(7.05, abs=0.25)
    # punctuation normalization
    assert text == "reference text here. "


def test_preprocess_appends_punctuation_variants(uvi, tmp_path, keep_paths):
    src = write_wav(tmp_path, burst(1))

    _, text_plain = uvi.preprocess_ref_audio_text(src, "hello world", clip_short=False)
    assert text_plain == "hello world. "

    _, text_cjk = uvi.preprocess_ref_audio_text(src, "你好世界。", clip_short=False)
    assert text_cjk.endswith("。") and not text_cjk.endswith("。 ")

    _, text_dot = uvi.preprocess_ref_audio_text(src, "already dotted.", clip_short=False)
    assert text_dot == "already dotted. "


def test_preprocess_clips_long_input_and_keeps_sr(uvi, tmp_path, keep_paths):
    src = write_wav(tmp_path, burst(20))
    out, _ = uvi.preprocess_ref_audio_text(src, "long reference.")
    keep_paths(out)

    data, sr = sf.read(out)
    assert sr == SR
    assert len(data) / SR == pytest.approx(15.05, abs=0.02)  # 15 s cap + tail


def test_preprocess_all_silence_does_not_crash(uvi, tmp_path, keep_paths):
    src = write_wav(tmp_path, silence(3))
    out, text = uvi.preprocess_ref_audio_text(src, "silence.")
    keep_paths(out)

    data, _ = sf.read(out)
    assert 0.4 <= len(data) / SR <= 0.7  # degenerate guard fills ~0.5 s + tail
    assert text == "silence. "
