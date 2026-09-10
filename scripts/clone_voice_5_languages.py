"""Multi-Language Voice Cloning Pipeline for 5 Indian Languages.

Uses the existing voice sample as the source voice, extracts acoustic features,
creates a voice profile, and generates TTS audio in Tamil, Telugu, Malayalam,
Kannada, and Hindi with emotion-aware modulation.

Usage:
    python scripts/clone_voice_5_languages.py

Output:
    - results/cloned_voice_profiles.json  (voice profile metadata)
    - results/<lang>_cloned_demo_*.wav     (TTS demo samples per language)
    - Avatar API integration for cloned voice selection
"""

import json
import logging
import os
import sys
import uuid
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("clone_5_languages")

# ── Paths ────────────────────────────────────────────────────────────
SOURCE_VOICE = _PROJECT_ROOT / "dreamtalk" / "local_upload_testing" / "Voice_local" / "sample1.wav"
RESULTS_DIR = _PROJECT_ROOT / "results"
TTS_SAMPLES_DIR = _PROJECT_ROOT / "pipeline_outputs" / "tts"
VOICE_PROFILES_PATH = RESULTS_DIR / "cloned_voice_profiles.json"

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(TTS_SAMPLES_DIR, exist_ok=True)

# ── Language Configuration ───────────────────────────────────────────
LANGUAGES = {
    "tamil": {
        "code": "ta",
        "name": "Tamil",
        "edge_voice": "ta-IN-PallaviNeural",
        "kokoro_code": None,
        "test_text": "வணக்கம், நான் உங்கள் டிஜிட்டல் ட்வின். உங்களுக்கு எப்படி உதவ முடியும்?"
    },
    "telugu": {
        "code": "te",
        "name": "Telugu",
        "edge_voice": "te-IN-MohanNeural",
        "kokoro_code": None,
        "test_text": "నమస్కారం, నేను మీ డిజిటల్ ట్విన్. నేను మీకు ఎలా సహాయం చేయగలను?"
    },
    "malayalam": {
        "code": "ml",
        "name": "Malayalam",
        "edge_voice": "ml-IN-MidhunNeural",
        "kokoro_code": None,
        "test_text": "നമസ്കാരം, ഞാൻ നിങ്ങളുടെ ഡിജിറ്റൽ ട്വിൻ. എനിക്ക് നിങ്ങളെ എങ്ങനെ സഹായിക്കാനാകും?"
    },
    "kannada": {
        "code": "kn",
        "name": "Kannada",
        "edge_voice": "kn-IN-SapnaNeural",
        "kokoro_code": None,
        "test_text": "ನಮಸ್ಕಾರ, ನಾನು ನಿಮ್ಮ ಡಿಜಿಟಲ್ ಟ್ವಿನ್. ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?"
    },
    "hindi": {
        "code": "hi",
        "name": "Hindi",
        "edge_voice": "hi-IN-SwaraNeural",
        "kokoro_code": "h",
        "kokoro_voice_female": "hf_alpha",
        "kokoro_voice_male": "hm_omega",
        "test_text": "नमस्ते, मैं आपका डिजिटल ट्विन हूँ। मैं आपकी कैसे मदद कर सकता हूँ?"
    },
}

# ── Step 1: Analyze Source Voice ─────────────────────────────────────

def analyze_source_voice():
    """Extract acoustic features from the source voice sample."""
    logger.info(f"Analyzing source voice: {SOURCE_VOICE}")
    
    if not SOURCE_VOICE.exists():
        logger.error(f"Source voice not found: {SOURCE_VOICE}")
        return None
    
    try:
        from dreamtalk.pipeline.voice_pipeline import VoicePipeline
        
        pipeline = VoicePipeline()
        result = pipeline.run([str(SOURCE_VOICE)], enable_enhancement=True)
        
        voice_profile = {
            "source_file": str(SOURCE_VOICE),
            "duration_seconds": result.duration_seconds,
            "sample_rate": result.sample_rate,
            "pitch_mean": result.pitch_mean,
            "pitch_std": result.pitch_std,
            "pitch_median": result.pitch_median,
            "energy_mean": result.energy_mean,
            "voice_detected": result.voice_detected,
            "speaker_count": result.speaker_count,
            "snr_estimate": result.snr_estimate,
            "gender_prediction": "male" if result.pitch_mean < 165 else "female",
            "speaking_rate": result.speaking_rate,
            "cloned_at": None,
            "languages": {},
        }
        
        logger.info(f"Voice analysis complete: pitch={result.pitch_mean:.1f}Hz, "
                    f"duration={result.duration_seconds:.1f}s, "
                    f"gender={voice_profile['gender_prediction']}")
        return voice_profile
        
    except Exception as e:
        logger.warning(f"Voice analysis via pipeline failed: {e}")
        # Fallback: basic analysis
        import soundfile as sf
        import numpy as np
        
        data, sr = sf.read(str(SOURCE_VOICE))
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        
        duration = len(data) / sr
        rms = np.sqrt(np.mean(data ** 2))
        
        voice_profile = {
            "source_file": str(SOURCE_VOICE),
            "duration_seconds": duration,
            "sample_rate": sr,
            "pitch_mean": 0.0,
            "pitch_std": 0.0,
            "pitch_median": 0.0,
            "energy_mean": float(rms),
            "voice_detected": True,
            "speaker_count": 1,
            "snr_estimate": 0.0,
            "gender_prediction": "female",
            "speaking_rate": 3.0,
            "cloned_at": None,
            "languages": {},
        }
        logger.info(f"Basic voice analysis: duration={duration:.1f}s")
        return voice_profile


# ── Step 2: Clone Voice via Pipeline ─────────────────────────────────

def clone_voice(voice_profile: dict) -> dict:
    """Clone the source voice using the voice pipeline's clone method."""
    logger.info("=" * 60)
    logger.info("Cloning source voice via pipeline...")
    logger.info("=" * 60)
    
    try:
        from dreamtalk.pipeline.voice_pipeline import VoicePipeline
        
        pipeline = VoicePipeline(
            assets_dir=str(_PROJECT_ROOT / "pipeline" / "assets"),
            model_dir=str(_PROJECT_ROOT / "pipeline" / "assets" / "voice_models"),
        )
        
        clone_path, clone_info = pipeline.clone_voice(
            str(SOURCE_VOICE),
            output_dir=str(RESULTS_DIR),
        )
        
        if clone_path and os.path.exists(clone_path):
            voice_profile["clone_file"] = clone_path
            voice_profile["clone_method"] = clone_info.get("method", "unknown")
            voice_profile["clone_confidence"] = clone_info.get("confidence", 0.0)
            logger.info(f"Voice cloned successfully via {clone_info['method']}: {clone_path}")
        else:
            logger.warning("Voice cloning returned no output; using source directly")
            voice_profile["clone_file"] = str(SOURCE_VOICE)
            voice_profile["clone_method"] = "source_direct"
            voice_profile["clone_confidence"] = 0.5
    
    except Exception as e:
        logger.error(f"Voice cloning failed: {e}")
        voice_profile["clone_file"] = str(SOURCE_VOICE)
        voice_profile["clone_method"] = "source_direct"
        voice_profile["clone_confidence"] = 0.3
    
    return voice_profile


# ── Step 3: Generate TTS in All 5 Languages ─────────────────────────

def generate_language_tts(lang_key: str, lang_config: dict, voice_profile: dict) -> str:
    """Generate TTS audio in the target language using the cloned voice characteristics.
    
    Uses emotion-aware voice selection for natural, human-like modulation.
    """
    logger.info(f"Generating {lang_config['name']} TTS...")
    
    output_filename = f"{lang_key}_cloned_demo.mp3"
    output_path = str(RESULTS_DIR / output_filename)
    
    # Try each TTS engine in priority order
    test_text = lang_config["test_text"]
    
    # 1. Edge-TTS (best quality for Indian languages)
    try:
        import edge_tts
        import asyncio
        
        async def _do_edge():
            comm = edge_tts.Communicate(
                test_text,
                lang_config["edge_voice"],
                rate="-5%",
                pitch="+0Hz",
            )
            await comm.save(output_path.replace('.mp3', '.wav'))
        
        wav_path = output_path.replace('.mp3', '.wav')
        asyncio.run(_do_edge())
        
        if os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000:
            # Add cloned voice characteristics via pitch/energy modulation
            modulated_path = _apply_voice_characteristics(
                wav_path, voice_profile, output_path
            )
            if modulated_path:
                logger.info(f"  Edge-TTS {lang_config['name']} complete: {modulated_path}")
                return modulated_path
    
    except Exception as e:
        logger.warning(f"  Edge-TTS failed: {e}")
    
    # 2. Kokoro (Hindi only)
    if lang_config.get("kokoro_code"):
        try:
            import soundfile as sf
            from dreamtalk.voice.core.tts.kokoro_engine import KokoroTTSEngine
            
            engine = KokoroTTSEngine(device="cpu")
            gender = voice_profile.get("gender_prediction", "female")
            voice_name = lang_config.get(
                f"kokoro_voice_{gender}",
                lang_config.get("kokoro_voice_female", "hf_alpha")
            )
            
            audio = engine.synthesize_full(
                test_text,
                voice=voice_name,
                lang_code=lang_config["kokoro_code"],
                speed=1.0,
            )
            if audio is not None:
                wav_path = output_path.replace('.mp3', '.wav')
                sf.write(wav_path, audio, 24000)
                _apply_voice_characteristics(wav_path, voice_profile, output_path)
                logger.info(f"  Kokoro {lang_config['name']} complete")
                return output_path
        except Exception as e:
            logger.warning(f"  Kokoro failed: {e}")
    
    # 3. gTTS (fallback)
    try:
        from gtts import gTTS
        
        tts = gTTS(test_text, lang=lang_config["code"], slow=False)
        mp3_path = output_path
        tts.save(mp3_path)
        
        if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 1000:
            logger.info(f"  gTTS {lang_config['name']} complete: {mp3_path}")
            return mp3_path
    except Exception as e:
        logger.warning(f"  gTTS failed: {e}")
    
    logger.warning(f"  All TTS engines failed for {lang_config['name']}")
    return None


def _apply_voice_characteristics(
    input_wav: str, voice_profile: dict, output_path: str
) -> str:
    """Apply source voice characteristics (pitch, energy) to the TTS output
    for more natural, human-like modulation.
    
    Uses librosa for pitch shifting and energy normalization."""
    try:
        import librosa
        import soundfile as sf
        import numpy as np
        
        y, sr = librosa.load(input_wav, sr=24000)
        
        # Get target pitch from voice profile
        target_pitch = voice_profile.get("pitch_mean", 180.0)
        target_energy = voice_profile.get("energy_mean", 0.3)
        
        if target_pitch <= 0:
            target_pitch = 180.0
        
        # Estimate current pitch
        f0, voiced_flag, _ = librosa.pyin(
            y, fmin=50, fmax=600, sr=sr
        )
        valid_f0 = f0[voiced_flag & ~np.isnan(f0)]
        
        if len(valid_f0) > 0:
            current_pitch = np.mean(valid_f0)
            if current_pitch > 0:
                # Pitch shift to match target
                semitones = 12 * np.log2(target_pitch / current_pitch)
                if abs(semitones) > 0.5:
                    y = librosa.effects.pitch_shift(
                        y=y, sr=sr, n_steps=semitones
                    )
        
        # Apply gentle energy normalization
        current_rms = np.sqrt(np.mean(y ** 2))
        if current_rms > 0 and target_energy > 0:
            gain = min(target_energy / current_rms, 2.0)
            y = y * gain
        
        # Normalize to prevent clipping
        peak = np.max(np.abs(y))
        if peak > 0.95:
            y = y * (0.95 / peak)
        
        sf.write(output_path.replace('.mp3', '.wav'), y, sr)
        return output_path.replace('.mp3', '.wav')
        
    except Exception as e:
        logger.warning(f"Voice characteristic modulation failed: {e}")
        return input_wav


# ── Step 4: Save Voice Profile ──────────────────────────────────────

def save_voice_profile(voice_profile: dict):
    """Save the complete voice profile with all language outputs."""
    # Add timestamp
    from datetime import datetime
    voice_profile["cloned_at"] = datetime.utcnow().isoformat()
    
    with open(VOICE_PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump(voice_profile, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Voice profile saved to {VOICE_PROFILES_PATH}")


# ── Step 5: Update Avatar API Language Config ───────────────────────

def update_avatar_language_config(voice_profile: dict):
    """Update the avatar API's language config to include cloned voice info
    with emotion-aware selection for natural, human-like speech."""
    
    avatar_py = _PROJECT_ROOT / "backend" / "api" / "v1" / "endpoints" / "avatar.py"
    if not avatar_py.exists():
        logger.warning(f"Cannot update avatar API - file not found: {avatar_py}")
        return
    
    with open(avatar_py, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Update the LANGUAGES dict to include cloned voice info
    # The LANGUAGES dict already has Edge-TTS voices for all 5 languages
    # We add cloned voice file paths for reference
    
    # Check if cloned_voice_info already exists
    if "cloned_voice_info" not in content:
        # Add cloned voice info comment near the LANGUAGES dict
        old = "# ── Supported Languages for TTS ──────────────────────────────────────"
        new = "# ── Supported Languages for TTS ──────────────────────────────────────\n"
        new += f"# Cloned voice profile: {VOICE_PROFILES_PATH}\n"
        new += f"# Source: {voice_profile.get('source_file', 'N/A')}\n"
        new += f"# Clone method: {voice_profile.get('clone_method', 'N/A')}\n"
        
        if old in content:
            content = content.replace(old, new)
            with open(avatar_py, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info("Updated avatar.py with cloned voice reference")
    
    logger.info("Avatar language config updated")


# ── Main Pipeline ───────────────────────────────────────────────────

def main():
    """Run the complete multi-language voice cloning pipeline."""
    logger.info("=" * 70)
    logger.info("MULTI-LANGUAGE VOICE CLONING PIPELINE")
    logger.info(f"Source: {SOURCE_VOICE}")
    logger.info(f"Languages: {', '.join(LANGUAGES.keys())}")
    logger.info("=" * 70)
    
    # Step 1: Analyze source voice
    voice_profile = analyze_source_voice()
    if voice_profile is None:
        logger.error("Cannot proceed without source voice analysis")
        return False
    
    # Step 2: Clone voice
    voice_profile = clone_voice(voice_profile)
    
    # Step 3: Generate TTS in all 5 languages
    logger.info("\n" + "=" * 60)
    logger.info("GENERATING MULTI-LANGUAGE TTS OUTPUTS")
    logger.info("=" * 60)
    
    for lang_key, lang_config in LANGUAGES.items():
        output_path = generate_language_tts(lang_key, lang_config, voice_profile)
        if output_path:
            lang_result = {
                "output_file": output_path,
                "test_text": lang_config["test_text"],
                "engine": "edge-tts",
                "voice": lang_config["edge_voice"],
            }
            voice_profile["languages"][lang_key] = lang_result
    
    # Step 4: Save voice profile
    save_voice_profile(voice_profile)
    
    # Step 5: Update avatar API
    update_avatar_language_config(voice_profile)
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Voice Profile: {VOICE_PROFILES_PATH}")
    for lang_key in LANGUAGES:
        if lang_key in voice_profile.get("languages", {}):
            logger.info(f"  {LANGUAGES[lang_key]['name']}: {voice_profile['languages'][lang_key]['output_file']}")
        else:
            logger.warning(f"  {LANGUAGES[lang_key]['name']}: FAILED")
    
    logger.info("\nTo use cloned voices in chat:")
    logger.info("  1. Start backend: cd dreamtalk && python run_server.py")
    logger.info("  2. Chat: POST /api/avatar/chat with text='Hello'")
    logger.info("  3. TTS: POST /api/avatar/tts/generate with language='ta'")
    logger.info(f"\nVoice profile contains {len(voice_profile.get('languages', {}))} languages")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
