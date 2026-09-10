# Dreamtalk - Voice Engine API Router
# Extracted from GPT-SoVITS api.py and api_v2.py

import os
import base64
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/voice", tags=["voice"])


class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize")
    text_language: str = Field("auto", description="Text language")
    ref_audio_path: str = Field(..., description="Reference audio path")
    ref_text: str = Field("", description="Reference text for prompt")
    ref_language: str = Field("auto", description="Reference audio language")
    top_k: int = Field(15, ge=1, le=100)
    top_p: float = Field(1.0, ge=0.0, le=1.0)
    temperature: float = Field(1.0, ge=0.0, le=10.0)
    speed_factor: float = Field(1.0, ge=0.5, le=2.0)
    seed: int = Field(-1)
    output_format: str = Field("wav", pattern="^(wav|mp3)$")


class TTSResponse(BaseModel):
    success: bool
    audio_base64: Optional[str] = None
    sampling_rate: Optional[int] = None
    message: Optional[str] = None


@router.post("/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    try:
        from dreamtalk.voice.core.tts.inference import DreamtalkTTS

        tts = DreamtalkTTS()
        sr, audio = tts.synthesize(
            ref_audio_path=request.ref_audio_path,
            ref_text=request.ref_text,
            ref_language=request.ref_language,
            text=request.text,
            text_language=request.text_language,
            top_k=request.top_k,
            top_p=request.top_p,
            temperature=request.temperature,
            speed_factor=request.speed_factor,
            seed=request.seed,
        )
        import soundfile as sf
        import io
        buf = io.BytesIO()
        sf.write(buf, audio, sr, format=request.output_format)
        buf.seek(0)
        audio_base64 = base64.b64encode(buf.read()).decode("utf-8")
        return TTSResponse(success=True, audio_base64=audio_base64, sampling_rate=sr)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/languages")
async def get_languages():
    return {
        "languages": ["auto", "en", "zh", "ja", "ko", "yue", "all_zh", "all_ja", "all_yue", "all_ko"]
    }


@router.get("/health")
async def health_check():
    return {"status": "ok", "engine": "dreamtalk-voice"}
