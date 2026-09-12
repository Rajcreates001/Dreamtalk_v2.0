"""Canonical end-to-end runtime for DreamTalk's human avatar.

This service owns the product path:
  profile media -> face assets + verified voice reference
  text/audio -> language + emotion -> LLM -> cloned TTS -> animation payload

Legacy research pipelines remain available, but this module is the single
contract used by the v1 avatar API and realtime WebSocket.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import hmac
import importlib.util
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from dreamtalk.backend.services.cloned_speech import (
    ClonedSpeechService,
    get_cloned_speech_service,
    prepare_reference_audio,
)
from dreamtalk.backend.services.multimodal_language import (
    SUPPORTED_LANGUAGES,
    LanguageDetection,
    MultilingualASR,
    VocalEmotion,
    analyze_vocal_emotion,
    detect_text_language,
    get_multilingual_asr,
    normalize_language,
)
from dreamtalk.backend.services.two_d_avatar import get_two_d_avatar_renderer
from dreamtalk.backend.services.image_identity import (
    get_face_identity_service,
    get_face_restoration_service,
)

logger = logging.getLogger("dreamtalk.avatar.runtime")


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_RUNTIME_ROOT = PROJECT_ROOT / "media" / "avatar_runtime"
DEFAULT_PROFILE_INDEX = PROJECT_ROOT / "results" / "avatar_runtime_profiles.json"


PREVIEW_TEXT = {
    "as": "নমস্কাৰ, এইটো মোৰ ক্লোন কৰা কণ্ঠস্বৰ।",
    "bn": "নমস্কার, এটি আমার ক্লোন করা কণ্ঠস্বর।",
    "en": "Hello, this is my cloned voice.",
    "gu": "નમસ્તે, આ મારો ક્લોન કરેલો અવાજ છે.",
    "hi": "नमस्ते, यह मेरी क्लोन की गई आवाज़ है।",
    "kn": "ನಮಸ್ಕಾರ, ಇದು ನನ್ನ ಕ್ಲೋನ್ ಮಾಡಿದ ಧ್ವನಿ.",
    "ml": "നമസ്കാരം, ഇത് എന്റെ ക്ലോൺ ചെയ്ത ശബ്ദമാണ്.",
    "mr": "नमस्कार, हा माझा क्लोन केलेला आवाज आहे.",
    "or": "ନମସ୍କାର, ଏହା ମୋର କ୍ଲୋନ୍ ହୋଇଥିବା ସ୍ୱର।",
    "pa": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ, ਇਹ ਮੇਰੀ ਕਲੋਨ ਕੀਤੀ ਆਵਾਜ਼ ਹੈ।",
    "ta": "வணக்கம், இது என்னுடைய குளோன் செய்யப்பட்ட குரல்.",
    "te": "నమస్కారం, ఇది నా క్లోన్ చేసిన స్వరం.",
}


FALLBACK_RESPONSES = {
    "as": "মই আপোনাৰ কথা বুজিছোঁ। অনুগ্ৰহ কৰি অলপ বেছিকৈ কওক।",
    "bn": "আমি আপনার কথা বুঝেছি। অনুগ্রহ করে আরেকটু বলুন।",
    "en": "I understand. Please tell me a little more.",
    "gu": "હું તમારી વાત સમજ્યો. કૃપા કરીને થોડું વધુ કહો.",
    "hi": "मैं आपकी बात समझ गया। कृपया थोड़ा और बताइए।",
    "kn": "ನಾನು ನಿಮ್ಮ ಮಾತನ್ನು ಅರ್ಥಮಾಡಿಕೊಂಡಿದ್ದೇನೆ. ದಯವಿಟ್ಟು ಇನ್ನಷ್ಟು ಹೇಳಿ.",
    "ml": "നിങ്ങൾ പറഞ്ഞത് എനിക്ക് മനസ്സിലായി. ദയവായി കുറച്ചുകൂടി പറയൂ.",
    "mr": "तुमचे म्हणणे मला समजले. कृपया थोडे अधिक सांगा.",
    "or": "ମୁଁ ଆପଣଙ୍କ କଥା ବୁଝିଛି। ଦୟାକରି ଆଉ କିଛି କୁହନ୍ତୁ।",
    "pa": "ਮੈਂ ਤੁਹਾਡੀ ਗੱਲ ਸਮਝ ਗਿਆ ਹਾਂ। ਕਿਰਪਾ ਕਰਕੇ ਹੋਰ ਦੱਸੋ।",
    "ta": "நீங்கள் சொன்னதை நான் புரிந்துகொண்டேன். இன்னும் கொஞ்சம் சொல்லுங்கள்.",
    "te": "మీరు చెప్పింది నాకు అర్థమైంది. దయచేసి ఇంకొంచెం చెప్పండి.",
}


EMOTION_ALIASES = {
    "anxious": "fearful",
    "annoyed": "angry",
    "anticipatory": "excited",
    "content": "calm",
    "defensive": "angry",
    "embarrassed": "sad",
    "furious": "angry",
    "grateful": "happy",
    "hopeful": "happy",
    "playful": "happy",
    "sarcastic": "confused",
    "trusting": "calm",
}


EMOTION_WORDS = {
    "happy": ("happy", "glad", "great", "love", "खुश", "आनंद", "சந்தோஷ", "மகிழ", "సంతోష", "ಖುಷ", "സന്തോഷ", "খুশি", "আনন্দ", "ખુશ", "આનંદ", "ਖੁਸ਼", "ଖୁସି"),
    "sad": ("sad", "upset", "cry", "sorry", "दुख", "उदास", "दुःखी", "சோகம்", "வருத்த", "బాధ", "ದುಃಖ", "ദുഃഖ", "মন খারাপ", "দুঃখ", "દુઃખી", "ਦੁਖੀ", "ଦୁଃଖ"),
    "angry": ("angry", "furious", "hate", "annoyed", "गुस्सा", "नाराज़", "राग", "கோப", "కోప", "ಕೋಪ", "ദേഷ്യം", "রাগ", "ગુસ્સો", "ਗੁੱਸਾ", "ରାଗ"),
    "fearful": ("afraid", "scared", "fear", "worried", "डर", "भय", "भीती", "பயம்", "భయం", "ಭಯ", "ഭയം", "ভয়", "ડર", "ਡਰ", "ଭୟ"),
    "surprised": ("surprised", "wow", "unexpected", "हैरान", "आश्चर्य", "ஆச்சரிய", "ఆశ్చర్య", "ಆಶ್ಚರ್ಯ", "അത്ഭുത", "অবাক", "આશ્ચર્ય", "ਹੈਰਾਨ", "ଆଶ୍ଚର୍ଯ୍ୟ"),
    "disgusted": ("disgust", "gross", "awful", "घिन", "அருவருப்பு", "అసహ్యం", "ಅಸಹ್ಯ", "വെറുപ്പ്", "ঘৃণা", "અણગમો", "ਘਿਣ", "ଘୃଣା"),
    "confused": ("confused", "don't understand", "समझ नहीं", "புரியவில்லை", "అర్థం కాలేదు", "ಅರ್ಥವಾಗಲಿಲ್ಲ", "മനസ്സിലായില്ല", "বুঝতে পারছি না", "સમજાતું નથી", "ਸਮਝ ਨਹੀਂ", "ବୁଝି ପାରୁନି"),
    "excited": ("excited", "amazing", "can't wait", "उत्साहित", "உற்சாக", "ఉత్సాహ", "ಉತ್ಸಾಹ", "ആവേശ", "উত্তেজিত", "ઉત્સાહિત", "ਉਤਸ਼ਾਹਿਤ", "ଉତ୍ସାହିତ"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(name: str, default: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]", "_", Path(name or default).name)
    return clean[:120] or default


def _json_safe(value: Any) -> Any:
    """Convert NumPy/OpenCV scalar values into JSON-native values."""
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    try:
        import numpy as np
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.generic):
            return value.item()
    except Exception:
        pass
    return value


class AvatarProfileStore:
    """Small atomic profile registry; media lives in persistent bind-mounted storage."""

    def __init__(self, runtime_root: Optional[str] = None, index_path: Optional[str] = None) -> None:
        self.runtime_root = Path(runtime_root or os.environ.get("AVATAR_RUNTIME_DIR", DEFAULT_RUNTIME_ROOT))
        self.index_path = Path(index_path or os.environ.get("AVATAR_PROFILE_INDEX", DEFAULT_PROFILE_INDEX))
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _read(self) -> dict[str, Any]:
        with self._lock:
            if not self.index_path.exists():
                return {"version": 1, "active_profile_id": None, "profiles": {}}
            try:
                data = json.loads(self.index_path.read_text(encoding="utf-8"))
                data.setdefault("version", 1)
                data.setdefault("active_profile_id", None)
                data.setdefault("profiles", {})
                return data
            except Exception as exc:
                logger.error("Profile index is invalid: %s", exc)
                return {"version": 1, "active_profile_id": None, "profiles": {}}

    def _write(self, data: dict[str, Any]) -> None:
        with self._lock:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.index_path.with_suffix(f".{uuid.uuid4().hex}.tmp")
            temp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(temp_path, self.index_path)

    def save(self, profile: dict[str, Any], activate: bool = True) -> dict[str, Any]:
        data = self._read()
        data["profiles"][profile["id"]] = copy.deepcopy(profile)
        if activate:
            data["active_profile_id"] = profile["id"]
        self._write(data)
        return copy.deepcopy(profile)

    def get(self, profile_id: Optional[str] = None) -> Optional[dict[str, Any]]:
        data = self._read()
        key = profile_id or data.get("active_profile_id")
        if not key:
            return None
        value = data["profiles"].get(key)
        return copy.deepcopy(value) if value else None

    def list(self) -> list[dict[str, Any]]:
        data = self._read()
        profiles = list(data["profiles"].values())
        profiles.sort(key=lambda item: item.get("updated_at", item.get("created_at", "")), reverse=True)
        return copy.deepcopy(profiles)

    def activate(self, profile_id: str) -> dict[str, Any]:
        data = self._read()
        if profile_id not in data["profiles"]:
            raise KeyError(profile_id)
        data["active_profile_id"] = profile_id
        data["profiles"][profile_id]["updated_at"] = utc_now()
        self._write(data)
        return copy.deepcopy(data["profiles"][profile_id])

    def delete(self, profile_id: str) -> dict[str, Any]:
        """Remove one profile record and return it for controlled media cleanup."""
        data = self._read()
        profile = data["profiles"].pop(profile_id, None)
        if profile is None:
            raise KeyError(profile_id)
        if data.get("active_profile_id") == profile_id:
            remaining = list(data["profiles"].values())
            remaining.sort(
                key=lambda item: item.get("updated_at", item.get("created_at", "")),
                reverse=True,
            )
            data["active_profile_id"] = remaining[0]["id"] if remaining else None
        self._write(data)
        return copy.deepcopy(profile)


class AvatarRuntimeService:
    def __init__(
        self,
        store: Optional[AvatarProfileStore] = None,
        speech: Optional[ClonedSpeechService] = None,
        asr: Optional[MultilingualASR] = None,
    ) -> None:
        self.store = store or AvatarProfileStore()
        self.speech = speech or get_cloned_speech_service()
        self.asr = asr or get_multilingual_asr()
        self.two_d = get_two_d_avatar_renderer()
        self.restoration = get_face_restoration_service()
        self.identity = get_face_identity_service()

    def _asset_signature(self, relative_path: str, expires: int) -> str:
        secret = os.environ.get(
            "AVATAR_ASSET_SIGNING_SECRET",
            os.environ.get("JWT_SECRET", "dreamtalk-secret-change-in-production"),
        )
        payload = f"{relative_path}:{expires}".encode("utf-8")
        return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    def _runtime_url(self, path: Optional[str]) -> Optional[str]:
        if not path:
            return None
        try:
            relative = Path(path).resolve().relative_to(self.store.runtime_root.resolve())
            relative_path = relative.as_posix()
            ttl = max(60, int(os.environ.get("AVATAR_ASSET_URL_TTL_SECONDS", "3600")))
            expires = int(time.time()) + ttl
            signature = self._asset_signature(relative_path, expires)
            return (
                f"/api/v1/avatar/assets/{relative_path}"
                f"?expires={expires}&signature={signature}"
            )
        except Exception:
            return None

    def resolve_signed_asset(self, relative_path: str, expires: int, signature: str) -> Path:
        if expires < int(time.time()):
            raise PermissionError("Avatar asset URL has expired")
        clean = Path(relative_path.replace("\\", "/"))
        if clean.is_absolute() or ".." in clean.parts:
            raise PermissionError("Invalid avatar asset path")
        normalized = clean.as_posix()
        expected = self._asset_signature(normalized, expires)
        if not hmac.compare_digest(expected, signature):
            raise PermissionError("Invalid avatar asset signature")
        target = (self.store.runtime_root / clean).resolve()
        try:
            target.relative_to(self.store.runtime_root.resolve())
        except ValueError as exc:
            raise PermissionError("Invalid avatar asset path") from exc
        if not target.is_file():
            raise FileNotFoundError(target)
        return target

    def public_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        value = copy.deepcopy(profile)
        voice = value.get("voice") or {}
        reference_audio_path = voice.pop("reference_audio_path", None)
        if reference_audio_path:
            voice["reference_audio_url"] = self._runtime_url(reference_audio_path)
        sample_language = normalize_language(voice.get("sample_language"))
        voice["sample_language_supported_by_clone"] = sample_language in SUPPORTED_LANGUAGES
        if isinstance(voice.get("quality"), dict):
            voice["quality"].pop("path", None)
        if isinstance(voice.get("validation"), dict):
            voice["validation"].pop("path", None)
            voice["validation"].pop("service_url", None)
        appearance = value.get("appearance") or {}
        source_paths = appearance.pop("source_image_paths", None) or []
        primary_path = appearance.pop("primary_image_path", None)
        if primary_path or source_paths:
            appearance["primary_image_url"] = self._runtime_url(primary_path or source_paths[0])
        analysis = appearance.get("analysis") or {}
        analysis.pop("face_embedding", None)
        analysis.pop("identity_embedding", None)
        analysis.pop("mesh_3d_path", None)
        analysis.pop("mesh_glb_path", None)
        analysis.pop("texture_path", None)
        render_modes = appearance.setdefault("render_modes", [])
        for mode in ("talkinghead_2d", "realtime_3d"):
            if mode not in render_modes:
                render_modes.append(mode)
        mesh_path = appearance.pop("mesh_path", None) or analysis.get("mesh_3d_path")
        glb_path = appearance.pop("glb_path", None)
        texture_path = appearance.pop("texture_path", None) or analysis.get("texture_path")
        if mesh_path:
            appearance["mesh_url"] = self._runtime_url(mesh_path)
        if glb_path:
            appearance["glb_url"] = self._runtime_url(glb_path)
        if texture_path:
            appearance["texture_url"] = self._runtime_url(texture_path)
        if appearance.get("mesh_url") and appearance.get("texture_url"):
            analysis["texture_mapped"] = True
        # Report the morph targets actually baked into the GLB. Claiming
        # blendshape support the mesh does not have makes the frontend render
        # a head it cannot animate, so this is derived, never hardcoded.
        blendshape_names = list(
            appearance.pop("blendshape_names", None)
            or analysis.get("mesh_blendshape_names")
            or []
        )
        appearance["blendshape_names"] = blendshape_names
        has_shapes = bool(appearance.get("glb_url")) and bool(blendshape_names)
        appearance["capabilities"] = {
            "talkinghead_2d": True,
            "lip_sync_video": True,
            "textured_3d_mesh": bool(appearance.get("mesh_url") and appearance.get("texture_url")),
            "browser_glb": bool(appearance.get("glb_url")),
            "arkit_blendshapes": has_shapes,
            "vrm_expressions": has_shapes,
            "visemes": [n for n in blendshape_names if n in ("aa", "ih", "ou", "ee", "oh")],
            "animation_driver": (
                "glb_morph_targets" if has_shapes else "timestamped_external_blendshapes"
            ),
        }
        return value

    async def create_profile(
        self,
        name: str,
        voice_sample_path: str,
        face_image_paths: list[str],
        reference_text: str = "",
        language: str = "auto",
        user_id: str = "default",
        validate_clone: bool = True,
        consent: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        if not face_image_paths:
            raise ValueError("At least one clear face image is required")
        if not consent or not consent.get("confirmed"):
            raise ValueError("Explicit consent is required to clone a person's face and voice")
        profile_id = str(uuid.uuid4())
        profile_dir = self.store.runtime_root / profile_id
        voice_dir = profile_dir / "voice"
        appearance_dir = profile_dir / "appearance"
        source_dir = appearance_dir / "source"
        restored_dir = appearance_dir / "restored"
        generated_dir = appearance_dir / "generated"
        for directory in (voice_dir, source_dir, restored_dir, generated_dir):
            directory.mkdir(parents=True, exist_ok=True)

        voice_path = voice_dir / "reference.wav"
        voice_quality = await asyncio.to_thread(prepare_reference_audio, voice_sample_path, str(voice_path))

        transcription = None
        requested_language = None if language == "auto" else normalize_language(language)
        if not reference_text.strip():
            transcription = await self.asr.transcribe(str(voice_path), requested_language)
            reference_text = transcription.text
            sample_language = transcription.language
        else:
            detection = detect_text_language(reference_text, preferred=requested_language)
            sample_language = requested_language or detection.language
        if not reference_text.strip():
            raise ValueError("Could not determine the reference transcript; provide reference_text explicitly")

        copied_images: list[str] = []
        for index, source_name in enumerate(face_image_paths):
            source = Path(source_name)
            if not source.exists():
                continue
            suffix = source.suffix.lower() if source.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"
            destination = source_dir / f"face_{index + 1}{suffix}"
            shutil.copy2(source, destination)
            copied_images.append(str(destination))
        if not copied_images:
            raise ValueError("No valid face images could be stored")

        quality_assessment = await asyncio.to_thread(
            self.restoration.needs_restoration, copied_images[0]
        )
        canonical_images = list(copied_images)
        restoration_result: dict[str, Any] = {
            "applied": False,
            "quality_assessment": quality_assessment,
            "service": self.restoration.status(),
        }
        if quality_assessment["required"]:
            if self.restoration.status()["ready"]:
                restored_path = restored_dir / "primary.png"
                restored = await asyncio.to_thread(
                    self.restoration.restore, copied_images[0], str(restored_path)
                )
                restoration_result.update({"applied": True, **restored})
                canonical_images[0] = str(restored_path)
            else:
                restoration_result["warning"] = (
                    "Input quality needs restoration, but the GFPGAN service is unavailable"
                )

        identity_result: dict[str, Any]
        try:
            if restoration_result["applied"]:
                identity_result = await asyncio.to_thread(
                    self.identity.verify, copied_images[0], canonical_images[0]
                )
                identity_result["gate"] = "restoration_identity_preservation"
            else:
                embedding = await asyncio.to_thread(self.identity.embed, canonical_images[0])
                identity_result = {
                    "verified": True,
                    "gate": "single_reference_enrollment",
                    "model": self.identity.model_name,
                    "embedding_dim": int(embedding.size),
                }
            for candidate_path in copied_images[1:]:
                comparison = await asyncio.to_thread(
                    self.identity.verify, copied_images[0], candidate_path
                )
                if not comparison["verified"]:
                    raise ValueError("The supplied face images do not appear to show the same person")
            if not identity_result["verified"]:
                raise ValueError("Face restoration changed the person's identity beyond the safety threshold")
        except ValueError:
            raise
        except Exception as exc:
            identity_result = {
                "verified": False,
                "gate": "unavailable",
                "error": str(exc),
                "service": self.identity.status(),
            }
            if os.environ.get("AVATAR_REQUIRE_IDENTITY_GATE", "true").lower() == "true":
                raise RuntimeError(f"Real face identity verification is required: {exc}") from exc

        face_analysis = await asyncio.to_thread(
            self._run_face_pipeline,
            canonical_images,
            str(generated_dir),
        )
        if not face_analysis.get("face_detected"):
            raise ValueError(f"No face was detected in the supplied image: {face_analysis.get('error') or 'unknown error'}")

        created_at = utc_now()
        profile = {
            "id": profile_id,
            "user_id": user_id,
            "name": name.strip() or "DreamTalk Avatar",
            "status": "processing",
            "created_at": created_at,
            "updated_at": created_at,
            "consent": {
                "confirmed": True,
                "subject_name": str(consent.get("subject_name") or name).strip(),
                "scopes": list(consent.get("scopes") or ["face", "voice", "animation"]),
                "version": str(consent.get("version") or "1.0"),
                "recorded_at": created_at,
            },
            "voice": {
                "engine": "auto-indic-mio-then-indicf5",
                "ready": False,
                "sample_language": sample_language,
                "sample_language_supported_by_clone": sample_language in SUPPORTED_LANGUAGES,
                "clone_quality_warnings": [],
                "reference_text": reference_text.strip(),
                "reference_audio_path": str(voice_path),
                "reference_audio_url": self._runtime_url(str(voice_path)),
                "quality": voice_quality,
                "transcription": transcription.to_dict() if transcription else None,
                "preview_audio_url": None,
            },
            "appearance": {
                "ready": bool(face_analysis.get("face_detected")),
                "source_image_paths": copied_images,
                "primary_image_path": canonical_images[0],
                "primary_image_url": self._runtime_url(canonical_images[0]),
                "mesh_path": face_analysis.get("mesh_3d_path"),
                "glb_path": face_analysis.get("mesh_glb_path"),
                "blendshape_names": face_analysis.get("mesh_blendshape_names") or [],
                "texture_path": face_analysis.get("texture_path"),
                "mesh_url": self._runtime_url(face_analysis.get("mesh_3d_path")),
                "texture_url": self._runtime_url(face_analysis.get("texture_path")),
                "mesh_format": face_analysis.get("mesh_format", "obj"),
                "analysis": face_analysis,
                "restoration": restoration_result,
                "identity_verification": identity_result,
                "render_modes": ["talkinghead_2d", "realtime_3d", "liveportrait_video"],
            },
            "preferences": {"language": "auto", "strict_clone": True},
        }
        self.store.save(profile, activate=True)

        if validate_clone:
            # Validate in a language the clone engine actually covers. IndicF5
            # handles 11 Indic languages but not English, so validating in the
            # sample's own language marked every English-sample profile
            # "degraded" even though cloning works perfectly in the covered
            # languages. The profile is ready; the coverage gap is a warning.
            health = await self.speech.discover()
            supported = set((health.get("supported_languages") or {}).keys())
            if sample_language in supported or not supported:
                validation_language = sample_language
            else:
                validation_language = "hi" if "hi" in supported else sorted(supported)[0]
            try:
                preview = await self.speech.synthesize_clone(
                    text=PREVIEW_TEXT.get(validation_language, PREVIEW_TEXT["en"]),
                    reference_audio=str(voice_path),
                    reference_text=reference_text.strip(),
                    language=validation_language,
                    emotion="happy",
                    reference_language=sample_language,
                )
                profile["voice"]["ready"] = True
                profile["voice"]["validated_language"] = validation_language
                profile["voice"]["preview_audio_url"] = preview.audio_url
                profile["voice"]["validation"] = preview.to_dict()
                if validation_language != sample_language:
                    profile["voice"]["clone_quality_warnings"].append(
                        f"Voice cloned and verified in '{validation_language}'. The sample "
                        f"language '{sample_language}' is outside the clone engine's coverage, "
                        f"so replies in it use a clearly-labelled stand-in voice."
                    )
            except Exception as exc:
                profile["voice"]["validation_error"] = str(exc)
                logger.warning("Clone validation failed for profile %s: %s", profile_id, exc)
        else:
            health = await self.speech.discover()
            profile["voice"]["ready"] = bool(health.get("available"))
            profile["voice"]["validation"] = {"skipped": True, "service": health}

        profile["status"] = "ready" if profile["voice"]["ready"] and profile["appearance"]["ready"] else "degraded"
        profile["updated_at"] = utc_now()
        self.store.save(profile, activate=True)
        return self.public_profile(profile)

    def delete_profile(self, profile_id: str, user_id: str) -> dict[str, Any]:
        profile = self.store.get(profile_id)
        if not profile:
            raise KeyError(profile_id)
        if str(profile.get("user_id")) != str(user_id):
            raise PermissionError("Avatar profile belongs to another user")
        removed = self.store.delete(profile_id)
        profile_dir = (self.store.runtime_root / profile_id).resolve()
        profile_dir.relative_to(self.store.runtime_root.resolve())
        if profile_dir.is_dir():
            shutil.rmtree(profile_dir)
        return {"deleted": True, "profile_id": removed["id"]}

    @staticmethod
    def _run_face_pipeline(image_paths: list[str], output_dir: str) -> dict[str, Any]:
        from dreamtalk.pipeline.face_pipeline import FacePipeline

        result = asyncio.run(FacePipeline().run(image_paths, output_dir=output_dir, enable_sr=False))
        return _json_safe(result.model_dump())

    async def _detect_text_emotion(self, text: str) -> dict[str, Any]:
        lowered = text.lower()
        lexical_scores = {
            emotion: sum(token in lowered for token in tokens)
            for emotion, tokens in EMOTION_WORDS.items()
        }
        lexical_emotion, lexical_score = max(lexical_scores.items(), key=lambda item: item[1])
        try:
            from dreamtalk.pipeline.brain_pipeline import BrainPipeline

            result = await BrainPipeline().detect_emotion(text)
            if result:
                payload = {
                    "primary_mood": result.primary_mood.value,
                    "secondary_mood": result.secondary_mood.value if result.secondary_mood else None,
                    "valence": float(result.valence),
                    "arousal": float(result.arousal),
                    "dominance": float(result.dominance),
                    "intensity": result.intensity,
                    "intensity_score": float(result.intensity_score),
                    "confidence": float(result.confidence),
                    "source": "text_brain_pipeline",
                }
                if lexical_score and (
                    payload["primary_mood"] == "neutral" or payload["confidence"] < 0.55
                ):
                    payload["primary_mood"] = lexical_emotion
                    payload["confidence"] = max(payload["confidence"], min(0.9, 0.58 + lexical_score * 0.12))
                    payload["intensity_score"] = max(payload["intensity_score"], min(1.0, 0.5 + lexical_score * 0.18))
                    payload["source"] = "brain_multilingual_lexicon_fusion"
                return payload
        except Exception as exc:
            logger.warning("Brain emotion detection unavailable: %s", exc)

        emotion, score = lexical_emotion, lexical_score
        if score == 0:
            emotion = "neutral"
        negative = emotion in {"sad", "angry", "fearful", "disgusted"}
        arousal = 0.75 if emotion in {"angry", "excited", "surprised"} else 0.3 if emotion in {"sad", "calm"} else 0.5
        return {
            "primary_mood": emotion,
            "secondary_mood": None,
            "valence": -0.65 if negative else 0.65 if emotion in {"happy", "excited"} else 0.0,
            "arousal": arousal,
            "dominance": 0.7 if emotion == "angry" else 0.5,
            "intensity": "high" if score > 1 else "medium" if score else "low",
            "intensity_score": min(1.0, 0.35 + score * 0.25),
            "confidence": min(0.85, 0.4 + score * 0.18),
            "source": "multilingual_lexicon",
        }

    @staticmethod
    def _fuse_emotion(text_emotion: dict[str, Any], vocal: Optional[VocalEmotion]) -> dict[str, Any]:
        result = copy.deepcopy(text_emotion)
        if not vocal:
            result["vocal"] = None
            return result
        text_confidence = float(result.get("confidence", 0.0))
        text_label = result.get("primary_mood", "neutral")
        if text_label == "neutral" and vocal.emotion != "neutral" and vocal.confidence >= 0.55:
            result["primary_mood"] = vocal.emotion
            result["confidence"] = vocal.confidence
        text_weight = 0.72 if text_confidence >= 0.55 and text_label != "neutral" else 0.45
        vocal_weight = 1.0 - text_weight
        for field in ("valence", "arousal", "dominance"):
            result[field] = round(
                float(result.get(field, 0.0)) * text_weight + float(getattr(vocal, field)) * vocal_weight,
                4,
            )
        result["source"] = "text_vocal_fusion"
        result["vocal"] = vocal.to_dict()
        return result

    async def _generate_response(
        self,
        message: str,
        language: str,
        profile: Optional[dict[str, Any]],
        history: Optional[list[dict[str, str]]],
        user_emotion: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        language_name = SUPPORTED_LANGUAGES.get(language, "English")
        avatar_name = (profile or {}).get("name", "DreamTalk Avatar")
        system_prompt = (
            f"You are {avatar_name}, a warm, natural human-like digital avatar. "
            f"Reply in {language_name}, matching the user's script and conversational style. "
            "If the user code-switches, respond naturally in the dominant language and retain familiar English terms. "
            "Be emotionally aware and answer in one or two short spoken sentences (maximum 35 words). "
            "Never mention internal models or pipelines. "
            f"The user's detected emotion is {user_emotion.get('primary_mood', 'neutral')}."
        )
        messages: list[dict[str, str]] = []
        for item in (history or [])[-12:]:
            role = item.get("role")
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content[:4000]})
        messages.append({"role": "user", "content": message})

        try:
            from dreamtalk.backend.services.llm_service import chat_completion

            result = await chat_completion(
                messages=messages,
                temperature=0.65,
                max_tokens=int(os.environ.get("AVATAR_LLM_MAX_TOKENS", "120")),
                system_prompt=system_prompt,
            )
            response = str(result.get("response", "")).strip()
            if response:
                return response, {"model": result.get("model", "unknown"), "usage": result.get("usage", {}), "fallback": False}
        except Exception as exc:
            logger.warning("Primary avatar LLM failed: %s", exc)
            llm_error = str(exc)
        else:
            llm_error = "empty LLM response"

        try:
            from dreamtalk.pipeline.brain_pipeline import BrainPipeline

            brain = BrainPipeline()
            emotion_result = await brain.detect_emotion(message)
            decision = await brain.make_decision(
                text=message,
                role="normal_user",
                emotion=emotion_result,
                model_name=os.environ.get("LLM_FALLBACK_MODEL", "deepseek-r1:7b"),
            )
            if decision.response_text:
                return decision.response_text, {
                    "model": decision.model_name,
                    "fallback": True,
                    "reason": llm_error,
                    "brain_confidence": decision.confidence,
                }
        except Exception as exc:
            logger.warning("Brain response fallback failed: %s", exc)

        return FALLBACK_RESPONSES.get(language, FALLBACK_RESPONSES["en"]), {
            "model": "localized_safe_fallback",
            "fallback": True,
            "reason": llm_error,
        }

    async def _ensure_response_language(self, text: str, target_language: str) -> tuple[str, bool]:
        detection = detect_text_language(text, preferred=target_language)
        if detection.language == target_language or detection.confidence < 0.6:
            return text, False
        try:
            from dreamtalk.voice.core.translation.language_router import get_language_router

            translated = await get_language_router().translate(
                text,
                target_lang=target_language,
                source_lang=detection.language,
            )
            candidate = getattr(translated, "translated_text", "") or getattr(translated, "text", "")
            if candidate and candidate.strip() != text.strip():
                return candidate.strip(), True
        except Exception as exc:
            logger.warning("Response language correction failed: %s", exc)
        return text, False

    @staticmethod
    def _display_emotion(label: str) -> str:
        return EMOTION_ALIASES.get(label, label if label in {
            "neutral", "calm", "happy", "excited", "sad", "angry", "surprised",
            "fearful", "disgusted", "loving", "frustrated", "confused",
        } else "neutral")

    def _animation_payload(self, emotion: dict[str, Any], lipsync: Optional[dict[str, Any]]) -> dict[str, Any]:
        from dreamtalk.pipeline.emotion_animation import EmotionAnimationMapper

        display = self._display_emotion(str(emotion.get("primary_mood", "neutral")))
        mapper = EmotionAnimationMapper(smoothing_factor=1.0)
        expression = mapper.map_emotion(
            primary_mood=display,
            valence=float(emotion.get("valence", 0.0)),
            arousal=float(emotion.get("arousal", 0.5)),
            dominance=float(emotion.get("dominance", 0.5)),
            intensity_score=float(emotion.get("intensity_score", 0.6)),
            secondary_mood=self._display_emotion(emotion["secondary_mood"]) if emotion.get("secondary_mood") else None,
        ).to_dict()
        expression["arkit"] = self._flatten_arkit(expression)
        expression["vrm"] = {
            "happy": 1.0 if display in {"happy", "excited", "loving"} else 0.0,
            "angry": 1.0 if display in {"angry", "frustrated"} else 0.0,
            "sad": 1.0 if display == "sad" else 0.0,
            "surprised": 1.0 if display in {"surprised", "fearful"} else 0.0,
            "relaxed": 1.0 if display == "calm" else 0.0,
        }
        return {
            "emotion": display,
            "transition_ms": 220,
            "hold_ms": 900,
            "expression": expression,
            "lipsync": lipsync or {"duration": 0.0, "keyframes": []},
            "idle": {
                "blink_interval_ms": [2400, 5200],
                "blink_duration_ms": 140,
                "gaze_saccade_interval_ms": [1600, 3600],
                "head_micro_motion": 0.035,
                "breathing_cycle_ms": 4200,
            },
        }

    @staticmethod
    def _flatten_arkit(expression: dict[str, Any]) -> dict[str, float]:
        brows = expression.get("eyebrows", {})
        eyes = expression.get("eyes", {})
        mouth = expression.get("mouth", {})
        cheeks = expression.get("cheeks", {})
        return {
            "browInnerUp": brows.get("brow_inner_up", 0.0),
            "browOuterUpLeft": brows.get("brow_outer_up", 0.0),
            "browOuterUpRight": brows.get("brow_outer_up", 0.0),
            "browDownLeft": brows.get("brow_lower", 0.0),
            "browDownRight": brows.get("brow_lower", 0.0),
            "eyeSquintLeft": eyes.get("eye_squint_left", 0.0),
            "eyeSquintRight": eyes.get("eye_squint_right", 0.0),
            "eyeWideLeft": eyes.get("eye_wide_left", 0.0),
            "eyeWideRight": eyes.get("eye_wide_right", 0.0),
            "mouthSmileLeft": mouth.get("mouth_smile_left", 0.0),
            "mouthSmileRight": mouth.get("mouth_smile_right", 0.0),
            "mouthFrownLeft": mouth.get("mouth_frown_left", 0.0),
            "mouthFrownRight": mouth.get("mouth_frown_right", 0.0),
            "mouthPucker": mouth.get("mouth_pucker", 0.0),
            "mouthFunnel": mouth.get("mouth_funnel", 0.0),
            "mouthStretchLeft": mouth.get("mouth_stretch_left", 0.0),
            "mouthStretchRight": mouth.get("mouth_stretch_right", 0.0),
            "cheekSquintLeft": cheeks.get("cheek_squint_left", 0.0),
            "cheekSquintRight": cheeks.get("cheek_squint_right", 0.0),
            "jawOpen": expression.get("jaw_open", 0.0),
        }

    async def process_text(
        self,
        message: str,
        profile_id: Optional[str] = None,
        language: str = "auto",
        history: Optional[list[dict[str, str]]] = None,
        synthesize: bool = True,
        strict_clone: bool = True,
        vocal_emotion: Optional[VocalEmotion] = None,
        render_video: bool = False,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        message = (message or "").strip()
        if not message:
            raise ValueError("Message is empty")
        profile = self.store.get(profile_id)
        requested = None if language == "auto" else normalize_language(language)
        preferred = requested or ((profile or {}).get("preferences") or {}).get("language")
        detection = LanguageDetection(requested, 1.0, "explicit", "unknown", {requested: 1.0}) if requested else detect_text_language(message, preferred=preferred)
        target_language = detection.language

        text_emotion = await self._detect_text_emotion(message)
        user_emotion = self._fuse_emotion(text_emotion, vocal_emotion)
        response_text, brain = await self._generate_response(message, target_language, profile, history, user_emotion)
        response_text, translated = await self._ensure_response_language(response_text, target_language)
        response_emotion = await self._detect_text_emotion(response_text)

        speech_result = None
        lipsync = None
        if synthesize:
            speech_result = await self.speech.synthesize(
                text=response_text,
                language=target_language,
                emotion=self._display_emotion(response_emotion.get("primary_mood", "neutral")),
                profile=profile,
                strict_clone=strict_clone,
            )
            lipsync = await asyncio.to_thread(self._build_lipsync, speech_result.path, response_emotion, response_text)

        animation = self._animation_payload(response_emotion, lipsync)
        video = None
        if render_video and profile and speech_result:
            video = await asyncio.to_thread(
                self._render_video,
                profile,
                speech_result.path,
                animation["emotion"],
            )

        audio_payload = speech_result.to_dict() if speech_result else None
        if audio_payload:
            audio_payload.pop("path", None)
            audio_payload.pop("service_url", None)

        return {
            "response": response_text,
            "text": response_text,
            "profile_id": profile.get("id") if profile else None,
            "language": {
                "input": detection.to_dict(),
                "response": target_language,
                "name": SUPPORTED_LANGUAGES.get(target_language, target_language),
                "response_was_translated": translated,
            },
            "user_emotion": user_emotion,
            "response_emotion": response_emotion,
            "emotion": animation["emotion"],
            "audio": audio_payload,
            "audio_url": speech_result.audio_url if speech_result else None,
            "lipsync": (lipsync or {}).get("keyframes", []),
            "lipsync_duration": (lipsync or {}).get("duration", 0.0),
            "animation": animation,
            "video": video,
            "brain": brain,
            "processing_ms": round((time.perf_counter() - started) * 1000, 2),
        }

    @staticmethod
    def _build_lipsync(audio_path: str, emotion: dict[str, Any], text: str) -> dict[str, Any]:
        from dreamtalk.pipeline.lipsync_pipeline import get_lipsync_pipeline

        result = get_lipsync_pipeline(fps=30.0).extract_from_audio(audio_path, emotion=emotion, text=text)
        return result.to_dict()

    async def process_audio(
        self,
        audio_path: str,
        profile_id: Optional[str] = None,
        language: str = "auto",
        history: Optional[list[dict[str, str]]] = None,
        synthesize: bool = True,
        strict_clone: bool = True,
        render_video: bool = False,
    ) -> dict[str, Any]:
        hint = None if language == "auto" else normalize_language(language)
        transcription, vocal = await asyncio.gather(
            self.asr.transcribe(audio_path, hint),
            asyncio.to_thread(analyze_vocal_emotion, audio_path),
        )
        if not transcription.text.strip():
            raise ValueError("No speech was detected in the audio")
        result = await self.process_text(
            message=transcription.text,
            profile_id=profile_id,
            language=hint or transcription.language,
            history=history,
            synthesize=synthesize,
            strict_clone=strict_clone,
            vocal_emotion=vocal,
            render_video=render_video,
        )
        result["transcription"] = transcription.to_dict()
        return result

    def _render_video(
        self,
        profile: dict[str, Any],
        audio_path: str,
        emotion: str,
        engine: str = "auto",
    ) -> dict[str, Any]:
        source_images = (profile.get("appearance") or {}).get("source_image_paths") or []
        if not source_images:
            return {"status": "unavailable", "reason": "Profile has no source image"}
        output_dir = self.store.runtime_root / profile["id"] / "responses"
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = self.two_d.render(
                source_image=source_images[0],
                audio_path=audio_path,
                output_dir=str(output_dir),
                emotion=emotion,
                engine=engine,
            )
            path = result.pop("path", None)
            result["url"] = self._runtime_url(path)
            result["render_mode"] = "talkinghead_2d"
            return result
        except Exception as exc:
            logger.exception("2D avatar video rendering failed")
            return {"status": "failed", "reason": str(exc)}

    async def render_2d(
        self,
        profile_id: str,
        audio_path: str,
        emotion: str = "neutral",
        engine: str = "auto",
    ) -> dict[str, Any]:
        profile = self.store.get(profile_id)
        if not profile:
            raise KeyError(profile_id)
        return await asyncio.to_thread(self._render_video, profile, audio_path, emotion, engine)

    async def status(self) -> dict[str, Any]:
        speech = await self.speech.discover(force=True)
        hardware: dict[str, Any] = {
            "gpu_required": os.environ.get("AVATAR_REQUIRE_GPU", "false").lower() == "true",
            "cuda_available": False,
            "device_count": 0,
            "devices": [],
        }
        try:
            import torch

            hardware["torch_version"] = torch.__version__
            hardware["torch_cuda_build"] = torch.version.cuda
            hardware["cuda_available"] = bool(torch.cuda.is_available())
            hardware["device_count"] = int(torch.cuda.device_count())
            for index in range(torch.cuda.device_count()):
                properties = torch.cuda.get_device_properties(index)
                hardware["devices"].append({
                    "index": index,
                    "name": properties.name,
                    "total_vram_mb": round(properties.total_memory / (1024 * 1024), 1),
                    "allocated_vram_mb": round(torch.cuda.memory_allocated(index) / (1024 * 1024), 1),
                    "reserved_vram_mb": round(torch.cuda.memory_reserved(index) / (1024 * 1024), 1),
                    "capability": list(torch.cuda.get_device_capability(index)),
                })
        except Exception as exc:
            hardware["error"] = str(exc)
        liveportrait_dir = PROJECT_ROOT / "weights" / "liveportrait"
        liveportrait_required = [
            "appearance_feature_extractor.pth",
            "motion_extractor.pth",
            "spade_generator.pth",
            "warping_module.pth",
            "landmark.onnx",
            "stitching_retargeting_module.pth",
        ]
        liveportrait_weights = {
            name: (liveportrait_dir / name).exists() for name in liveportrait_required
        }
        liveportrait_validation_path = DEFAULT_RUNTIME_ROOT / "validation" / "liveportrait.json"
        liveportrait_validation = None
        if liveportrait_validation_path.exists():
            try:
                liveportrait_validation = json.loads(liveportrait_validation_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
        liveportrait = {
            "ready": all(liveportrait_weights.values()) and hardware["cuda_available"],
            "weights_ready": all(liveportrait_weights.values()),
            "inference_validated": liveportrait_validation is not None,
            "last_validation": liveportrait_validation,
            "weights": liveportrait_weights,
            "loading": "lazy",
        }
        face_weights = {
            "flame": (PROJECT_ROOT / "weights" / "flame" / "FLAME2020" / "generic_model.pkl").exists()
                or any((PROJECT_ROOT / "weights" / "flame").glob("*.pkl")),
            "mediapipe": importlib.util.find_spec("mediapipe") is not None,
        }
        asr_available = importlib.util.find_spec("faster_whisper") is not None or importlib.util.find_spec("transformers") is not None
        profiles = self.store.list()
        ready_profiles = sum(1 for item in profiles if item.get("status") == "ready")
        gpu_ok = hardware["cuda_available"] or not hardware["gpu_required"]
        return {
            "status": "ready" if speech.get("available") and asr_available and all(face_weights.values()) and gpu_ok else "degraded",
            "hardware": hardware,
            "voice_cloning": speech,
            "asr": {"available": asr_available, "loaded_engine": self.asr.engine},
            "appearance": face_weights,
            "image_restoration": self.restoration.status(),
            "identity_verification": self.identity.status(),
            "liveportrait": liveportrait,
            "avatar_2d": self.two_d.status(),
            "profiles": {"total": len(profiles), "ready": ready_profiles},
            "supported_languages": SUPPORTED_LANGUAGES,
            "supported_emotions": [
                "neutral", "calm", "happy", "excited", "sad", "angry", "surprised",
                "fearful", "disgusted", "loving", "frustrated", "confused",
            ],
        }


_default_runtime: Optional[AvatarRuntimeService] = None


def get_avatar_runtime() -> AvatarRuntimeService:
    global _default_runtime
    if _default_runtime is None:
        _default_runtime = AvatarRuntimeService()
    return _default_runtime
