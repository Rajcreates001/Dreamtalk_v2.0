"""
DreamTalk — Voice Profile Manager

Manages voice cloning profiles: creation from reference audio,
storage in PostgreSQL, retrieval for TTS synthesis, and profile
lifecycle (activate/deactivate/delete).

Architecture:
  User uploads 30-60s audio → ASR transcribes ref text →
  Profile stored in DB → TTS uses ref_audio for voice cloning

Usage:
    manager = VoiceProfileManager()
    profile = await manager.create_profile(user_id, name, audio_path, language="hi")
    profiles = await manager.list_profiles(user_id)
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger("dreamtalk.voice_profile")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VOICE_PROFILES_DIR = PROJECT_ROOT / "voice_module" / "assets" / "voice_profiles"


class VoiceProfileManager:
    """Create, store, and manage voice cloning profiles."""

    def __init__(self):
        os.makedirs(VOICE_PROFILES_DIR, exist_ok=True)

    async def create_profile(
        self,
        user_id: str,
        name: str,
        audio_path: str,
        language: str = "hi",
        ref_text: str = "",
    ) -> Dict[str, Any]:
        """Create a voice profile from reference audio.

        Args:
            user_id: UUID of the user.
            name: Human-readable name for the profile.
            audio_path: Path to the reference audio (30-60s WAV).
            language: ISO 639-1 language code.
            ref_text: Transcript of the reference audio (optional — ASR will generate if empty).

        Returns:
            Dict with profile_id, name, language, ref_audio_path, ref_text.
        """
        # Copy audio to profiles directory
        profile_id = str(uuid.uuid4())
        ext = Path(audio_path).suffix or ".wav"
        profile_dir = VOICE_PROFILES_DIR / user_id
        os.makedirs(profile_dir, exist_ok=True)
        stored_path = profile_dir / f"{profile_id}{ext}"

        import shutil
        shutil.copy2(audio_path, stored_path)

        # If no ref_text provided, try to transcribe with ASR
        if not ref_text.strip():
            try:
                from dreamtalk.voice.core.asr import get_recognizer
                recognizer = get_recognizer()
                result = await recognizer.transcribe(str(stored_path), language=language)
                ref_text = result.text
                logger.info(f"ASR auto-transcribed ref audio: {len(ref_text)} chars")
            except Exception as e:
                logger.warning(f"ASR auto-transcription failed: {e}")
                ref_text = ""

        profile = {
            "id": profile_id,
            "user_id": user_id,
            "name": name,
            "language": language,
            "ref_audio_path": str(stored_path),
            "ref_text": ref_text,
            "provider": "indicf5",
            "is_cloned": True,
        }

        # Store in database
        try:
            from dreamtalk.backend.db.database import execute
            await execute(
                """INSERT INTO voice_profiles
                   (id, user_id, name, provider, language, ref_audio_path, ref_text, is_cloned)
                   VALUES ($1, $2, $3, 'indicf5', $4, $5, $6, TRUE)""",
                uuid.UUID(profile_id), uuid.UUID(user_id),
                name, language, str(stored_path), ref_text,
            )
            logger.info(f"Voice profile created: {name} ({language}) for user {user_id}")
        except Exception as e:
            logger.warning(f"DB storage failed (profile still usable): {e}")

        return profile

    async def list_profiles(self, user_id: str) -> List[Dict[str, Any]]:
        """List all voice profiles for a user."""
        try:
            from dreamtalk.backend.db.database import fetch
            rows = await fetch(
                """SELECT id, name, language, ref_audio_path, ref_text, provider,
                          is_cloned, is_active, created_at
                   FROM voice_profiles
                   WHERE user_id = $1 AND is_active = TRUE
                   ORDER BY created_at DESC""",
                uuid.UUID(user_id),
            )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"Failed to list profiles from DB: {e}")
            return []

    async def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get a voice profile by ID."""
        try:
            from dreamtalk.backend.db.database import fetchrow
            row = await fetchrow(
                """SELECT * FROM voice_profiles WHERE id = $1""",
                uuid.UUID(profile_id),
            )
            return dict(row) if row else None
        except Exception as e:
            logger.warning(f"Failed to get profile: {e}")
            return None

    async def delete_profile(self, profile_id: str) -> bool:
        """Delete a voice profile."""
        try:
            from dreamtalk.backend.db.database import execute
            # Delete audio file
            profile = await self.get_profile(profile_id)
            if profile and profile.get("ref_audio_path"):
                audio_path = Path(profile["ref_audio_path"])
                if audio_path.exists():
                    audio_path.unlink()

            await execute(
                "DELETE FROM voice_profiles WHERE id = $1",
                uuid.UUID(profile_id),
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to delete profile: {e}")
            return False

    def get_ref_audio_for_synthesis(self, profile: Dict[str, Any]) -> Optional[bytes]:
        """Read reference audio bytes for TTS synthesis."""
        ref_path = profile.get("ref_audio_path")
        if ref_path and os.path.exists(ref_path):
            with open(ref_path, "rb") as f:
                return f.read()
        return None
