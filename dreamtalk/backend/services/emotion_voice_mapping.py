# Dreamtalk - Voice Module
# ElevenLabs has been removed. This file is kept as a stub to prevent import errors.


class EmotionVoiceMapper:
    """
    Emotion Voice Mapper — DISABLED.
    Previously used for ElevenLabs prosody mapping.
    Kokoro handles emotion naturally through voice selection.
    """

    @staticmethod
    def get_voice_settings(emotion: str, pitch: float = 1.0, speed: float = 1.0, tone: str = "neutral"):
        return {"stability": 0.5, "similarity_boost": 0.75}

    @staticmethod
    def apply_prosody(text: str, emotion: str):
        return text
