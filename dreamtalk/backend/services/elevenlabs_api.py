# Dreamtalk - Voice Module
# ElevenLabs has been removed. All voice operations use local engines (Kokoro, RVC, IndicF5).
# This file is kept as a placeholder only — no functionality remaining.


class ElevenLabsAPI:
    """
    ElevenLabs API wrapper — DISABLED.
    This class is retained only as a stub to prevent import errors in legacy code.
    All its methods raise NotImplementedError.
    """

    def __init__(self):
        self.api_key = ""

    async def get_voices(self):
        return {"voices": []}

    async def text_to_speech(self, voice_id: str, text: str, voice_settings: dict = None):
        raise NotImplementedError("ElevenLabs is disabled. Use Kokoro TTS or RVC instead.")

    async def clone_voice(self, name: str, description: str, files: list):
        raise NotImplementedError("ElevenLabs is disabled. Use RVC for local voice cloning.")
