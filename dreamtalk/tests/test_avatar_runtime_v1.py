import asyncio
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from dreamtalk.backend.services.avatar_runtime import AvatarProfileStore, AvatarRuntimeService
from dreamtalk.backend.services.image_identity import FaceIdentityService, FaceRestorationService
from dreamtalk.backend.services.multimodal_language import (
    SUPPORTED_LANGUAGES,
    analyze_vocal_emotion,
    detect_text_language,
)
from dreamtalk.pipeline.face_pipeline import FacePipeline
from dreamtalk.face.core.animation.liveportrait.utils.crop import crop_image


class LanguageDetectionTests(unittest.TestCase):
    def test_supports_all_scheduled_indian_languages_plus_english(self):
        self.assertEqual(len(SUPPORTED_LANGUAGES), 23)
        self.assertTrue({"brx", "doi", "ks", "kok", "mai", "mni", "ne", "sa", "sat", "sd", "ur"}.issubset(SUPPORTED_LANGUAGES))

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

    def test_detects_unique_scheduled_language_scripts(self):
        self.assertEqual(detect_text_language("ᱡᱚᱦᱟᱨ ᱟᱢ ᱪᱮᱫ ᱞᱮᱠᱟ").language, "sat")
        self.assertEqual(detect_text_language("ꯈꯨꯔꯨꯝꯖꯔꯤ").language, "mni")
        self.assertEqual(detect_text_language("آپ کیسے ہیں").language, "ur")


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

    def test_delete_changes_active_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = AvatarProfileStore(str(root / "media"), str(root / "profiles.json"))
            store.save({"id": "one", "created_at": "1"})
            store.save({"id": "two", "created_at": "2"})
            store.delete("two")
            self.assertEqual(store.get()["id"], "one")


class FaceSafetyTests(unittest.TestCase):
    def test_mediapipe_rotation_matrix_produces_bounded_head_pose(self):
        angle = np.radians(8.0)
        matrix = np.array([
            [np.cos(angle), -np.sin(angle), 0.0, 0.0],
            [np.sin(angle), np.cos(angle), 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])
        pose = FacePipeline._rotation_matrix_to_pose(matrix)
        self.assertAlmostEqual(pose["roll"], 8.0, places=1)
        self.assertAlmostEqual(pose["yaw"], 0.0, places=1)

    def test_liveportrait_crop_returns_inverse_affine_transform(self):
        image = np.zeros((300, 400, 3), dtype=np.uint8)
        landmarks = np.array([
            [160, 120], [240, 120], [200, 155], [175, 190], [225, 190],
        ], dtype=np.float32)
        result = crop_image(image, landmarks, dsize=256)
        recovered = result["pt_crop"] @ result["M_c2o"][:2, :2].T + result["M_c2o"][:2, 2]
        np.testing.assert_allclose(recovered, landmarks, atol=1e-3)
        self.assertEqual(result["img_crop"].shape, (256, 256, 3))

    def test_identity_comparison_uses_normalized_cosine_similarity(self):
        service = FaceIdentityService()
        service.model_name = "test-model"
        result = service.compare_embeddings(
            np.asarray([3.0, 0.0], dtype=np.float32),
            np.asarray([4.0, 0.0], dtype=np.float32),
        )
        self.assertTrue(result["verified"])
        self.assertAlmostEqual(result["similarity"], 1.0)

    def test_quality_gate_flags_small_blurry_image(self):
        import cv2

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "flat.png"
            cv2.imwrite(str(path), np.full((128, 128, 3), 20, dtype=np.uint8))
            result = FaceRestorationService.needs_restoration(str(path))
            self.assertTrue(result["required"])
            self.assertIn("low_resolution", result["reasons"])
            self.assertIn("blur", result["reasons"])
            self.assertIn("low_light", result["reasons"])


class RuntimeContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_signed_runtime_asset_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            media = root / "media"
            asset = media / "profile" / "asset.txt"
            asset.parent.mkdir(parents=True)
            asset.write_text("safe", encoding="utf-8")
            store = AvatarProfileStore(str(media), str(root / "profiles.json"))
            runtime = AvatarRuntimeService(store=store)
            url = runtime._runtime_url(str(asset))
            self.assertIn("signature=", url)
            with self.assertRaises(PermissionError):
                runtime.resolve_signed_asset("../asset.txt", 4102444800, "0" * 64)

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
