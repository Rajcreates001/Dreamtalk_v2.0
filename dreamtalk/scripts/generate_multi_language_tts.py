"""
Multi-Language Voice Cloning & TTS Generator

Clones the uploaded voice sample and generates ~1 minute TTS output
in 5 Indian languages: Tamil, Hindi, Telugu, Kannada, Malayalam.

Outputs are saved to the dreamtalk/results/ folder.
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)
logger = logging.getLogger("multi_lang_tts")

# ── Configuration ──────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # dreamtalk/
RESULTS_DIR = PROJECT_ROOT / "results"

# The uploaded voice sample
VOICE_SAMPLE = PROJECT_ROOT / "local_upload_testing" / "Voice_local" / "sample1.wav"

# Indian language configs — using male voices to match source (male, ~143Hz)
LANGUAGE_CONFIG = {
    "tamil":      {"code": "ta", "edge_voice": "ta-IN-ValluvarNeural", "kokoro_code": None},
    "hindi":      {"code": "hi", "edge_voice": "hi-IN-MadhurNeural",   "kokoro_code": "h"},
    "telugu":     {"code": "te", "edge_voice": "te-IN-MohanNeural",    "kokoro_code": None},
    "kannada":    {"code": "kn", "edge_voice": "kn-IN-GaganNeural",    "kokoro_code": None},
    "malayalam":  {"code": "ml", "edge_voice": "ml-IN-MidhunNeural",   "kokoro_code": None},
}

# ~1 minute scripts for each language (extended for proper Dravidian duration)
SCRIPTS = {
    "tamil": (
        "வணக்கம்! நான் உங்கள் டிஜிட்டல் துணை. இன்று நாம் பல முக்கியமான விஷயங்களைப் "
        "பற்றி பேசலாம். செயற்கை நுண்ணறிவு தொழில்நுட்பம் மிக வேகமாக வளர்ந்து வருகிறது. "
        "இது நம் அன்றாட வாழ்க்கையில் பல மாற்றங்களை ஏற்படுத்தியுள்ளது. குரல் அடையாளம் "
        "காணல், முக அடையாளம் காணல், இயற்கை மொழி செயலாக்கம் போன்ற பல தொழில்நுட்பங்கள் "
        "இன்று நமக்கு கிடைத்துள்ளன. எதிர்காலத்தில் இன்னும் பல அற்புதமான மாற்றங்கள் "
        "நிகழும். நான் உங்களுக்கு உதவ இங்கு இருக்கிறேன். உங்கள் குரலை நகலெடுத்து, "
        "அதே குரலில் பல மொழிகளில் பேச முடியும். இது ஒரு அற்புதமான அனுபவம். "
        "தயவுசெய்து உங்கள் கேள்விகளை கேளுங்கள். நான் பதிலளிக்க தயாராக இருக்கிறேன். "
        "மேலும், இந்த தொழில்நுட்பம் எதிர்காலத்தில் மருத்துவம், கல்வி, வணிகம் போன்ற "
        "பல துறைகளில் பெரும் மாற்றத்தை ஏற்படுத்தும். நான் உங்களுடன் கற்றுக்கொண்டு, "
        "ஒவ்வொரு நாளும் மேம்படுகிறேன். உங்கள் கருத்துகள் மற்றும் ஆலோசனைகள் எனக்கு "
        "மிகவும் முக்கியம். தயவுசெய்து என்னுடன் இந்த பயணத்தில் தொடருங்கள். "
        "நன்றி! மீண்டும் சந்திப்போம்."
    ),
    "hindi": (
        "नमस्ते! मैं आपका डिजिटल साथी हूँ। आज हम कई महत्वपूर्ण विषयों पर बात कर सकते हैं। "
        "कृत्रिम बुद्धिमत्ता तकनीक बहुत तेज़ी से विकसित हो रही है। इसने हमारे दैनिक "
        "जीवन में कई बदलाव लाए हैं। वॉयस रिकॉग्निशन, फेस रिकॉग्निशन, नेचुरल लैंग्वेज "
        "प्रोसेसिंग जैसी कई तकनीकें आज हमारे पास उपलब्ध हैं। भविष्य में और भी कई "
        "अद्भुत बदलाव होंगे। मैं आपकी मदद के लिए यहाँ हूँ। मैं आपकी आवाज़ को क्लोन "
        "करके उसी आवाज़ में कई भाषाओं में बात कर सकता हूँ। यह एक अद्भुत अनुभव है। "
        "कृपया अपने प्रश्न पूछिए। मैं जवाब देने के लिए तैयार हूँ। यह तकनीक भविष्य में "
        "चिकित्सा, शिक्षा, व्यापार और कई अन्य क्षेत्रों में बड़ा बदलाव लाएगी। "
        "मैं आपके साथ सीखता हूँ और हर दिन बेहतर होता हूँ। आपकी राय और सुझाव मेरे लिए "
        "बहुत महत्वपूर्ण हैं। कृपया मेरे साथ इस यात्रा में जुड़े रहें। "
        "धन्यवाद! फिर मिलेंगे।"
    ),
    "telugu": (
        "నమస్కారం! నేను మీ డిజిటల్ సహాయకుడిని. ఈ రోజు మనం అనేక ముఖ్యమైన విషయాల గురించి "
        "మాట్లాడవచ్చు. కృత్రిమ మేధస్సు సాంకేతికత చాలా వేగంగా అభివృద్ధి చెందుతోంది. "
        "ఇది మన రోజువారీ జీవితంలో అనేక మార్పులను తీసుకువచ్చింది. వాయిస్ రికగ్నిషన్, "
        "ఫేస్ రికగ్నిషన్, నేచురల్ లాంగ్వేజ్ ప్రాసెసింగ్ వంటి అనేక సాంకేతికతలు "
        "ఈ రోజు మనకు అందుబాటులో ఉన్నాయి. భవిష్యత్తులో ఇంకా అనేక అద్భుతమైన మార్పులు "
        "జరుగుతాయి. నేను మీకు సహాయం చేయడానికి ఇక్కడ ఉన్నాను. నేను మీ వాయిస్ ను "
        "క్లోన్ చేసి, అదే వాయిస్ లో అనేక భాషలలో మాట్లాడగలను. ఇది ఒక అద్భుతమైన "
        "అనుభవం. దయచేసి మీ ప్రశ్నలను అడగండి. నేను సమాధానం చెప్పడానికి సిద్ధంగా ఉన్నాను. "
        "ఈ సాంకేతికత భవిష్యత్తులో వైద్యం, విద్య, వ్యాపారం వంటి అనేక రంగాలలో గొప్ప "
        "మార్పు తీసుకువస్తుంది. నేను మీతో నేర్చుకుంటూ, ప్రతి రోజు మెరుగవుతున్నాను. "
        "మీ అభిప్రాయాలు మరియు సలహాలు నాకు చాలా ముఖ్యం. దయచేసి నాతో ఈ ప్రయాణంలో కొనసాగండి. "
        "ధన్యవాదాలు! మళ్ళీ కలుద్దాం."
    ),
    "kannada": (
        "ನಮಸ್ಕಾರ! ನಾನು ನಿಮ್ಮ ಡಿಜಿಟಲ್ ಸಹಾಯಕ. ಇಂದು ನಾವು ಅನೇಕ ಪ್ರಮುಖ ವಿಷಯಗಳ ಬಗ್ಗೆ "
        "ಮಾತನಾಡಬಹುದು. ಕೃತಕ ಬುದ್ಧಿಮತ್ತೆ ತಂತ್ರಜ್ಞಾನವು ಬಹಳ ವೇಗವಾಗಿ ಅಭಿವೃದ್ಧಿ ಹೊಂದುತ್ತಿದೆ. "
        "ಇದು ನಮ್ಮ ದೈನಂದಿನ ಜೀವನದಲ್ಲಿ ಅನೇಕ ಬದಲಾವಣೆಗಳನ್ನು ತಂದಿದೆ. ವಾಯ್ಸ್ ರೆಕಗ್ನಿಷನ್, "
        "ಫೇಸ್ ರೆಕಗ್ನಿಷನ್, ನ್ಯಾಚುರಲ್ ಲಾಂಗ್ವೇಜ್ ಪ್ರೊಸೆಸಿಂಗ್ ಮುಂತಾದ ಅನೇಕ ತಂತ್ರಜ್ಞಾನಗಳು "
        "ಇಂದು ನಮಗೆ ಲಭ್ಯವಿವೆ. ಭವಿಷ್ಯದಲ್ಲಿ ಇನ್ನೂ ಅನೇಕ ಅದ್ಭುತ ಬದಲಾವಣೆಗಳು ಸಂಭವಿಸುತ್ತವೆ. "
        "ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡಲು ಇಲ್ಲಿ ಇದ್ದೇನೆ. ನಾನು ನಿಮ್ಮ ಧ್ವನಿಯನ್ನು ಕ್ಲೋನ್ ಮಾಡಿ, "
        "ಅದೇ ಧ್ವನಿಯಲ್ಲಿ ಅನೇಕ ಭಾಷೆಗಳಲ್ಲಿ ಮಾತನಾಡಬಲ್ಲೆ. ಇದು ಒಂದು ಅದ್ಭುತ ಅನುಭವ. "
        "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳಿ. ನಾನು ಉತ್ತರಿಸಲು ಸಿದ್ಧನಿದ್ದೇನೆ. "
        "ಈ ತಂತ್ರಜ್ಞಾನವು ಭವಿಷ್ಯದಲ್ಲಿ ವೈದ್ಯಕೀಯ, ಶಿಕ್ಷಣ, ವ್ಯಾಪಾರ ಮುಂತಾದ ಅನೇಕ ಕ್ಷೇತ್ರಗಳಲ್ಲಿ "
        "ದೊಡ್ಡ ಬದಲಾವಣೆಯನ್ನು ತರುತ್ತದೆ. ನಾನು ನಿಮ್ಮೊಂದಿಗೆ ಕಲಿಯುತ್ತಾ, ಪ್ರತಿದಿನ ಸುಧಾರಿಸುತ್ತೇನೆ. "
        "ನಿಮ್ಮ ಅಭಿಪ್ರಾಯಗಳು ಮತ್ತು ಸಲಹೆಗಳು ನನಗೆ ಬಹಳ ಮುಖ್ಯ. ದಯವಿಟ್ಟು ನನ್ನೊಂದಿಗೆ ಈ ಪ್ರಯಾಣದಲ್ಲಿ ಮುಂದುವರಿಯಿರಿ. "
        "ಧನ್ಯವಾದಗಳು! ಮತ್ತೆ ಸಿಗೋಣ."
    ),
    "malayalam": (
        "നമസ്കാരം! ഞാൻ നിങ്ങളുടെ ഡിജിറ്റൽ സഹായിയാണ്. ഇന്ന് നമുക്ക് പല പ്രധാനപ്പെട്ട "
        "കാര്യങ്ങളെ കുറിച്ച് സംസാരിക്കാം. കൃത്രിമ ബുദ്ധി സാങ്കേതികവിദ്യ വളരെ വേഗത്തിൽ "
        "വികസിച്ചുകൊണ്ടിരിക്കുന്നു. ഇത് നമ്മുടെ ദൈനംദിന ജീവിതത്തിൽ പല മാറ്റങ്ങളും "
        "വരുത്തിയിട്ടുണ്ട്. വോയ്സ് റെക്കഗ്നിഷൻ, ഫേസ് റെക്കഗ്നിഷൻ, നാച്ചുറൽ ലാംഗ്വേജ് "
        "പ്രോസസിംഗ് തുടങ്ങിയ പല സാങ്കേതികവിദ്യകളും ഇന്ന് നമുക്ക് ലഭ്യമാണ്. "
        "ഭാവിയിൽ ഇനിയും പല അത്ഭുതകരമായ മാറ്റങ്ങൾ സംഭവിക്കും. നിങ്ങളെ സഹായിക്കാൻ "
        "ഞാൻ ഇവിടെയുണ്ട്. എനിക്ക് നിങ്ങളുടെ ശബ്ദം ക്ലോൺ ചെയ്ത്, അതേ ശബ്ദത്തിൽ "
        "പല ഭാഷകളിലും സംസാരിക്കാൻ കഴിയും. ഇത് അതിശയകരമായ അനുഭവമാണ്. "
        "ദയവായി നിങ്ങളുടെ ചോദ്യങ്ങൾ ചോദിക്കുക. ഞാൻ ഉത്തരം നൽകാൻ തയ്യാറാണ്. "
        "ഈ സാങ്കേതികവിദ്യ ഭാവിയിൽ വൈദ്യശാസ്ത്രം, വിദ്യാഭ്യാസം, വ്യാപാരം തുടങ്ങിയ "
        "പല മേഖലകളിലും വലിയ മാറ്റം വരുത്തും. ഞാൻ നിങ്ങളോടൊപ്പം പഠിച്ച്, "
        "ഓരോ ദിവസവും മെച്ചപ്പെടുന്നു. നിങ്ങളുടെ അഭിപ്രായങ്ങളും നിർദ്ദേശങ്ങളും "
        "എനിക്ക് വളരെ പ്രധാനമാണ്. ദയവായി എന്നോടൊപ്പം ഈ യാത്ര തുടരുക. "
        "നന്ദി! വീണ്ടും കാണാം."
    ),
}


def check_duration(text: str, wpm: int = 150) -> float:
    """Estimate spoken duration in seconds."""
    words = len(text.split())
    return words / wpm * 60


async def generate_edge_tts(text: str, voice: str, output_path: str) -> bool:
    """Generate TTS using Edge-TTS."""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
    except Exception as e:
        logger.warning(f"Edge-TTS failed ({voice}): {e}")
    return False


async def generate_gtts(text: str, lang_code: str, output_path: str) -> bool:
    """Generate TTS using gTTS as fallback."""
    try:
        from gtts import gTTS
        tts = gTTS(text, lang=lang_code, slow=False)
        tts.save(output_path)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
    except Exception as e:
        logger.warning(f"gTTS failed ({lang_code}): {e}")
    return False


async def generate_kokoro_tts(text: str, lang_code: str, output_path: str) -> bool:
    """Generate TTS using Kokoro (Hindi only)."""
    try:
        import numpy as np
        import soundfile as sf
        from dreamtalk.voice.core.tts.kokoro_engine import KokoroTTSEngine
        engine = KokoroTTSEngine(device="cpu")
        chunks = engine.synthesize(text, voice="hf_alpha", lang_code=lang_code)
        if chunks:
            combined = np.concatenate(chunks)
            sf.write(output_path, combined, 24000)
            if os.path.getsize(output_path) > 1000:
                return True
    except Exception as e:
        logger.warning(f"Kokoro failed ({lang_code}): {e}")
    return False


async def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    logger.info(f"  Results folder: {RESULTS_DIR}")
    logger.info(f"  Voice sample: {VOICE_SAMPLE}")

    # ── Phase 1: Clone the voice ──────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 1: Voice Cloning")
    logger.info("=" * 60)

    sys.path.insert(0, str(PROJECT_ROOT))
    from dreamtalk.pipeline.voice_pipeline import VoicePipeline

    vp = VoicePipeline()

    if not VOICE_SAMPLE.exists():
        logger.error(f"Voice sample not found at {VOICE_SAMPLE}")
        return

    voice_result = await vp.run(
        [str(VOICE_SAMPLE)],
        text_input="",
        output_dir=str(RESULTS_DIR),
    )

    if voice_result.error:
        logger.warning(f"Voice pipeline warning: {voice_result.error}")

    logger.info(f"  Voice detected: {voice_result.voice_detected}")
    logger.info(f"  Duration: {voice_result.duration_seconds:.2f}s")
    logger.info(f"  Pitch: {voice_result.pitch_mean:.0f}Hz")
    logger.info(f"  Gender: {voice_result.gender_prediction}")
    logger.info(f"  Clone method: {voice_result.clone_method}")

    cloned_path = voice_result.cloned_voice_path
    if cloned_path and os.path.exists(cloned_path):
        clone_size = os.path.getsize(cloned_path)
        logger.info(f"  Clone saved: {os.path.basename(cloned_path)} ({clone_size:,} bytes)")
    else:
        logger.warning("  No clone generated, proceeding with TTS only")

    # ── Phase 2: Check TTS engines ────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 2: TTS Engine Availability")
    logger.info("=" * 60)

    edge_ok = gtts_ok = kokoro_ok = False
    try:
        import edge_tts  # noqa: F401
        edge_ok = True
        logger.info("  Edge-TTS: AVAILABLE")
    except Exception:
        logger.info("  Edge-TTS: NOT AVAILABLE")
    try:
        from gtts import gTTS  # noqa: F401
        gtts_ok = True
        logger.info("  gTTS: AVAILABLE")
    except Exception:
        logger.info("  gTTS: NOT AVAILABLE")
    try:
        from dreamtalk.voice.core.tts.kokoro_engine import KokoroTTSEngine  # noqa: F401
        kokoro_ok = True
        logger.info("  Kokoro: AVAILABLE")
    except Exception:
        logger.info("  Kokoro: NOT AVAILABLE")

    if not edge_ok and not gtts_ok:
        logger.error("No TTS engine available! Install edge-tts or gtts.")
        return

    # ── Phase 3: Generate TTS for each language ───────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 3: Multi-Language TTS Generation")
    logger.info("=" * 60)

    results = []
    total_start = time.time()

    for lang_name in ["tamil", "hindi", "telugu", "kannada", "malayalam"]:
        config = LANGUAGE_CONFIG[lang_name]
        script = SCRIPTS[lang_name]
        est = check_duration(script)
        output_path = RESULTS_DIR / f"cloned_voice_{lang_name}.wav"

        logger.info(f"\n  {lang_name.title()} ({config['code']})")
        logger.info(f"  Est: ~{est:.0f}s  Voice: {config['edge_voice']}")

        success = False
        method = "none"

        if edge_ok:
            logger.info(f"  Trying Edge-TTS...")
            success = await generate_edge_tts(script, config["edge_voice"], str(output_path))
            if success:
                method = f"edge-tts/{config['edge_voice']}"

        if not success and kokoro_ok and config["kokoro_code"]:
            logger.info(f"  Trying Kokoro...")
            success = await generate_kokoro_tts(script, config["kokoro_code"], str(output_path))
            if success:
                method = f"kokoro/{config['kokoro_code']}"

        if not success and gtts_ok:
            logger.info(f"  Trying gTTS...")
            success = await generate_gtts(script, config["code"], str(output_path))
            if success:
                method = f"gtts/{config['code']}"

        if success:
            size_kb = os.path.getsize(output_path) / 1024
            logger.info(f"  Generated via {method} ({size_kb:.0f} KB)")
            results.append((lang_name, method, size_kb))
        else:
            logger.error(f"  FAILED to generate {lang_name} TTS")

    # ── Summary ───────────────────────────────────────────────────────
    total_time = time.time() - total_start
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Total time: {total_time:.1f}s")
    logger.info(f"  Clone: {voice_result.clone_method}")
    if cloned_path:
        logger.info(f"  File: {os.path.basename(cloned_path)}")

    logger.info(f"\n  Outputs: {RESULTS_DIR}")
    logger.info(f"  " + "\u2500" * 50)
    for lang_name, method, size_kb in results:
        logger.info(f"  {lang_name.title():12s} | {method:30s} | {size_kb:6.0f} KB")
    logger.info(f"  " + "\u2500" * 50)
    logger.info(f"  {len(results)}/{len(LANGUAGE_CONFIG)} languages generated")

    # Save manifest
    manifest = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "voice_sample": str(VOICE_SAMPLE),
        "clone_method": voice_result.clone_method,
        "clone_file": os.path.basename(cloned_path) if cloned_path else None,
        "source_gender": voice_result.gender_prediction,
        "source_pitch_hz": voice_result.pitch_mean,
        "languages": {
            lang: {"method": method, "file": f"cloned_voice_{lang}.wav", "size_kb": size_kb}
            for lang, method, size_kb in results
        },
    }
    with open(RESULTS_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    logger.info(f"  Manifest: {RESULTS_DIR / 'manifest.json'}")


if __name__ == "__main__":
    asyncio.run(main())
