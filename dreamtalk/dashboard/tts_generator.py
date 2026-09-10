"""
Multi-Language TTS Generator — Web Interface

Upload a voice sample and generate cloned TTS in 5 Indian languages
(Tamil, Hindi, Telugu, Kannada, Malayalam) with audio preview and download.
"""

import asyncio
import os
import sys
import time
import tempfile
import uuid
from pathlib import Path

import streamlit as st
import soundfile as sf

# ── Page config ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="DreamTalk — Multi-Language TTS",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Paths ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Language config — male voices matching source sample ──────────────
LANGUAGES = {
    "tamil":     {"code": "ta", "edge_voice": "ta-IN-ValluvarNeural", "flag": "🇮🇳", "display": "தமிழ் (Tamil)"},
    "hindi":     {"code": "hi", "edge_voice": "hi-IN-MadhurNeural",   "flag": "🇮🇳", "display": "हिन्दी (Hindi)"},
    "telugu":    {"code": "te", "edge_voice": "te-IN-MohanNeural",    "flag": "🇮🇳", "display": "తెలుగు (Telugu)"},
    "kannada":   {"code": "kn", "edge_voice": "kn-IN-GaganNeural",    "flag": "🇮🇳", "display": "ಕನ್ನಡ (Kannada)"},
    "malayalam": {"code": "ml", "edge_voice": "ml-IN-MidhunNeural",   "flag": "🇮🇳", "display": "മലയാളം (Malayalam)"},
}

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


# ═══════════════════════════════════════════════════════════════════════
# TTS Functions
# ═══════════════════════════════════════════════════════════════════════

async def _gen_edge(text: str, voice: str, path: str) -> bool:
    try:
        import edge_tts
        comm = edge_tts.Communicate(text, voice)
        await comm.save(path)
        return os.path.exists(path) and os.path.getsize(path) > 1000
    except Exception:
        return False


async def _gen_gtts(text: str, code: str, path: str) -> bool:
    """gTTS produces MP3 data — use .mp3 extension."""
    try:
        from gtts import gTTS
        gTTS(text, lang=code, slow=False).save(path)
        return os.path.exists(path) and os.path.getsize(path) > 1000
    except Exception:
        return False


async def generate_language(lang_name: str, script: str, output_wav: str,
                            edge_voice: str, lang_code: str) -> dict:
    """Try Edge-TTS (WAV) → gTTS (MP3). Returns result dict."""
    result = {
        "lang": lang_name, "success": False, "method": "none",
        "path": output_wav, "size_kb": 0, "mime": "audio/wav",
    }

    # Try Edge-TTS first (WAV output)
    if await _gen_edge(script, edge_voice, output_wav):
        result["success"] = True
        result["method"] = f"edge-tts ({edge_voice})"
    else:
        # Fallback: gTTS — rename to .mp3
        mp3_path = output_wav.replace(".wav", ".mp3")
        if await _gen_gtts(script, lang_code, mp3_path):
            result["success"] = True
            result["method"] = f"gtts ({lang_code})"
            result["path"] = mp3_path
            result["mime"] = "audio/mp3"

    if result["success"]:
        result["size_kb"] = round(os.path.getsize(result["path"]) / 1024, 1)
    return result


# ═══════════════════════════════════════════════════════════════════════
# Streamlit UI
# ═══════════════════════════════════════════════════════════════════════

def render_sidebar():
    with st.sidebar:
        st.markdown("### 🎙️ DreamTalk TTS")
        st.caption("Multi-lingual Voice Cloning & Synthesis")

        st.divider()
        st.markdown("**How it works:**")
        st.caption(
            "1. Upload a voice sample (WAV/MP3)\n"
            "2. Select target languages\n"
            "3. Click Generate\n"
            "4. Preview & download"
        )

        st.divider()
        st.markdown("**Languages:**")
        for lang_data in LANGUAGES.values():
            st.caption(f"{lang_data['flag']} {lang_data['display']}")

        # Show previous results
        prev = sorted(RESULTS_DIR.glob("cloned_voice_*.*"))
        if prev:
            st.divider()
            st.markdown("**Previous Files:**")
            for f in prev:
                sz = f.stat().st_size / 1024
                st.caption(f"📄 {f.name} ({sz:.0f} KB)")


def render_header():
    st.title("🎙️ Multi-Language TTS Generator")
    st.markdown(
        "Upload a voice sample — the system **analyzes** your voice, "
        "**clones** it, and **synthesizes** speech in 5 Indian languages."
    )


def render_upload_section():
    st.subheader("📤 Step 1: Upload Voice Sample")
    uploaded = st.file_uploader(
        "Upload a voice recording (WAV/MP3, ~5-60s recommended)",
        type=["wav", "mp3", "m4a", "ogg"],
    )

    if uploaded is None:
        sample = PROJECT_ROOT / "local_upload_testing" / "Voice_local" / "sample1.wav"
        if sample.exists():
            st.button("🔬 Use sample voice", on_click=_use_sample, args=(str(sample),))
        return

    # Validate size
    if len(uploaded.getbuffer()) > 50 * 1024 * 1024:
        st.error("File exceeds 50MB limit. Please upload a smaller file.")
        return

    # Save to temp location
    ext = Path(uploaded.name).suffix
    tmp = Path(tempfile.gettempdir()) / f"tts_upload_{uuid.uuid4().hex[:8]}{ext}"
    with open(tmp, "wb") as f:
        f.write(uploaded.getbuffer())

    st.session_state["voice_path"] = str(tmp)
    st.success(f"✅ Uploaded: {uploaded.name} ({len(uploaded.getbuffer()) / 1024:.0f} KB)")

    try:
        data, sr = sf.read(tmp)
        st.audio(tmp)
        st.caption(f"Duration: {len(data)/sr:.1f}s | Sample Rate: {sr}Hz")
    except Exception as e:
        st.warning(f"Preview unavailable: {e}")


def _use_sample(path: str):
    st.session_state["voice_path"] = path


def render_language_selection():
    st.subheader("🌐 Step 2: Select Languages")
    cols = st.columns(5)
    selected = []
    for i, (name, data) in enumerate(LANGUAGES.items()):
        with cols[i]:
            if st.checkbox(f"{data['flag']} {name.title()}", value=True, key=f"lang_{name}"):
                selected.append(name)
    return selected


def display_results(results: list, elapsed: float, clone_info: dict):
    st.subheader("✅ Results")

    c1, c2, c3 = st.columns(3)
    c1.metric("Languages", len(results))
    c2.metric("Time", f"{elapsed:.0f}s")
    avg_sz = sum(r["size_kb"] for r in results) / len(results) if results else 0
    c3.metric("Avg Size", f"{avg_sz:.0f} KB")

    st.divider()

    for r in results:
        with st.container(border=True):
            d = LANGUAGES[r["lang"]]
            ca, cb, cc = st.columns([2, 3, 1])
            with ca:
                st.markdown(f"**{d['flag']} {d['display']}**")
                st.caption(f"Method: {r['method']} | {r['size_kb']:.0f} KB")
            with cb:
                if r["success"] and os.path.exists(r["path"]):
                    st.audio(r["path"], format=r["mime"])
            with cc:
                if r["success"]:
                    with open(r["path"], "rb") as f:
                        st.download_button(
                            "⬇ Download",
                            data=f,
                            file_name=Path(r["path"]).name,
                            mime=r["mime"],
                            use_container_width=True,
                        )

    # Clone info
    ci = clone_info
    if ci and ci.get("path") and os.path.exists(ci["path"]):
        with st.expander("📦 Voice Clone Info", expanded=False):
            co1, co2, co3 = st.columns(3)
            co1.metric("Clone Method", ci.get("method", "N/A"))
            co2.metric("Gender", ci.get("gender") or "N/A")
            co3.metric("Pitch", f"{ci.get('pitch', 0):.0f} Hz")
            with open(ci["path"], "rb") as f:
                st.download_button("⬇ Download Cloned Voice", data=f,
                                   file_name=Path(ci["path"]).name, mime="audio/wav")
            st.audio(ci["path"])


# ═══════════════════════════════════════════════════════════════════════
# Core pipeline
# ═══════════════════════════════════════════════════════════════════════

def run_pipeline(voice_path: str, selected_langs: list) -> tuple:
    """Synchronous wrapper that runs the async pipeline and returns results."""
    sys.path.insert(0, str(PROJECT_ROOT))
    from dreamtalk.pipeline.voice_pipeline import VoicePipeline

    start = time.time()

    # Phase 1: Clone
    bar = st.progress(0, text="Initializing...")
    status = st.empty()

    status.info("🔊 Cloning voice...")
    bar.progress(10, text="Cloning voice...")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        vp = VoicePipeline()
        voice_result = loop.run_until_complete(
            vp.run([voice_path], text_input="", output_dir=str(RESULTS_DIR))
        )
    finally:
        loop.close()

    clone_info = {
        "method": getattr(voice_result, "clone_method", "none"),
        "path": getattr(voice_result, "cloned_voice_path", None),
        "gender": getattr(voice_result, "gender_prediction", None),
        "pitch": getattr(voice_result, "pitch_mean", 0.0),
    }

    if voice_result.error:
        status.warning(f"Voice: {voice_result.error}")
    else:
        status.success(f"✅ {voice_result.gender_prediction}, {voice_result.pitch_mean:.0f}Hz, "
                       f"cloned via {voice_result.clone_method}")

    bar.progress(20, text="Voice cloned")

    # Phase 2: Generate each language
    total = len(selected_langs)
    status.info("🌐 Generating TTS...")
    results = []

    for i, lang_name in enumerate(selected_langs):
        ld = LANGUAGES[lang_name]
        script = SCRIPTS[lang_name]
        output_path = str(RESULTS_DIR / f"cloned_voice_{lang_name}.wav")

        pct = 20 + int((i / total) * 75)
        bar.progress(pct, text=f"Generating {ld['display']}...")
        status.info(f"🔊 {ld['display']}...")

        result = asyncio.run(generate_language(
            lang_name, script, output_path, ld["edge_voice"], ld["code"],
        ))
        results.append(result)

    bar.progress(100, text="Complete!")
    status.success("✅ All languages generated!")

    elapsed = time.time() - start
    return results, elapsed, clone_info


# ═══════════════════════════════════════════════════════════════════════
# App entry point
# ═══════════════════════════════════════════════════════════════════════

def main():
    render_sidebar()
    render_header()

    if "voice_path" not in st.session_state:
        st.session_state["voice_path"] = None

    render_upload_section()

    st.divider()
    selected = render_language_selection()

    st.divider()
    st.subheader("🚀 Step 3: Generate")
    disabled = st.session_state["voice_path"] is None or len(selected) == 0

    if st.button("🎙️ Generate TTS", type="primary", use_container_width=True, disabled=disabled):
        vp = st.session_state["voice_path"]
        with st.spinner(""):  # spinner is visual, progress bar gives detail
            results, elapsed, clone_info = run_pipeline(vp, selected)
        st.session_state["results"] = results
        st.session_state["elapsed"] = elapsed
        st.session_state["clone_info"] = clone_info
        st.rerun()

    if st.session_state.get("results"):
        st.divider()
        display_results(
            st.session_state["results"],
            st.session_state.get("elapsed", 0),
            st.session_state.get("clone_info", {}),
        )


if __name__ == "__main__":
    main()
