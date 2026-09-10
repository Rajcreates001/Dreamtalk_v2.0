"""Unit tests for DreamTalk voice sub-modules:
  - Prosody Controller (emotion presets, parameter bounds)
  - Voice-Face Sync (audio→blendshape mapping)

Run:
    dt_venv/Scripts/python.exe -m pytest dreamtalk/tests/unit/test_voice_modules.py -v

Note: Language detection tests are excluded from this file because the
translation module imports torch/jieba (25s cold start). Test language
detection via the backend API endpoint instead.
"""

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Prosody Controller
# ---------------------------------------------------------------------------

class TestProsodyController:
    """Test prosody parameter generation."""

    def test_default_prosody(self):
        from dreamtalk.voice.core.tts.prosody import ProsodyParams
        p = ProsodyParams()
        assert p.speed == 1.0
        assert p.pitch_semitones == 0.0
        assert p.intensity == 0.5

    def test_speed_clamped(self):
        from dreamtalk.voice.core.tts.prosody import ProsodyParams
        assert ProsodyParams(speed=3.0).speed == 2.0  # Clamped to max
        assert ProsodyParams(speed=0.1).speed == 0.5  # Clamped to min

    def test_pitch_clamped(self):
        from dreamtalk.voice.core.tts.prosody import ProsodyParams
        assert ProsodyParams(pitch_semitones=20).pitch_semitones == 12
        assert ProsodyParams(pitch_semitones=-20).pitch_semitones == -12

    def test_happy_prosody(self):
        from dreamtalk.voice.core.tts.prosody import prosody_for_emotion
        p = prosody_for_emotion("happy", intensity=0.8)
        assert p.speed > 1.0  # Happy is faster
        assert p.pitch_semitones > 0  # Happy is higher pitch
        assert p.warmth > 0.5  # Happy is warm

    def test_sad_prosody(self):
        from dreamtalk.voice.core.tts.prosody import prosody_for_emotion
        p = prosody_for_emotion("sad", intensity=0.8)
        assert p.speed < 1.0  # Sad is slower
        assert p.pitch_semitones < 0  # Sad is lower pitch
        assert p.intensity < 0.5  # Sad is softer

    def test_angry_prosody(self):
        from dreamtalk.voice.core.tts.prosody import prosody_for_emotion
        p = prosody_for_emotion("angry", intensity=0.9)
        assert p.speed > 1.0  # Angry is fast
        assert p.intensity > 0.7  # Angry is loud
        assert p.warmth < 0.4  # Angry is cold

    def test_zero_intensity_gives_neutral(self):
        from dreamtalk.voice.core.tts.prosody import prosody_for_emotion
        p = prosody_for_emotion("happy", intensity=0.0)
        assert p.speed == pytest.approx(1.0, abs=0.01)
        assert p.pitch_semitones == pytest.approx(0.0, abs=0.1)

    def test_to_dict_roundtrip(self):
        from dreamtalk.voice.core.tts.prosody import ProsodyParams
        p = ProsodyParams(speed=1.2, pitch_semitones=3.0, intensity=0.8)
        d = p.to_dict()
        p2 = ProsodyParams.from_dict(d)
        assert p2.speed == 1.2
        assert p2.pitch_semitones == 3.0

    def test_all_emotions_have_prosody(self):
        from dreamtalk.voice.core.tts.prosody import EMOTION_PROSODY
        for emotion in ["happy", "sad", "angry", "excited", "calm", "surprised", "fearful", "neutral", "loving"]:
            assert emotion in EMOTION_PROSODY, f"Missing prosody for: {emotion}"

    def test_speed_multiplier_property(self):
        from dreamtalk.voice.core.tts.prosody import ProsodyParams
        p = ProsodyParams(speed=1.5)
        assert p.speed_multiplier == 1.5

    def test_pitch_multiplier_property(self):
        from dreamtalk.voice.core.tts.prosody import ProsodyParams
        p = ProsodyParams(pitch_semitones=12)
        assert p.pitch_multiplier == pytest.approx(2.0, abs=0.01)  # 12 semitones = octave


# ---------------------------------------------------------------------------
# Voice-Face Sync
# ---------------------------------------------------------------------------

class TestVoiceFaceSync:
    """Test audio-to-face parameter mapping."""

    def _get_sync(self):
        from dreamtalk.pipeline.voice_face_sync import VoiceFaceSync
        return VoiceFaceSync(sample_rate=24000)

    def test_loud_audio_opens_mouth(self):
        sync = self._get_sync()
        audio = np.ones(24000, dtype=np.float32) * 0.5  # Loud constant
        params = sync.audio_to_face(audio, emotion="neutral")
        assert params.mouth_open > 0.3

    def test_silence_gives_resting_face(self):
        sync = self._get_sync()
        silence = np.zeros(24000, dtype=np.float32)
        params = sync.audio_to_face(silence, emotion="neutral")
        assert params.mouth_open == 0.0
        assert params.jaw_open == 0.0

    def test_happy_emotion_adds_smile(self):
        sync = self._get_sync()
        audio = np.ones(24000, dtype=np.float32) * 0.3
        params = sync.audio_to_face(audio, emotion="happy", emotion_intensity=0.8)
        assert params.mouth_width > 0.3

    def test_sad_emotion_frowns(self):
        sync = self._get_sync()
        params = sync._resting_face("sad", 0.8)
        assert params.mouth_width <= 0.0  # Frown

    def test_surprised_widens_eyes(self):
        sync = self._get_sync()
        params = sync._resting_face("surprised", 0.9)
        assert params.eyebrow_raise > 0.5

    def test_empty_audio_gives_resting(self):
        sync = self._get_sync()
        params = sync.audio_to_face(np.array([], dtype=np.float32))
        assert params.mouth_open == 0.0

    def test_sequence_generates_frames(self):
        sync = self._get_sync()
        audio = np.random.randn(24000 * 2).astype(np.float32) * 0.2
        seq = sync.audio_to_face_sequence(audio, chunk_size=600)
        assert len(seq) == 80  # 48000 / 600 = 80

    def test_blendshape_dict_has_required_keys(self):
        sync = self._get_sync()
        params = sync._resting_face("neutral", 0.5)
        bs = params.to_blendshapes()
        required = {"mouthOpen", "jawOpen", "mouthSmileLeft", "eyeBlinkLeft", "eyeBlinkRight"}
        assert required.issubset(set(bs.keys()))

    def test_smoothing_reduces_jumps(self):
        sync = self._get_sync()
        audio1 = np.ones(600, dtype=np.float32) * 0.1
        audio2 = np.ones(600, dtype=np.float32) * 0.2
        p1 = sync.audio_to_face(audio1, emotion="neutral")
        p2 = sync.audio_to_face(audio2, emotion="neutral")
        # Smoothed values shouldn't jump by more than 2x the raw delta
        raw_delta = abs(0.2 - 0.1) * 8  # The 8x multiplier in audio_to_face
        assert abs(p2.mouth_open - p1.mouth_open) < raw_delta

    def test_fearful_widens_eyes(self):
        sync = self._get_sync()
        params = sync._resting_face("fearful", 0.8)
        assert params.eye_open > 0.9

    def test_angry_furrows_brows(self):
        sync = self._get_sync()
        params = sync._resting_face("angry", 0.8)
        assert params.eyebrow_raise < 0.0  # Negative = furrowed
        assert params.nose_wrinkle > 0.2

    def test_pitch_estimation(self):
        sync = self._get_sync()
        # Generate a 440Hz sine wave
        t = np.linspace(0, 0.05, int(24000 * 0.05), endpoint=False)
        audio = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)
        pitch = sync._estimate_pitch(audio, 24000)
        # Should be approximately 440 Hz (within 20%)
        assert 350 < pitch < 530
