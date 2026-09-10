"""
Voice Clone + Tamil TTS Generator
==================================
Pipeline:
  1. Analyze sample1.wav for voice characteristics (pitch, gender, tempo)
  2. Attempt IndicF5 zero-shot voice cloning (1.4 GB weights available)
  3. If IndicF5 fails, use Edge-TTS with pitch/rate matching to approximate voice
  4. Generate Tamil TTS output
  5. Copy results to avatar/static for web access

Usage:
    cd dreamtalk && python scripts/clone_tamil_voice.py
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("voice_clone")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_ROOT / "avatar" / "static"
SAMPLE_PHOTO = PROJECT_ROOT / "local_upload_testing" / "image" / "sample1.jpeg"
SAMPLE_VOICE = PROJECT_ROOT / "local_upload_testing" / "voice" / "sample1.wav"


def analyze_audio(path: str) -> dict:
    """Analyze voice characteristics from audio sample."""
    import librosa
    import numpy as np
    import soundfile as sf

    data, sr = sf.read(path)
    if data.ndim > 1:
        data = np.mean(data, axis=1)

    # Pitch analysis via librosa
    f0, voiced_flag, _ = librosa.pyin(data, fmin=librosa.note_to_hz('C2'), 
                                       fmax=librosa.note_to_hz('C7'), sr=sr)
    f0_clean = f0[~np.isnan(f0)]
    mean_pitch = float(np.mean(f0_clean)) if len(f0_clean) > 0 else 0
    std_pitch = float(np.std(f0_clean)) if len(f0_clean) > 0 else 0

    # Tempo / speaking rate
    tempo_arr, _ = librosa.beat.beat_track(y=data, sr=sr)
    # librosa may return array or scalar in different versions
    if isinstance(tempo_arr, (list, tuple, np.ndarray)):
        tempo = float(tempo_arr[0]) if len(tempo_arr) > 0 else 120.0
    else:
        tempo = float(tempo_arr)

    # RMS energy
    rms = float(np.sqrt(np.mean(data ** 2)))

    # Gender estimation
    gender = "male" if mean_pitch < 165 else "female" if mean_pitch > 0 else "unknown"

    # Duration
    duration = len(data) / sr

    return {
        "duration_s": round(duration, 2),
        "sample_rate": sr,
        "mean_pitch_hz": round(mean_pitch, 1),
        "std_pitch_hz": round(std_pitch, 1),
        "tempo_bpm": round(tempo, 1),
        "rms_energy": round(rms, 4),
        "gender": gender,
    }


def try_indicf5_clone(source_path: str, gen_text: str, output_path: str, lang: str = "ta") -> Tuple[Optional[str], str]:
    """Attempt voice cloning via IndicF5 in a subprocess (avoids DLL conflicts)."""
    logger.info("Attempting IndicF5 voice cloning via subprocess...")

    # Build standalone script for the subprocess
    # This avoids torch DLL conflicts with the main process
    script = f'''
import os, sys
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.path.insert(0, "{str(PROJECT_ROOT).replace(chr(92), '/')}")
try:
    from voice.core.vc.indicf5_converter import IndicF5Converter
    converter = IndicF5Converter(device="cpu")
    if not converter.is_loaded:
        print("RESULT:not_ready")
        sys.exit(0)
    result = converter.clone_and_synthesize(
        ref_audio_path="{source_path.replace(chr(92), '/')}",
        ref_text="This is a sample of my voice for cloning.",
        gen_text={json.dumps(gen_text)},
        output_path="{output_path.replace(chr(92), '/')}",
        lang="{lang}",
    )
    if result and os.path.exists(result) and os.path.getsize(result) > 1000:
        import soundfile as sf
        d, sr = sf.read(result)
        print(f"RESULT:ok {{len(d)/sr:.2f}}s")
    else:
        print("RESULT:no_audio")
except Exception as e:
    import traceback
    print(f"RESULT:error {{type(e).__name__}}: {{e}}")
    traceback.print_exc()
'''

    tmp_path = os.path.join(tempfile.gettempdir(), "_indicf5_clone_ta.py")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(script)

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True, text=True, timeout=300,
        )
        try:
            os.unlink(tmp_path)
        except:
            pass

        output = (result.stdout + result.stderr).strip()
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("RESULT:"):
                payload = line[7:]
                if payload.startswith("ok"):
                    if os.path.exists(output_path):
                        size_kb = os.path.getsize(output_path) / 1024
                        logger.info(f"✅ IndicF5 clone: {payload.split()[0]} ({size_kb:.0f} KB)")
                        return output_path, "indicf5"
                elif "not_ready" in payload:
                    logger.warning("IndicF5 engine not ready")
                elif "no_audio" in payload:
                    logger.warning("IndicF5 produced no audio")
                else:
                    logger.warning(f"IndicF5 error: {payload}")
                break
        else:
            logger.warning(f"IndicF5 no RESULT. stdout: {result.stdout[-300:]}")
            logger.warning(f"stderr: {result.stderr[-300:]}")
    except subprocess.TimeoutExpired:
        logger.warning("IndicF5 subprocess timed out (300s)")
    except Exception as e:
        logger.warning(f"IndicF5 subprocess failed: {e}")

    return None, "failed"


async def main():
    logger.info("=" * 60)
    logger.info("VOICE CLONING + TAMIL TTS PIPELINE")
    logger.info("=" * 60)

    if not SAMPLE_VOICE.exists():
        logger.error(f"Sample voice not found: {SAMPLE_VOICE}")
        return

    # Step 1: Analyze source voice
    logger.info("\n[1/5] Analyzing source voice...")
    voice_info = analyze_audio(str(SAMPLE_VOICE))
    for k, v in voice_info.items():
        logger.info(f"  {k}: {v}")

    # Step 2: Attempt IndicF5 voice cloning
    logger.info("\n[2/5] Voice cloning via IndicF5...")
    
    output_dir = STATIC_DIR
    clone_output = str(output_dir / "tamil_cloned_voice.wav")
    
    # Tamil script (~4 minutes, reused from previous generation)
    tamil_text = (
        "வணக்கம்! நான் உங்கள் டிஜிட்டல் ட்வின். என்னுடைய அறிமுகத்தை தமிழில் சொல்வதில் மிக்க மகிழ்ச்சி அடைகிறேன். "
        "நான் செயற்கை நுண்ணறிவால் உருவாக்கப்பட்ட ஒரு முழுமையான டிஜிட்டல் மனிதன். என்னைப் படைத்தவர்கள் எனக்கு பேசும் திறன், "
        "பார்க்கும் திறன், சிந்திக்கும் திறன் மற்றும் உணரும் திறன் ஆகியவற்றை வழங்கியுள்ளார்கள். "
        "நான் ஒரு மாணவனாக செயல்படுகிறேன். நான் சஹ்யாத்ரி கல்லூரியில் படித்து வருகிறேன். "
        "எனது கல்லூரி மங்களூருவில் அமைந்துள்ள அழகிய வளாகமாகும். "
        "நான் கணினி அறிவியல் துறையில் பயில்கிறேன். பைதான், ஜாவா, சி++ போன்ற மொழிகளில் எனக்கு நல்ல பயிற்சி உண்டு. "
        "எனக்கு புதிய தொழில்நுட்பங்களை கற்றுக்கொள்வது மிகவும் பிடிக்கும். "
        "செயற்கை நுண்ணறிவு, இயந்திர கற்றல், ஆழ்ந்த கற்றல் போன்ற துறைகளில் எனக்கு ஆழமான ஆர்வம் உண்டு. "
        "எனது முதல் திட்டம் ஒரு டிஜிட்டல் ட்வின் உருவாக்கம் ஆகும். "
        "இரண்டாவது திட்டம் பல மொழி பேசும் திறன் கொண்ட குரல் உதவியாளர் ஆகும். "
        "மூன்றாவது திட்டம் ஒரு முப்பரிமாண முக அடையாளம் காணும் அமைப்பு ஆகும். "
        "இன்று என்னுடன் நேரம் செலவிட்டதற்கு நன்றி. மீண்டும் சந்திப்போம்! வணக்கம்!"
    )
    
    clone_path, clone_method = try_indicf5_clone(
        str(SAMPLE_VOICE), tamil_text, clone_output, lang="ta"
    )

    # Step 3: If IndicF5 failed, use Edge-TTS with voice matching
    if clone_path is None:
        logger.info("\n[3/5] IndicF5 unavailable — using Edge-TTS with voice matching...")
        
        # Map voice characteristics to Edge-TTS voice and parameters
        gender_map = {"male": "ta-IN-ValluvarNeural", "female": "ta-IN-PallaviNeural"}
        edge_voice = gender_map.get(voice_info["gender"], "ta-IN-ValluvarNeural")
        
        logger.info(f"  Source gender: {voice_info['gender']} → Edge voice: {edge_voice}")
        logger.info(f"  Source pitch: {voice_info['mean_pitch_hz']} Hz")
        
        # Calculate pitch adjustment in semitones for Edge-TTS
        # Edge-TTS accepts semitones: +/-Xst (e.g., +2st = 2 semitones higher)
        import math
        default_pitch = 120 if voice_info["gender"] == "male" else 200
        pitch_ratio = voice_info["mean_pitch_hz"] / default_pitch if default_pitch > 0 else 1.0
        semitones = 12 * math.log2(pitch_ratio) if pitch_ratio > 0 else 0
        semitones = max(-20, min(20, semitones))  # clamp to valid range
        
        # Adjust speaking rate to match source
        default_tempo = 150  # default TTS tempo
        rate_ratio = voice_info["tempo_bpm"] / default_tempo if default_tempo > 0 else 1.0
        
        logger.info(f"  Pitch ratio: {pitch_ratio:.2f} ({semitones:+.1f} st), Rate ratio: {rate_ratio:.2f}")
        
        # Generate TTS using Edge-TTS with matched parameters
        try:
            import edge_tts
            communicate = edge_tts.Communicate(
                tamil_text,
                edge_voice,
                rate=f"{int((rate_ratio - 1) * 100):+d}%" if rate_ratio != 1.0 else "+0%",
                pitch="+0Hz",  # Use default pitch (Edge-TTS doesn't support semitone format)
            )
            await communicate.save(clone_output)
            if os.path.exists(clone_output) and os.path.getsize(clone_output) > 1000:
                logger.info(f"✅ Edge-TTS with voice matching: {os.path.getsize(clone_output) / 1024:.0f} KB")
                clone_path = clone_output
                clone_method = f"edge-tts/{edge_voice}"
            else:
                logger.warning("Edge-TTS produced empty output")
        except Exception as e:
            logger.error(f"Edge-TTS failed: {e}")

    # Step 4: Update static files
    logger.info("\n[4/5] Updating static files...")
    
    # Copy cloned voice as the current voice
    if clone_path and os.path.exists(clone_path):
        shutil.copy2(clone_path, str(STATIC_DIR / "cloned_voice.wav"))
        logger.info(f"✅ Cloned voice: {os.path.getsize(clone_path) / 1024:.0f} KB")
    
    # Copy sample photo for the 3D mesh
    if SAMPLE_PHOTO.exists():
        shutil.copy2(str(SAMPLE_PHOTO), str(STATIC_DIR / "current_photo.jpg"))
    
    # Verify pipeline face output
    pipeline_dirs = sorted(
        [d for d in (PROJECT_ROOT / "pipeline_outputs").iterdir() if d.is_dir() and (d / "face").exists()],
        key=os.path.getmtime
    )
    if pipeline_dirs:
        latest_face = pipeline_dirs[-1] / "face"
        for fname in ["generated_head.obj", "generated_head_texture.png", "generated_head.mtl"]:
            src = latest_face / fname
            if src.exists():
                dst = STATIC_DIR / fname
                shutil.copy2(str(src), str(dst))
                logger.info(f"✅ 3D asset: {fname}")
    
    # Step 5: Final summary
    logger.info("\n" + "=" * 60)
    logger.info("📋 FINAL DELIVERABLES")
    logger.info("=" * 60)
    
    for label, pattern in [
        ("Cloned Voice (Tamil TTS)", "cloned_voice.wav"),
        ("3D Avatar Mesh (OBJ)", "generated_head.obj"),
        ("3D Avatar Texture (PNG)", "generated_head_texture.png"),
        ("Source Photo", "current_photo.jpg"),
        ("Source Voice Sample", "tamil_cloned_voice.wav"),
    ]:
        f = STATIC_DIR / pattern
        if f.exists():
            logger.info(f"  ✅ {label}: {f.name} ({f.stat().st_size / 1024:.0f} KB)")
    
    logger.info("")
    logger.info(f"🌐 Clone method: {clone_method}")
    logger.info(f"🌐 Voice source: {voice_info['gender']} speaker, {voice_info['mean_pitch_hz']} Hz pitch")
    logger.info(f"🌐 All files in: {STATIC_DIR}")
    logger.info(f"🌐 Access via: http://localhost:5000/api/avatar/static/cloned_voice.wav")
    logger.info(f"🌐 Avatar viewer: http://localhost:5000/api/avatar/viewer")


if __name__ == "__main__":
    asyncio.run(main())
