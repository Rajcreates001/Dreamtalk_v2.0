import asyncio
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from dreamtalk.backend.services.avatar_runtime import AvatarProfileStore, AvatarRuntimeService
from dreamtalk.backend.services.multimodal_language import (
    analyze_vocal_emotion,
    detect_text_language,
)


class LanguageDetectionTests(unittest.TestCase):
    def test_detects_distinct_indian_scripts(self):
        cases = {
            "வணக்கம் எப்படி இருக்கிறீர்கள்": "ta",
            "నమస్కారం మీరు ఎలా ఉన్నారు": "te",
            "ನಮಸ್ಕಾರ ನೀವು ಹೇಗಿದ್ದೀರಿ": "kn",
            "നമസ്കാരം സുഖമാണോ": "ml",
            "નમસ્તે તમે કેમ છો": "gu",
            "ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਤੁਸੀਂ ਕਿਵੇਂ ਹੋ": "pa",
            "ନମସ୍କାର ଆପଣ କେମିତି ଅଛନ୍ତି": "or",
        }
        for text, expected in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(detect_text_language(text).language, expected)

    def test_disambiguates_shared_scripts(self):
        self.assertEqual(detect_text_language("मैं खुश हूं और आप कैसे हैं").language, "hi")
        self.assertEqual(detect_text_language("मी आनंदी आहे आणि तुम्ही कसे आहात").language, "mr")
        self.assertEqual(detect_text_language("আপনি কেমন আছেন").language, "bn")
        self.assertEqual(detect_text_language("আপুনি কেনেকুৱা আছে আৰু ক'ত যাব").language, "as")

    def test_detects_romanized_language_with_context(self):
        result = detect_text_language("vanakkam enna eppadi irukku")
        self.assertEqual(result.language, "ta")
        self.assertGreater(result.confidence, 0.6)


class ProfileStoreTests(unittest.TestCase):
    def test_profile_round_trip_and_activation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = AvatarProfileStore(str(root / "media"), str(root / "profiles.json"))
            store.save({"id": "one", "name": "One", "created_at": "1"})
            store.save({"id": "two", "name": "Two", "created_at": "2"})
            self.assertEqual(store.get()["id"], "two")
            self.assertEqual(len(store.list()), 2)
            store.activate("one")
            self.assertEqual(store.get()["id"], "one")


class RuntimeContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_multilingual_lexicon_overrides_neutral_emotion(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = AvatarProfileStore(str(root / "media"), str(root / "profiles.json"))
            runtime = AvatarRuntimeService(store=store)
            result = await runtime._detect_text_emotion("आज मैं बहुत खुश हूँ!")
            self.assertEqual(result["primary_mood"], "happy")
            self.assertGreaterEqual(result["confidence"], 0.58)

    async def test_text_response_contract_contains_animation_and_language(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = AvatarProfileStore(str(root / "media"), str(root / "profiles.json"))
            runtime = AvatarRuntimeService(store=store)

            async def fake_response(message, language, profile, history, user_emotion):
                return "நான் நன்றாக இருக்கிறேன்.", {"model": "test", "fallback": False}

            async def fake_emotion(text):
                return {
                    "primary_mood": "happy",
                    "secondary_mood": None,
                    "valence": 0.7,
                    "arousal": 0.6,
                    "dominance": 0.5,
                    "intensity": "medium",
                    "intensity_score": 0.7,
                    "confidence": 0.8,
                    "source": "test",
                }

            runtime._generate_response = fake_response
            runtime._detect_text_emotion = fake_emotion
            result = await runtime.process_text(
                "வணக்கம் எப்படி இருக்கிறீர்கள்",
                synthesize=False,
                strict_clone=False,
            )
            self.assertEqual(result["language"]["response"], "ta")
            self.assertEqual(result["animation"]["emotion"], "happy")
            self.assertIn("arkit", result["animation"]["expression"])
            self.assertIn("vrm", result["animation"]["expression"])
            self.assertIsNone(result["audio"])

    async def test_vocal_emotion_returns_bounded_pad_values(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "voice.wav"
            sample_rate = 24000
            t = np.arange(sample_rate * 4, dtype=np.float32) / sample_rate
            envelope = np.clip(np.sin(np.pi * t / 4), 0, 1)
            audio = 0.18 * np.sin(2 * np.pi * 180 * t) * envelope
            sf.write(path, audio, sample_rate)
            result = await asyncio.to_thread(analyze_vocal_emotion, str(path))
            self.assertGreaterEqual(result.arousal, 0.0)
            self.assertLessEqual(result.arousal, 1.0)
            self.assertGreaterEqual(result.dominance, 0.0)
            self.assertLessEqual(result.dominance, 1.0)


if __name__ == "__main__":
    unittest.main()
