from pydantic import BaseModel, Field
from typing import Optional


class CreateDigitalHumanRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = ""
    category: str = "personal"
    personality: Optional[str] = ""
    voice_id: Optional[str] = None
    style: str = "realistic"
    color_scheme: str = "emerald"
    outfit: str = "default"
    hair_style: str = "default"
    eye_glow: Optional[str] = "#10b981"


class UpdateDigitalHumanRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    personality: Optional[str] = None
    voice_id: Optional[str] = None
    style: Optional[str] = None
    color_scheme: Optional[str] = None
    outfit: Optional[str] = None
    hair_style: Optional[str] = None
    eye_glow: Optional[str] = None


class DigitalHumanResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: str
    personality: Optional[str] = None
    style: str = "realistic"
    color_scheme: str = "emerald"
    outfit: str = "default"
    hair_style: str = "default"
    eye_glow: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str


class SubscriptionResponse(BaseModel):
    id: str
    tier: str
    status: str
    current_period_start: str
    current_period_end: Optional[str] = None


class SettingsResponse(BaseModel):
    id: str
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    tts_provider: str = "kokoro"
    tts_voice: str = "af_heart"
    stt_provider: str = "whisper"
    theme: str = "dark"
    language: str = "en"
    notification_enabled: bool = True


class UpdateSettingsRequest(BaseModel):
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    tts_provider: Optional[str] = None
    tts_voice: Optional[str] = None
    stt_provider: Optional[str] = None
    theme: Optional[str] = None
    language: Optional[str] = None
    notification_enabled: Optional[bool] = None


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    avatar_url: Optional[str] = None
