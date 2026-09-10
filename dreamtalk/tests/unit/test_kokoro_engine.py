"""Unit tests for the Kokoro TTS engine.

Covers:
  - Chunk collection and concatenation (synthesize / synthesize_full)
  - Voice fallback on synthesis failure (language fallback, voice rotation)
  - Emotion-based voice selection
  - Language detection from Unicode script
  - Voice mixing (voice_mix)
  - Best-voice selection with quality hints
  - synthesize_from_tokens

All KPipeline and KModel calls are mocked — no model weights needed.

Run:
    dt_venv/Scripts/python.exe -m pytest dreamtalk/tests/unit/test_kokoro_engine.py -v
"""

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SR = 24000


def _make_chunk(duration_s: float = 0.5, sr: int = SR) -> np.ndarray:
    """Synthetic audio chunk (sine wave)."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    return (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


class FakeResult:
    """Mimics KPipeline.Result — must be unpackable as (gs, ps, audio)."""
    def __init__(self, graphemes, phonemes, tokens, output, audio=None, text_index=0):
        self.graphemes = graphemes
        self.phonemes = phonemes
        self.tokens = tokens
        self.output = output
        self.audio = audio
        self.text_index = text_index

    def __iter__(self):
        """Yield (graphemes, phonemes, audio) so the engine can unpack it."""
        yield self.graphemes
        yield self.phonemes
        yield self.audio

    def __repr__(self):
        return f"FakeResult({self.graphemes!r}, {self.phonemes!r}, audio={self.audio!r})"


class FakePipeline:
    """Callable mock that replaces KPipeline instances."""
    def __init__(self, gen_fn=None, error=None):
        self._gen_fn = gen_fn
        self._error = error

    def __call__(self, text, voice="af_heart", speed=1.0, **kwargs):
        if self._error:
            raise self._error
        if self._gen_fn:
            yield from self._gen_fn(text, voice, speed)
        # Default: yield nothing


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def engine(monkeypatch):
    """Create a KokoroTTSEngine with a fully mocked pipeline."""
    # Patch KPipeline import so __init__ doesn't load real weights
    fake_pipeline_cls = type("KPipeline", (), {
        "__init__": lambda self, **kw: None,
    })

    monkeypatch.setattr(
        "dreamtalk.voice.core.tts.kokoro_engine.KPipeline",
        fake_pipeline_cls,
    )

    from dreamtalk.voice.core.tts.kokoro_engine import KokoroTTSEngine
    eng = KokoroTTSEngine(device="cpu")
    return eng


# ---------------------------------------------------------------------------
# Chunk collection and concatenation
# ---------------------------------------------------------------------------

class TestChunkCollection:
    """Test that synthesize() collects pipeline chunks into a list."""

    def test_single_chunk_collected(self, engine, monkeypatch):
        """Pipeline yielding one chunk → synthesize returns list of one."""
        chunk = _make_chunk(0.5)

        def gen(text, voice, speed):
            yield FakeResult("Hello", "h EH l OW", [0], None, audio=chunk)

        engine._pipelines["a"] = FakePipeline(gen_fn=gen)

        result = engine.synthesize("Hello", voice="af_heart", lang_code="a")
        assert len(result) == 1
        np.testing.assert_array_equal(result[0], chunk)

    def test_multiple_chunks_collected(self, engine):
        """Multiple pipeline yields → multiple chunks in the list."""
        chunks = [_make_chunk(0.3), _make_chunk(0.4), _make_chunk(0.2)]

        def gen(text, voice, speed):
            for i, c in enumerate(chunks):
                yield FakeResult(f"seg_{i}", f"ph_{i}", [i], None, audio=c)

        engine._pipelines["a"] = FakePipeline(gen_fn=gen)

        result = engine.synthesize("Hello world", voice="af_heart", lang_code="a")
        assert len(result) == 3
        for i, c in enumerate(chunks):
            np.testing.assert_array_equal(result[i], c)

    def test_synthesize_full_concatenates(self, engine):
        """synthesize_full should concatenate all chunks into one array."""
        chunks = [_make_chunk(0.3), _make_chunk(0.4)]

        def gen(text, voice, speed):
            for i, c in enumerate(chunks):
                yield FakeResult(f"seg_{i}", f"ph_{i}", [i], None, audio=c)

        engine._pipelines["a"] = FakePipeline(gen_fn=gen)

        result = engine.synthesize_full("Hello world", voice="af_heart", lang_code="a")
        assert result is not None
        expected_len = sum(len(c) for c in chunks)
        assert len(result) == expected_len


# ---------------------------------------------------------------------------
# Voice fallback on failure
# ---------------------------------------------------------------------------

class TestVoiceFallback:
    """Test fallback behavior when synthesis fails."""

    def test_non_english_falls_back_to_english(self, engine, monkeypatch):
        """When Hindi pipeline fails, engine falls back to American English."""
        call_log = []

        # Hindi pipeline raises, English pipeline succeeds
        def hindi_gen(text, voice, speed):
            call_log.append(("hindi", voice))
            raise RuntimeError("Hindi pipeline failed")

        def english_gen(text, voice, speed):
            call_log.append(("english", voice))
            yield FakeResult("Hello", "h EH l OW", [0], None, audio=_make_chunk(0.5))

        engine._pipelines["h"] = FakePipeline(gen_fn=hindi_gen)
        engine._pipelines["a"] = FakePipeline(gen_fn=english_gen)

        result = engine.synthesize("नमस्ते", voice="hf_alpha", lang_code="h")
        assert len(result) == 1
        assert ("hindi", "hf_alpha") in call_log
        assert ("english", "hf_alpha") in call_log

    def test_english_fallback_rotates_voices(self, engine, monkeypatch):
        """When primary English voice fails, engine tries QUALITY_FALLBACK voices."""
        from dreamtalk.voice.core.tts.kokoro_engine import QUALITY_FALLBACK
        call_log = []

        def failing_gen(text, voice, speed):
            call_log.append(voice)
            if voice == "af_heart":
                raise RuntimeError("Primary voice failed")
            # Succeed on fallback voice
            yield FakeResult("Hello", "h EH l OW", [0], None, audio=_make_chunk(0.5))

        engine._pipelines["a"] = FakePipeline(gen_fn=failing_gen)

        result = engine.synthesize("Hello", voice="af_heart", lang_code="a")
        assert len(result) == 1
        # af_heart was tried and failed, then a fallback was tried
        assert "af_heart" in call_log
        assert len(call_log) >= 2

    def test_all_voices_fail_returns_empty(self, engine, monkeypatch):
        """If every voice in the fallback chain fails, return empty list."""
        def always_fail_gen(text, voice, speed):
            raise RuntimeError(f"Voice {voice} failed")

        engine._pipelines["a"] = FakePipeline(gen_fn=always_fail_gen)

        result = engine.synthesize("Hello", voice="af_heart", lang_code="a")
        assert result == []


# ---------------------------------------------------------------------------
# Emotion voice selection
# ---------------------------------------------------------------------------

class TestEmotionVoiceSelection:
    """Test that select_voice_for_emotion returns the correct voice."""

    def test_happy_maps_to_heart(self, engine):
        assert engine.select_voice_for_emotion("happy") == "af_heart"

    def test_sad_maps_to_nicole(self, engine):
        assert engine.select_voice_for_emotion("sad") == "af_nicole"

    def test_angry_maps_to_adam(self, engine):
        assert engine.select_voice_for_emotion("angry") == "am_adam"

    def test_surprised_maps_to_bella(self, engine):
        assert engine.select_voice_for_emotion("surprised") == "af_bella"

    def test_neutral_maps_to_heart(self, engine):
        assert engine.select_voice_for_emotion("neutral") == "af_heart"

    def test_unknown_emotion_falls_back_to_gender(self, engine):
        assert engine.select_voice_for_emotion("weird_mood", "male") == "am_adam"

    def test_unknown_emotion_no_gender_defaults_to_heart(self, engine):
        assert engine.select_voice_for_emotion("weird_mood") == "af_heart"

    def test_none_emotion_no_gender_defaults_to_heart(self, engine):
        assert engine.select_voice_for_emotion(None, None) == "af_heart"

    def test_emotion_is_case_insensitive(self, engine):
        assert engine.select_voice_for_emotion("HAPPY") == "af_heart"
        assert engine.select_voice_for_emotion("Sad") == "af_nicole"


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

class TestLanguageDetection:
    """Test detect_language() via Unicode script ranges."""

    def test_english_returns_a(self, engine):
        assert engine.detect_language("Hello world") == "a"

    def test_hindi_returns_h(self, engine):
        assert engine.detect_language("नमस्ते दुनिया") == "h"

    def test_japanese_returns_j(self, engine):
        # Pure hiragana → j; mixed with CJK ideographs → z (checked first)
        assert engine.detect_language("こんにちは") == "j"

    def test_chinese_returns_z(self, engine):
        assert engine.detect_language("你好世界") == "z"

    def test_mixed_latin_and_hindi_returns_h(self, engine):
        # Hindi script takes priority (checked first in the dict)
        assert engine.detect_language("Hello नमस्ते") == "h"

    def test_empty_string_returns_a(self, engine):
        assert engine.detect_language("") == "a"

    def test_pure_punctuation_returns_a(self, engine):
        assert engine.detect_language("!!!???...") == "a"

    def test_auto_lang_code_triggers_detection(self, engine, monkeypatch):
        """When lang_code='auto', detect_language should be called."""
        detection_called = [False]
        original_detect = engine.detect_language

        def patched_detect(text):
            detection_called[0] = True
            return original_detect(text)

        monkeypatch.setattr(engine, "detect_language", patched_detect)

        # Mock the pipeline to avoid real synthesis
        engine._pipelines["h"] = FakePipeline(gen_fn=lambda t, v, s: iter([]))

        engine.synthesize("नमस्ते", voice="hf_alpha", lang_code="auto")
        assert detection_called[0]


# ---------------------------------------------------------------------------
# Voice mixing
# ---------------------------------------------------------------------------

class TestVoiceMixing:
    """Test voice_mix blends two voice outputs."""

    def test_mix_returns_blended_audio(self, engine, monkeypatch):
        """Mixing two voices at 0.5 ratio produces their average."""
        chunk_a = _make_chunk(0.3)
        chunk_b = _make_chunk(0.3) * 2  # Different amplitude

        # voice_mix calls synthesize twice — once per voice.
        # We need to return different chunks for each call.
        voice_chunks = {"af_heart": chunk_a, "af_bella": chunk_b}

        def gen(text, voice, speed):
            yield FakeResult("test", "t EH s t", [0], None, audio=voice_chunks.get(voice, chunk_a))

        engine._pipelines["a"] = FakePipeline(gen_fn=gen)

        result = engine.voice_mix("Test", "af_heart", "af_bella", mix_ratio=0.5, lang_code="a")
        assert result is not None
        min_len = min(len(chunk_a), len(chunk_b))
        expected = chunk_a[:min_len] * 0.5 + chunk_b[:min_len] * 0.5
        np.testing.assert_allclose(result, expected, atol=1e-6)

    def test_mix_empty_chunks_returns_none(self, engine, monkeypatch):
        """If either voice produces no audio, mix returns None."""
        engine._pipelines["a"] = FakePipeline(gen_fn=lambda t, v, s: iter([]))
        result = engine.voice_mix("Test", "af_heart", "af_bella", lang_code="a")
        assert result is None


# ---------------------------------------------------------------------------
# Best voice selection
# ---------------------------------------------------------------------------

class TestBestVoiceSelection:
    """Test select_best_voice quality-based selection."""

    def test_best_voice_for_english(self, engine):
        voice = engine.select_best_voice(lang_code="a")
        assert voice in ("af_heart", "af_bella", "af_nicole")  # top quality English

    def test_best_voice_prefers_gender(self, engine):
        voice = engine.select_best_voice(lang_code="a", gender="male")
        meta = engine.get_voice_info(voice)
        assert meta is not None
        assert meta["gender"] == "male"
        assert meta["lang"] == "a"

    def test_unknown_lang_returns_heart(self, engine):
        voice = engine.select_best_voice(lang_code="x")
        assert voice == "af_heart"

    def test_voice_info_returns_metadata(self, engine):
        info = engine.get_voice_info("af_heart")
        assert info is not None
        assert info["display"] == "Heart"
        assert info["gender"] == "female"

    def test_voice_info_unknown_returns_none(self, engine):
        assert engine.get_voice_info("nonexistent_voice") is None


# ---------------------------------------------------------------------------
# synthesize_from_tokens
# ---------------------------------------------------------------------------

class TestSynthesizeFromTokens:
    """Test that synthesize_from_tokens feeds tokens to the pipeline."""

    def test_returns_concatenated_audio(self, engine):
        chunks = [_make_chunk(0.2), _make_chunk(0.3)]

        def gen(text, voice, speed):
            for i, c in enumerate(chunks):
                yield FakeResult(f"tok_{i}", f"ph_{i}", [i], None, audio=c)

        engine._pipelines["a"] = FakePipeline(gen_fn=gen)

        result = engine.synthesize_from_tokens([10, 20, 30], voice="af_heart", lang_code="a")
        assert result is not None
        assert len(result) == sum(len(c) for c in chunks)

    def test_empty_tokens_returns_none(self, engine, monkeypatch):
        engine._pipelines["a"] = FakePipeline(gen_fn=lambda t, v, s: iter([]))
        result = engine.synthesize_from_tokens([], voice="af_heart", lang_code="a")
        assert result is None


# ---------------------------------------------------------------------------
# Voice metadata integrity
# ---------------------------------------------------------------------------

class TestVoiceMetadata:
    """Test that VOICE_METADATA and categories are consistent."""

    def test_all_voices_have_required_fields(self):
        from dreamtalk.voice.core.tts.kokoro_engine import VOICE_METADATA
        required = {"display", "gender", "lang", "quality", "category"}
        for vid, meta in VOICE_METADATA.items():
            missing = required - set(meta.keys())
            assert not missing, f"{vid} missing fields: {missing}"

    def test_emotion_map_voices_exist(self):
        from dreamtalk.voice.core.tts.kokoro_engine import EMOTION_VOICE_MAP, VOICE_METADATA
        for emotion, voice_id in EMOTION_VOICE_MAP.items():
            assert voice_id in VOICE_METADATA, f"Emotion '{emotion}' maps to unknown voice '{voice_id}'"

    def test_categories_are_populated(self):
        from dreamtalk.voice.core.tts.kokoro_engine import VOICE_CATEGORIES
        assert len(VOICE_CATEGORIES) > 0
        for cat, voices in VOICE_CATEGORIES.items():
            assert len(voices) > 0, f"Category '{cat}' is empty"

    def test_list_voices_returns_all(self, engine):
        from dreamtalk.voice.core.tts.kokoro_engine import VOICE_METADATA
        all_voices = engine.list_voices()
        assert len(all_voices) == len(VOICE_METADATA)
