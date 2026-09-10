# Dreamtalk - Orchestration Module
# Extracted from Handcrafted Persona Engine (MIT License)
# Persona configuration dataclasses, ported from C# appsettings.json structure.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LlmConfig:
    """LLM connection settings (from PersonaEngine.Lib.Configuration.LlmOptions)."""

    text_api_key: str = ""
    text_model: str = "llama-3.1-8b-instant"
    text_endpoint: str = "https://api.groq.com/openai/v1"
    vision_api_key: str = ""
    vision_model: str = "qwen2.5-vl-3b-instruct"
    vision_endpoint: str = ""
    vision_enabled: bool = False


@dataclass
class KokoroVoiceConfig:
    """Kokoro TTS engine settings (from PersonaEngine.Lib.Configuration.KokoroVoiceOptions)."""

    default_voice: str = "af_heart"
    use_british_english: bool = False
    default_speed: float = 1.0
    max_phoneme_length: int = 510
    sample_rate: int = 24000
    trim_silence: bool = False


@dataclass
class Qwen3TtsConfig:
    """Qwen3 expressive TTS engine settings (from Qwen3TtsOptions)."""

    speaker: str = "kasumiva"
    language: str = "english"
    instruct: Optional[str] = None
    temperature: float = 0.9
    top_k: int = 50
    top_p: float = 1.0
    repetition_penalty: float = 1.05
    max_new_tokens: int = 512
    emit_every_frames: int = 8
    code_predictor_greedy: bool = False
    silence_penalty_enabled: bool = True


@dataclass
class RvcConfig:
    """Real-time voice cloning settings (from RVCFilterOptions)."""

    default_voice: str = "KasumiVA"
    enabled: bool = False
    hop_size: int = 64
    speaker_id: int = 0
    f0_up_key: int = 1


@dataclass
class TtsConfig:
    """Top-level TTS configuration (from TtsConfiguration)."""

    active_engine: str = "kokoro"
    espeak_path: str = "espeak-ng"
    model_directory: str = "Resources"
    kokoro: KokoroVoiceConfig = field(default_factory=KokoroVoiceConfig)
    qwen3: Qwen3TtsConfig = field(default_factory=Qwen3TtsConfig)
    rvc: RvcConfig = field(default_factory=RvcConfig)


@dataclass
class AsrConfig:
    """ASR / Whisper configuration (from AsrConfiguration)."""

    tts_mode: str = "performant"
    tts_prompt: str = "Aria, Joobel"
    vad_threshold: float = 0.5
    vad_threshold_gap: float = 0.15
    vad_min_speech_duration: float = 150.0
    vad_min_silence_duration: float = 450.0


@dataclass
class LipSyncConfig:
    """Lip-sync engine configuration (from LipSyncOptions)."""

    engine: str = "VBridger"
    identity: str = "James"
    use_gpu: bool = True
    solver_type: str = "Bvls"


@dataclass
class Live2DConfig:
    """Live2D model configuration (from Live2DOptions)."""

    model_path: str = "Resources/live2d"
    model_name: str = "aria"
    width: int = 1080
    height: int = 1920


@dataclass
class ConversationConfig:
    """Turn-level conversation behaviour (from ConversationOptions)."""

    barge_in_type: int = 3
    barge_in_min_words: int = 3


@dataclass
class PersonaConfig:
    """Aggregate persona configuration (from AvatarAppConfig + ConversationContextOptions).

    This is the top-level config object that mirrors the C# AvatarAppConfig
    and provides all knobs exposed in appsettings.json.
    """

    llm: LlmConfig = field(default_factory=LlmConfig)
    tts: TtsConfig = field(default_factory=TtsConfig)
    asr: AsrConfig = field(default_factory=AsrConfig)
    lip_sync: LipSyncConfig = field(default_factory=LipSyncConfig)
    live2d: Live2DConfig = field(default_factory=Live2DConfig)
    conversation: ConversationConfig = field(default_factory=ConversationConfig)

    system_prompt: str = ""
    system_prompt_file: Optional[str] = "personality.txt"
    use_custom_prompt: bool = False
    current_context: str = ""
    topics: list[str] = field(default_factory=lambda: ["casual conversation"])

    window_width: int = 1366
    window_height: int = 768
