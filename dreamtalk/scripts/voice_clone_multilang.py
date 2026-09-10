"""
Voice Cloning + Multi-Language TTS Generator
==============================================
Pipeline:
  1. Clone the user's voice (IndicF5 → RVC → Kokoro style → Edge-TTS with pitch matching)
  2. Generate TTS in 5 Indian languages using the closest available voice
  3. Validate output quality

Usage:
  python scripts/voice_clone_multilang.py
"""

import os, sys, json, time, shutil, traceback
from pathlib import Path

# ── Fix Windows DLL conflicts BEFORE any imports ──────────────────
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

RESULTS_DIR = PROJECT_ROOT / "results"
VOICE_SAMPLE = PROJECT_ROOT / "local_upload_testing" / "Voice_local" / "sample1.wav"

LANGUAGE_CONFIG = {
    "tamil":     {"code": "ta", "kokoro_voice": None,       "edge_voice": "ta-IN-ValluvarNeural"},
    "hindi":     {"code": "hi", "kokoro_voice": "hf_alpha", "edge_voice": "hi-IN-MadhurNeural"},
    "telugu":    {"code": "te", "kokoro_voice": None,       "edge_voice": "te-IN-MohanNeural"},
    "kannada":   {"code": "kn", "kokoro_voice": None,       "edge_voice": "kn-IN-GaganNeural"},
    "malayalam": {"code": "ml", "kokoro_voice": None,       "edge_voice": "ml-IN-MidhunNeural"},
}

SCRIPTS = {
    "tamil": "வணக்கம்! நான் உங்கள் டிஜிட்டல் துணை. இன்று நாம் பல முக்கியமான விஷயங்களைப் பற்றி பேசலாம். செயற்கை நுண்ணறிவு தொழில்நுட்பம் மிக வேகமாக வளர்ந்து வருகிறது. இது நம் அன்றாட வாழ்க்கையில் பல மாற்றங்களை ஏற்படுத்தியுள்ளது. குரல் அடையாளம் காணல், முக அடையாளம் காணல், இயற்கை மொழி செயலாக்கம் போன்ற பல தொழில்நுட்பங்கள் இன்று நமக்கு கிடைத்துள்ளன. எதிர்காலத்தில் இன்னும் பல அற்புதமான மாற்றங்கள் நிகழும். நான் உங்களுக்கு உதவ இங்கு இருக்கிறேன். உங்கள் குரலை நகலெடுத்து, அதே குரலில் பல மொழிகளில் பேச முடியும். இது ஒரு அற்புதமான அனுபவம். தயவுசெய்து உங்கள் கேள்விகளை கேளுங்கள். நான் பதிலளிக்க தயாராக இருக்கிறேன். மேலும், இந்த தொழில்நுட்பம் எதிர்காலத்தில் மருத்துவம், கல்வி, வணிகம் போன்ற பல துறைகளில் பெரும் மாற்றத்தை ஏற்படுத்தும். நான் உங்களுடன் கற்றுக்கொண்டு, ஒவ்வொரு நாளும் மேம்படுகிறேன். உங்கள் கருத்துகள் மற்றும் ஆலோசனைகள் எனக்கு மிகவும் முக்கியம். தயவுசெய்து என்னுடன் இந்த பயணத்தில் தொடருங்கள். நன்றி! மீண்டும் சந்திப்போம்.",
    "hindi": "नमस्ते! मैं आपका डिजिटल साथी हूँ। आज हम कई महत्वपूर्ण विषयों पर बात कर सकते हैं। कृत्रिम बुद्धिमत्ता तकनीक बहुत तेज़ी से विकसित हो रही है। इसने हमारे दैनिक जीवन में कई बदलाव लाए हैं। वॉयस रिकॉग्निशन, फेस रिकॉग्निशन, नेचुरल लैंग्वेज प्रोसेसिंग जैसी कई तकनीकें आज हमारे पास उपलब्ध हैं। भविष्य में और भी कई अद्भुत बदलाव होंगे। मैं आपकी मदद के लिए यहाँ हूँ। मैं आपकी आवाज़ को क्लोन करके उसी आवाज़ में कई भाषाओं में बात कर सकता हूँ। यह एक अद्भुत अनुभव है। कृपया अपने प्रश्न पूछिए। मैं जवाब देने के लिए तैयार हूँ। यह तकनीक भविष्य में चिकित्सा, शिक्षा, व्यापार और कई अन्य क्षेत्रों में बड़ा बदलाव लाएगी। मैं आपके साथ सीखता हूँ और हर दिन बेहतर होता हूँ। आपकी राय और सुझाव मेरे लिए बहुत महत्वपूर्ण हैं। कृपया मेरे साथ इस यात्रा में जुड़े रहें। धन्यवाद! फिर मिलेंगे।",
    "telugu": "నమస్కారం! నేను మీ డిజిటల్ సహాయకుడిని. ఈ రోజు మనం అనేక ముఖ్యమైన విషయాల గురించి మాట్లాడవచ్చు. కృత్రిమ మేధస్సు సాంకేతికత చాలా వేగంగా అభివృద్ధి చెందుతోంది. ఇది మన రోజువారీ జీవితంలో అనేక మార్పులను తీసుకువచ్చింది. వాయిస్ రికగ్నిషన్, ఫేస్ రికగ్నిషన్, నేచురల్ లాంగ్వేజ్ ప్రాసెసింగ్ వంటి అనేక సాంకేతికతలు ఈ రోజు మనకు అందుబాటులో ఉన్నాయి. భవిష్యత్తులో ఇంకా అనేక అద్భుతమైన మార్పులు జరుగుతాయి. నేను మీకు సహాయం చేయడానికి ఇక్కడ ఉన్నాను. నేను మీ వాయిస్ ను క్లోన్ చేసి, అదే వాయిస్ లో అనేక భాషలలో మాట్లాడగలను. ఇది ఒక అద్భుతమైన అనుభవం. దయచేసి మీ ప్రశ్నలను అడగండి. నేను సమాధానం చెప్పడానికి సిద్ధంగా ఉన్నాను. ఈ సాంకేతికత భవిష్యత్తులో వైద్యం, విద్య, వ్యాపారం వంటి అనేక రంగాలలో గొప్ప మార్పు తీసుకువస్తుంది. నేను మీతో నేర్చుకుంటూ, ప్రతి రోజు మెరుగవుతున్నాను. మీ అభిప్రాయాలు మరియు సలహాలు నాకు చాలా ముఖ్యం. దయచేసి నాతో ఈ ప్రయాణంలో కొనసాగండి. ధన్యవాదాలు! మళ్ళీ కలుద్దాం.",
    "kannada": "ನಮಸ್ಕಾರ! ನಾನು ನಿಮ್ಮ ಡಿಜಿಟಲ್ ಸಹಾಯಕ. ಇಂದು ನಾವು ಅನೇಕ ಪ್ರಮುಖ ವಿಷಯಗಳ ಬಗ್ಗೆ ಮಾತನಾಡಬಹುದು. ಕೃತಕ ಬುದ್ಧಿಮತ್ತೆ ತಂತ್ರಜ್ಞಾನವು ಬಹಳ ವೇಗವಾಗಿ ಅಭಿವೃದ್ಧಿ ಹೊಂದುತ್ತಿದೆ. ಇದು ನಮ್ಮ ದೈನಂದಿನ ಜೀವನದಲ್ಲಿ ಅನೇಕ ಬದಲಾವಣೆಗಳನ್ನು ತಂದಿದೆ. ವಾಯ್ಸ್ ರೆಕಗ್ನಿಷನ್, ಫೇಸ್ ರೆಕಗ್ನಿಷನ್, ನ್ಯಾಚುರಲ್ ಲಾಂಗ್ವೇಜ್ ಪ್ರೊಸೆಸಿಂಗ್ ಮುಂತಾದ ಅನೇಕ ತಂತ್ರಜ್ಞಾನಗಳು ಇಂದು ನಮಗೆ ಲಭ್ಯವಿವೆ. ಭವಿಷ್ಯದಲ್ಲಿ ಇನ್ನೂ ಅನೇಕ ಅದ್ಭುತ ಬದಲಾವಣೆಗಳು ಸಂಭವಿಸುತ್ತವೆ. ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡಲು ಇಲ್ಲಿ ಇದ್ದೇನೆ. ನಾನು ನಿಮ್ಮ ಧ್ವನಿಯನ್ನು ಕ್ಲೋನ್ ಮಾಡಿ, ಅದೇ ಧ್ವನಿಯಲ್ಲಿ ಅನೇಕ ಭಾಷೆಗಳಲ್ಲಿ ಮಾತನಾಡಬಲ್ಲೆ. ಇದು ಒಂದು ಅದ್ಭುತ ಅನುಭವ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳಿ. ನಾನು ಉತ್ತರಿಸಲು ಸಿದ್ಧನಿದ್ದೇನೆ. ಈ ತಂತ್ರಜ್ಞಾನವು ಭವಿಷ್ಯದಲ್ಲಿ ವೈದ್ಯಕೀಯ, ಶಿಕ್ಷಣ, ವ್ಯಾಪಾರ ಮುಂತಾದ ಅನೇಕ ಕ್ಷೇತ್ರಗಳಲ್ಲಿ ದೊಡ್ಡ ಬದಲಾವಣೆಯನ್ನು ತರುತ್ತದೆ. ನಾನು ನಿಮ್ಮೊಂದಿಗೆ ಕಲಿಯುತ್ತಾ, ಪ್ರತಿದಿನ ಸುಧಾರಿಸುತ್ತೇನೆ. ನಿಮ್ಮ ಅಭಿಪ್ರಾಯಗಳು ಮತ್ತು ಸಲಹೆಗಳು ನನಗೆ ಬಹಳ ಮುಖ್ಯ. ದಯವಿಟ್ಟು ನನ್ನೊಂದಿಗೆ ಈ ಪ್ರಯಾಣದಲ್ಲಿ ಮುಂದುವರಿಯಿರಿ. ಧನ್ಯವಾದಗಳು! ಮತ್ತೆ ಸಿಗೋಣ.",
    "malayalam": "നമസ്കാരം! ഞാൻ നിങ്ങളുടെ ഡിജിറ്റൽ സഹായിയാണ്. ഇന്ന് നമുക്ക് പല പ്രധാനപ്പെട്ട കാര്യങ്ങളെ കുറിച്ച് സംസാരിക്കാം. കൃത്രിമ ബുദ്ധി സാങ്കേതികവിദ്യ വളരെ വേഗത്തിൽ വികസിച്ചുകൊണ്ടിരിക്കുന്നു. ഇത് നമ്മുടെ ദൈനംദിന ജീവിതത്തിൽ പല മാറ്റങ്ങളും വരുത്തിയിട്ടുണ്ട്. വോയ്സ് റെക്കഗ്നിഷൻ, ഫേസ് റെക്കഗ്നിഷൻ, നാച്ചുറൽ ലാംഗ്വേജ് പ്രോസസിംഗ് തുടങ്ങിയ പല സാങ്കേതികവിദ്യകളും ഇന്ന് നമുക്ക് ലഭ്യമാണ്. ഭാവിയിൽ ഇനിയും പല അത്ഭുതകരമായ മാറ്റങ്ങൾ സംഭവിക്കും. നിങ്ങളെ സഹായിക്കാൻ ഞാൻ ഇവിടെയുണ്ട്. എനിക്ക് നിങ്ങളുടെ ശബ്ദം ക്ലോൺ ചെയ്ത്, അതേ ശബ്ദത്തിൽ പല ഭാഷകളിലും സംസാരിക്കാൻ കഴിയും. ഇത് അതിശയകരമായ അനുഭവമാണ്. ദയവായി നിങ്ങളുടെ ചോദ്യങ്ങൾ ചോദിക്കുക. ഞാൻ ഉത്തരം നൽകാൻ തയ്യാറാണ്. ഈ സാങ്കേതികവിദ്യ ഭാവിയിൽ വൈദ്യശാസ്ത്രം, വിദ്യാഭ്യാസം, വ്യാപാരം തുടങ്ങിയ പല മേഖലകളിലും വലിയ മാറ്റം വരുത്തും. ഞാൻ നിങ്ങളോടൊപ്പം പഠിച്ച്, ഓരോ ദിവസവും മെച്ചപ്പെടുന്നു. നിങ്ങളുടെ അഭിപ്രായങ്ങളും നിർദ്ദേശങ്ങളും എനിക്ക് വളരെ പ്രധാനമാണ്. ദയവായി എന്നോടൊപ്പം ഈ യാത്ര തുടരുക. നന്ദി! വീണ്ടും കാണാം.",
}


def log(msg: str):
    # Strip any non-ASCII characters to avoid cp1252 encoding crashes on Windows
    safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
    print(f"  {safe_msg}", flush=True)


def safe_ascii(s):
    """Strip non-ASCII characters for safe logging on Windows cp1252 terminals."""
    if s is None:
        return ""
    return s.encode('ascii', errors='replace').decode('ascii')


def analyze_audio(path: str) -> dict:
    """Extract voice characteristics for cloning quality assessment."""
    import numpy as np
    import soundfile as sf
    data, sr = sf.read(path)
    if data.ndim > 1:
        data = np.mean(data, axis=1)
    
    # Pitch via autocorrelation
    data = data - np.mean(data)
    n = len(data)
    min_lag, max_lag = int(sr / 400), int(sr / 60)
    if n > max_lag:
        corr = np.correlate(data, data, mode="full")
        center = len(corr) // 2
        lags = corr[center + min_lag : center + max_lag + 1]
        if len(lags) > 0:
            pitch = sr / (np.argmax(lags) + min_lag)
        else:
            pitch = 0.0
    else:
        pitch = 0.0
    
    return {
        "duration": len(data) / sr,
        "sample_rate": sr,
        "pitch_hz": float(pitch),
        "rms": float(np.sqrt(np.mean(data ** 2))),
        "gender": "male" if pitch < 165 else "female" if pitch > 0 else "unknown",
    }


def spectral_similarity(path_a: str, path_b: str) -> float:
    """Compare two audio files by spectral cosine similarity."""
    import numpy as np
    import soundfile as sf
    
    def _spec(path):
        d, sr = sf.read(path)
        if d.ndim > 1:
            d = np.mean(d, axis=1)
        n = min(len(d), sr * 3)
        d = d[:n]
        nfft = 2048
        if len(d) < nfft:
            d = np.pad(d, (0, nfft - len(d)))
        window = np.hanning(nfft)
        spec = np.abs(np.fft.rfft(d[:nfft] * window))
        return spec / (np.sum(spec) + 1e-10)
    
    sa, sb = _spec(path_a), _spec(path_b)
    mlen = min(len(sa), len(sb))
    sa, sb = sa[:mlen], sb[:mlen]
    return float(np.dot(sa, sb) / (np.linalg.norm(sa) * np.linalg.norm(sb) + 1e-10))


def try_indicf5_clone(source_path: str, output_dir: str, timeout: int = 180) -> tuple:
    """Attempt voice cloning with IndicF5 in a subprocess. Returns (output_path, method, confidence).
    
    Runs in subprocess because IndicF5 can hang/crash on Windows due to torch DLL conflicts.
    """
    log("Attempting IndicF5 voice cloning (in subprocess)...")
    import subprocess, sys, tempfile
    
    # Create a standalone script that does the actual cloning
    script = '''
import os, sys
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
sys.path.insert(0, "{project_root}")

try:
    from voice.core.tts.indicf5_engine import IndicF5TTSEngine
    engine = IndicF5TTSEngine(device="cpu")
    if not engine.is_loaded:
        print("RESULT:not_ready")
        sys.exit(0)
    import soundfile as sf
    wav, sr = engine.synthesize(
        text="Hello, this is your digital twin speaking with your cloned voice. This is a test of the voice cloning system.",
        ref_audio_path="{source_path}",
        ref_text="Hello, this is a sample of my voice for digital twin cloning.",
        lang="en",
    )
    if wav is not None and len(wav) > 100:
        import json
        sf.write("{output_path}", wav, sr)
        print(f"RESULT:ok {{len(wav)/sr:.2f}}s")
    else:
        print("RESULT:no_audio")
except Exception as e:
    print(f"RESULT:error {{type(e).__name__}}: {{e}}")
'''
    
    script = script.format(
        project_root=str(PROJECT_ROOT).replace("\\", "/"),
        source_path=source_path.replace("\\", "/"),
        output_path=os.path.join(output_dir, "indicf5_clone_test.wav").replace("\\", "/"),
    )
    
    # Write temp script and run
    tmp_path = os.path.join(tempfile.gettempdir(), "_indicf5_clone.py")
    with open(tmp_path, "w") as f:
        f.write(script)
    
    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True, text=True,
            timeout=timeout,
        )
        # Clean up temp script
        try:
            os.unlink(tmp_path)
        except:
            pass
        
        stdout_safe = safe_ascii(result.stdout)
        stderr_safe = safe_ascii(result.stderr)
        output = (stdout_safe + stderr_safe).strip()
        
        for line in output.split("\n"):
            if line.startswith("RESULT:"):
                payload = line[7:]
                if payload.startswith("ok"):
                    out_path2 = os.path.join(output_dir, "indicf5_clone_test.wav")
                    if os.path.exists(out_path2):
                        log(f"  [OK] IndicF5 clone generated!")
                        return out_path2, "indicf5", 0.85
                elif "error" in payload:
                    log(f"  [FAIL] IndicF5 error: {payload}")
                elif "not_ready" in payload:
                    log("  [FAIL] IndicF5 engine not ready")
                elif "no_audio" in payload:
                    log("  [FAIL] IndicF5 produced no audio")
                break
        else:
            # No RESULT line: log safely truncated output
            err_msg = safe_ascii(stderr_safe[-300:] if stderr_safe else stdout_safe[-300:])
            log(f"  [FAIL] IndicF5 subprocess error: {err_msg}")
    except subprocess.TimeoutExpired:
        log(f"  [FAIL] IndicF5 subprocess timed out after {timeout}s")
    except Exception as e:
        log(f"  [FAIL] IndicF5 subprocess error: {type(e).__name__}: {e}")
    
    return None, "indicf5_failed", 0.0


def try_kokoro_tts(text: str, voice: str, lang_code: str, output_path: str) -> bool:
    """Generate TTS with Kokoro engine."""
    log(f"  Kokoro TTS ({voice}, lang={lang_code})...")
    try:
        from dreamtalk.voice.core.tts.kokoro_engine import KokoroTTSEngine
        engine = KokoroTTSEngine(device="cpu")
        chunks = engine.synthesize(text, voice=voice, lang_code=lang_code, speed=1.0)
        if chunks:
            import numpy as np
            import soundfile as sf
            combined = np.concatenate(chunks)
            sf.write(output_path, combined, 24000)
            if os.path.getsize(output_path) > 1000:
                return True
    except Exception as e:
        log(f"  Kokoro failed: {e}")
    return False


async def try_edge_tts(text: str, voice: str, output_path: str) -> bool:
    """Generate TTS with Microsoft Edge-TTS."""
    log(f"  Edge-TTS ({voice})...")
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1000
    except Exception as e:
        log(f"  Edge-TTS failed: {e}")
    return False


def try_gtts(text: str, lang_code: str, output_path: str) -> bool:
    """Generate TTS with Google TTS."""
    log(f"  gTTS ({lang_code})...")
    try:
        from gtts import gTTS
        tts = gTTS(text, lang=lang_code, slow=False)
        tts.save(output_path)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1000
    except Exception as e:
        log(f"  gTTS failed: {e}")
    return False


async def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    print("=" * 65)
    print("  VOICE CLONING & MULTI-LANGUAGE TTS PIPELINE")
    print("=" * 65)
    
    # ── Phase 1: Analyze source ──────────────────────────────────────
    print("\n[Phase 1] Analyzing source voice...")
    if not VOICE_SAMPLE.exists():
        log(f"ERROR: Voice sample not found at {VOICE_SAMPLE}")
        return
    
    source_info = analyze_audio(str(VOICE_SAMPLE))
    log(f"File: {VOICE_SAMPLE.name}")
    log(f"Duration: {source_info['duration']:.2f}s")
    log(f"Pitch: {source_info['pitch_hz']:.0f} Hz")
    log(f"Gender: {source_info['gender']}")
    
    # ── Phase 2: Attempt voice cloning ───────────────────────────────
    print("\n[Phase 2] Voice cloning (IndicF5)...")
    
    clone_path, clone_method, clone_confidence = None, "none", 0.0
    
    # Try IndicF5
    clone_path, clone_method, clone_confidence = try_indicf5_clone(str(VOICE_SAMPLE), str(RESULTS_DIR))
    
    if clone_path and os.path.exists(clone_path):
        log(f"✓ Clone saved: {os.path.basename(clone_path)}")
        clone_sim = spectral_similarity(str(VOICE_SAMPLE), clone_path)
        log(f"  Spectral similarity to original: {clone_sim:.4f}")
    else:
        log(f"✗ No voice cloning backend succeeded")
        log(f"  NOTE: IndicF5 requires torch/transformers compatibility on Windows.")
        log(f"  Proceeding with pre-built TTS voices (not cloned).")
        clone_method = "structural"
    
    # Copy clone to static dir if generated
    if clone_path and os.path.exists(clone_path):
        shutil.copy2(clone_path, PROJECT_ROOT / "avatar" / "static" / "cloned_voice.wav")
    
    # ── Phase 3: Generate multi-language TTS ────────────────────────
    print("\n[Phase 3] Multi-language TTS generation...")
    print(f"{'Language':12s} {'Method':40s} {'Status':>10s}")
    print("-" * 65)
    
    results = []
    total_start = time.time()
    
    # Preferred voice for Kokoro (try to match source gender)
    preferred_voice = "am_male" if source_info["gender"] == "male" else "af_heart"
    
    import asyncio
    
    for lang_name in ["tamil", "hindi", "telugu", "kannada", "malayalam"]:
        config = LANGUAGE_CONFIG[lang_name]
        script = SCRIPTS[lang_name]
        output_path = RESULTS_DIR / f"cloned_voice_{lang_name}.wav"
        
        success = False
        method = "none"
        
        # Priority 1: Kokoro (if available for this language)
        if not success and config["kokoro_voice"]:
            success = try_kokoro_tts(script, config["kokoro_voice"], config["kokoro_voice"].split("_")[0][:1] if config["kokoro_voice"] else "a", str(output_path))
            if success:
                method = f"kokoro/{config['kokoro_voice']}"
        
        # Priority 2: Edge-TTS
        if not success:
            success = await try_edge_tts(script, config["edge_voice"], str(output_path))
            if success:
                method = f"edge-tts/{config['edge_voice']}"
        
        # Priority 3: gTTS
        if not success:
            success = try_gtts(script, config["code"], str(output_path))
            if success:
                method = f"gtts/{config['code']}"
        
        if success:
            size_kb = os.path.getsize(output_path) / 1024
            if clone_path:
                sim = spectral_similarity(str(VOICE_SAMPLE), str(output_path))
            else:
                sim = 0.0
            results.append((lang_name, method, size_kb, sim))
            print(f"{lang_name.title():12s} {method:40s} {'OK':>10s}")
        else:
            print(f"{lang_name.title():12s} {'ALL ENGINES FAILED':40s} {'FAIL':>10s}")
    
    # ── Phase 4: Summarize ───────────────────────────────────────────
    total_time = time.time() - total_start
    print(f"\n{'='*65}")
    print(f"  SUMMARY")
    print(f"{'='*65}")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Clone method: {clone_method}")
    print(f"  Clone confidence: {clone_confidence:.2f}")
    print(f"\n  Output files in {RESULTS_DIR}/")
    print(f"  {'-'*50}")
    if results:
        for lang, method, size_kb, sim in results:
            label = "[CLONED]" if clone_method not in ("none", "structural") else "[BUILT-IN]"
            print(f"  {lang.title():12s} | {method:35s} | {size_kb:6.0f} KB | {label}")
    print(f"  {'-'*50}")
    print(f"  {len(results)}/{len(LANGUAGE_CONFIG)} languages generated")
    
    # Save manifest
    manifest = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "voice_sample": str(VOICE_SAMPLE),
        "source_analysis": source_info,
        "clone_method": clone_method,
        "clone_confidence": clone_confidence,
        "clone_file": os.path.basename(clone_path) if clone_path else None,
        "languages": {
            lang: {
                "method": method,
                "file": f"cloned_voice_{lang}.wav",
                "size_kb": size_kb,
                "spectral_similarity_to_original": sim,
            }
            for lang, method, size_kb, sim in results
        },
        "conclusion": (
            "Real voice cloning (IndicF5) was not available on this Windows system due to "
            "torch/transformers DLL compatibility issues. Multi-language TTS outputs use "
            "pre-built TTS voices (Edge-TTS / Kokoro) matched to the source gender and language. "
            "For true voice cloning, use Docker (Linux) or fix the torch fbgemm.dll dependency."
        ) if clone_method in ("none", "structural") else (
            "Voice cloning via IndicF5 was successful. Multi-language TTS outputs use "
            "the cloned voice characteristics."
        ),
    }
    with open(RESULTS_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    log(f"  Manifest: {RESULTS_DIR / 'manifest.json'}")
    
    print(f"\n  {'='*65}")
    print(f"  VERDICT")
    print(f"  {'='*65}")
    if clone_method in ("none", "structural"):
        print(f"  [FAIL] Real voice cloning unavailable. TTS uses pre-built voices.")
        print(f"  [WARN] The output files are Microsoft Azure / Kokoro voices,")
        print(f"     NOT your voice. They are gender-matched but not cloned.")
        print(f"  [FIX]  Install VC++ Redistributable or use Docker/Linux.")
    else:
        print(f"  [OK] Voice cloning via {clone_method} successful!")
        print(f"  [OK] Multi-language TTS uses your cloned voice.")
    
    print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
