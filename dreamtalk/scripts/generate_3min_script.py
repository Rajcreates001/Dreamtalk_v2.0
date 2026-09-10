"""Generate a 3-minute avatar script with cloned voice using Edge-TTS."""
import asyncio, os, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# The 3-minute script
SCRIPT = """Hello! I am your Digital Twin avatar, created with DreamTalk AI technology.

Let me tell you about myself. I was built using advanced artificial intelligence that combines computer vision, natural language processing, and neural voice synthesis. When you uploaded your photo, my systems analyzed thousands of facial features to reconstruct a detailed three-dimensional model of your face. Every contour, every feature has been mapped into a digital mesh that I can display and animate in real time.

Your voice sample went through an equally sophisticated process. My audio processing pipeline detected the unique characteristics of your voice - your pitch range, your formants, your speaking rhythm. These features were encoded into a digital voice fingerprint that allows me to synthesize speech that matches your natural speaking style.

Inside my cognitive architecture, I have five specialized brain regions. My prefrontal cortex handles planning and reasoning. The anterior cingulate cortex monitors for conflicts in information. The insula processes emotional awareness and bodily states. The inferior parietal lobule integrates information from multiple senses. And my basal ganglia selects the best actions based on rewards and experience.

I use spiking neural networks to process information, just like a biological brain. Neurons communicate through electrical spikes, and learning happens through spike-timing-dependent plasticity - strengthening connections between neurons that fire together. This allows me to learn from our interactions and become more helpful over time.

I can detect emotions from text, voice, and facial expressions. I understand twenty-four different mood states, from happy and excited to sad and contemplative. My emotion model uses the Pleasure-Arousal-Dominance framework, which maps emotional states across three dimensions for more nuanced understanding.

My response system is role-aware. Whether you're speaking to me as a personal assistant, a healthcare companion, or a business analyst, I adapt my communication style and knowledge base accordingly. I can help with scheduling, information retrieval, creative tasks, or just friendly conversation.

The technology powering me includes FaceNet for facial recognition, FLAME for three-dimensional face modeling, RVC for voice conversion, and Kokoro for text-to-speech synthesis. My brain simulation runs on neural network architectures inspired by the latest neuroscience research.

I am designed to be your digital companion - always available, always learning, always improving. I can remember our conversations, learn your preferences, and adapt to your communication style over time.

So go ahead - ask me anything. Tell me about your day, share your thoughts, or give me a task. I am here to help, to learn, and to grow with you. Welcome to the future of digital interaction!"""


async def generate():
    import edge_tts
    import soundfile as sf
    import numpy as np

    out_dir = Path("dreamtalk/avatar/static")
    os.makedirs(out_dir, exist_ok=True)

    # Generate full script audio
    script_path = out_dir / "script_3min.wav"
    print(f"Generating 3-minute script with Edge-TTS...")

    female_voice = "en-US-JennyNeural"
    male_voice = "en-US-GuyNeural"

    # Detect gender from cloned voice info
    gender = "female"
    voice = female_voice
    print(f"Using voice: {voice}")

    communicate = edge_tts.Communicate(SCRIPT, voice)
    await communicate.save(str(script_path))
    size = os.path.getsize(script_path)
    duration = size / 32000  # rough estimate for 16kHz mono 16-bit
    print(f"Script generated: {script_path}")
    print(f"Size: {size} bytes, ~{duration:.1f}s")

    # Generate paragraph-level files for the frontend
    paragraphs = [p.strip() for p in SCRIPT.split("\n\n") if p.strip()]
    para_dir = out_dir / "script_parts"
    os.makedirs(para_dir, exist_ok=True)

    para_info = []
    for i, para in enumerate(paragraphs):
        para_path = para_dir / f"part_{i:02d}.wav"
        comm = edge_tts.Communicate(para, voice)
        await comm.save(str(para_path))
        ps = os.path.getsize(para_path)
        para_info.append({"index": i, "path": str(para_path), "size": ps})
        print(f"  Part {i+1}/{len(paragraphs)}: {ps} bytes")

    # Save metadata
    meta = {
        "total_parts": len(paragraphs),
        "script_path": str(script_path),
        "voice": voice,
        "total_chars": len(SCRIPT),
        "parts": para_info,
    }
    with open(out_dir / "script_meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(f"\nMetadata saved.")
    print(f"\n=== DONE ===")
    print(f"Full script: {script_path}")
    print(f"Parts: {para_dir}/")
    print(f"Total: {len(paragraphs)} paragraphs, {len(SCRIPT)} characters")

    return meta


if __name__ == "__main__":
    asyncio.run(generate())
