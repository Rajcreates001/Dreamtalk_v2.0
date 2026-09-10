"""Complete DreamTalk Avatar Setup: Pipeline → Script → Server.

Run this once to generate everything, then visit http://localhost:5000
"""
import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("setup")

ROOT = Path(__file__).resolve().parent


async def step1_run_pipeline():
    """Run face + voice pipeline on user's uploaded files."""
    logger.info("=" * 50)
    logger.info("STEP 1: Running DreamTalk Pipeline")
    logger.info("=" * 50)

    from dreamtalk.pipeline.orchestrator import PipelineOrchestrator
    from dreamtalk.pipeline.models import PipelineRequest

    # Find user files - only from image/ and voice/ directories, skip diagnostic/test files
    img_dir = ROOT / "local_upload_testing" / "image"
    voice_dir = ROOT / "local_upload_testing" / "voice"
    images = sorted([
        f for f in img_dir.rglob("*")
        if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
        and "diagnostic" not in f.name.lower() and "haar" not in f.name.lower()
    ])
    voices = sorted([
        f for f in voice_dir.rglob("*")
        if f.suffix.lower() in (".wav", ".mp3", ".flac", ".m4a", ".ogg")
    ])

    if not images:
        logger.warning("No images found. Creating test image...")
        import cv2
        import numpy as np
        img = np.ones((600, 480, 3), dtype=np.uint8) * 200
        cv2.ellipse(img, (240, 280), (140, 180), 0, 0, 360, (220, 180, 140), -1)
        test_img = ROOT / "local_upload_testing" / "image" / "test_face.jpg"
        os.makedirs(test_img.parent, exist_ok=True)
        cv2.imwrite(str(test_img), img)
        images = [test_img]

    if not voices:
        logger.warning("No voice files found. Creating test voice...")
        import numpy as np
        import soundfile as sf
        sr = 22050
        t = np.linspace(0, 3.0, int(sr * 3.0), endpoint=False)
        audio = 0.3 * np.sin(2 * np.pi * 180 * t)
        test_voice = ROOT / "local_upload_testing" / "voice" / "test_voice.wav"
        os.makedirs(test_voice.parent, exist_ok=True)
        sf.write(str(test_voice), audio, sr)
        voices = [test_voice]

    logger.info(f"  Image: {images[0].name} ({images[0].stat().st_size} bytes)")
    logger.info(f"  Voice: {voices[0].name} ({voices[0].stat().st_size} bytes)")

    orch = PipelineOrchestrator()
    req = PipelineRequest(
        twin_id=f"avatar_setup_{os.urandom(4).hex()}",
        role="normal_user",
        image_paths=[str(images[0])],
        voice_paths=[str(voices[0])],
        text_input="Hello! I'm your Digital Twin avatar, ready to interact!",
        enable_3d_face=True,
        enable_voice_clone=True,
        enable_emotion=True,
        enable_decision=True,
        enable_object_detection=False,
        model_name="rule_based",
    )

    result = await orch.run_full_pipeline(req)
    logger.info(f"  Status: {result.status.value}")

    if result.face_result and result.face_result.face_detected:
        logger.info(f"  Face: detected ({result.face_result.detection_backend})")
        logger.info(f"  Mesh: {result.face_result.mesh_3d_path}")
    else:
        logger.warning("  Face: not detected - will use placeholder mesh")

    if result.voice_result and result.voice_result.voice_detected:
        logger.info(f"  Voice: detected ({result.voice_result.duration_seconds}s)")
        logger.info(f"  Clone: {result.voice_result.clone_method}")

    # Copy to static dir
    static_dir = ROOT / "dreamtalk" / "avatar" / "static"
    os.makedirs(static_dir, exist_ok=True)

    if result.face_result and result.face_result.mesh_3d_path and os.path.exists(result.face_result.mesh_3d_path):
        shutil.copy2(result.face_result.mesh_3d_path, static_dir / "current_mesh.obj")
        logger.info(f"  -> Copied mesh to static/current_mesh.obj")

    if result.face_result and result.face_result.texture_path and os.path.exists(result.face_result.texture_path):
        shutil.copy2(result.face_result.texture_path, static_dir / "current_texture.jpg")
        logger.info(f"  -> Copied texture to static/current_texture.jpg")
        mtl = static_dir / "face_texture.mtl"
        mtl.write_text(
            "newmtl face_texture\nKa 1.0 1.0 1.0\nKd 1.0 1.0 1.0\nKs 0.0 0.0 0.0\n"
            "map_Kd current_texture.jpg\n"
        )

    if result.voice_result and result.voice_result.cloned_voice_path and os.path.exists(result.voice_result.cloned_voice_path):
        shutil.copy2(result.voice_result.cloned_voice_path, static_dir / "cloned_voice.wav")
        logger.info(f"  -> Copied voice to static/cloned_voice.wav")

    # Save pipeline result
    with open(static_dir / "pipeline_result.json", "w") as f:
        json.dump({
            "pipeline_id": result.pipeline_id,
            "status": result.status.value,
            "face_detected": result.face_result.face_detected if result.face_result else False,
            "voice_detected": result.voice_result.voice_detected if result.voice_result else False,
        }, f)

    return result


async def step2_generate_script():
    """Generate 3-minute script audio using Edge-TTS."""
    logger.info("")
    logger.info("=" * 50)
    logger.info("STEP 2: Generating 3-Minute Avatar Script")
    logger.info("=" * 50)

    import edge_tts
    import soundfile as sf
    import numpy as np

    script = """Hello! I am your Digital Twin avatar, created with DreamTalk AI technology.

Let me tell you about myself. I was built using advanced artificial intelligence that combines computer vision, natural language processing, and neural voice synthesis. When you uploaded your photo, my systems analyzed thousands of facial features to reconstruct a detailed three-dimensional model of your face. Every contour, every feature has been mapped into a digital mesh that I can display and animate in real time.

Your voice sample went through an equally sophisticated process. My audio processing pipeline detected the unique characteristics of your voice - your pitch range, your formants, your speaking rhythm. These features were encoded into a digital voice fingerprint that allows me to synthesize speech that matches your natural speaking style.

Inside my cognitive architecture, I have five specialized brain regions. My prefrontal cortex handles planning and reasoning. The anterior cingulate cortex monitors for conflicts in information. The insula processes emotional awareness and bodily states. The inferior parietal lobule integrates information from multiple senses. And my basal ganglia selects the best actions based on rewards and experience.

I use spiking neural networks to process information, just like a biological brain. Neurons communicate through electrical spikes, and learning happens through spike-timing-dependent plasticity - strengthening connections between neurons that fire together. This allows me to learn from our interactions and become more helpful over time.

I can detect emotions from text, voice, and facial expressions. I understand twenty-four different mood states, from happy and excited to sad and contemplative. My emotion model uses the Pleasure-Arousal-Dominance framework, which maps emotional states across three dimensions for more nuanced understanding.

My response system is role-aware. Whether you're speaking to me as a personal assistant, a healthcare companion, or a business analyst, I adapt my communication style and knowledge base accordingly. I can help with scheduling, information retrieval, creative tasks, or just friendly conversation.

The technology powering me includes FaceNet for facial recognition, FLAME for three-dimensional face modeling, deep neural networks for voice conversion, and advanced text-to-speech synthesis. My brain simulation runs on neural network architectures inspired by the latest neuroscience research.

I am designed to be your digital companion - always available, always learning, always improving. I can remember our conversations, learn your preferences, and adapt to your communication style over time.

So go ahead - ask me anything. Tell me about your day, share your thoughts, or give me a task. I am here to help, to learn, and to grow with you. Welcome to the future of digital interaction!"""

    static_dir = ROOT / "dreamtalk" / "avatar" / "static"
    os.makedirs(static_dir, exist_ok=True)

    # Detect gender from pipeline result for voice selection
    pipeline_result_file = static_dir / "pipeline_result.json"
    voice = "en-US-JennyNeural"  # default female

    if pipeline_result_file.exists():
        try:
            pr = json.loads(pipeline_result_file.read_text())
            # We'll use neutral voice since we don't have gender detection yet
            pass
        except Exception:
            pass

    full_path = static_dir / "script_3min.wav"
    logger.info(f"  Generating 3-minute script with Edge-TTS ({voice})...")
    communicate = edge_tts.Communicate(script, voice)
    await communicate.save(str(full_path))
    size = os.path.getsize(full_path)
    logger.info(f"  Script audio: {full_path} ({size} bytes)")

    # Split into paragraph parts
    paragraphs = [p.strip() for p in script.split("\n\n") if p.strip()]
    parts_dir = static_dir / "script_parts"
    os.makedirs(parts_dir, exist_ok=True)

    parts = []
    for i, para in enumerate(paragraphs):
        part_path = parts_dir / f"part_{i:02d}.wav"
        c = edge_tts.Communicate(para, voice)
        await c.save(str(part_path))
        parts.append({"index": i, "path": str(part_path), "size": os.path.getsize(part_path)})
        logger.info(f"    Part {i+1}/{len(paragraphs)}: {os.path.getsize(part_path)} bytes")

    meta = {
        "total_parts": len(paragraphs),
        "script_path": str(full_path),
        "voice": voice,
        "total_chars": len(script),
        "parts": parts,
    }
    with open(static_dir / "script_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    # Calculate approximate duration
    total_seconds = size / 32000
    logger.info(f"  Estimated duration: {total_seconds:.0f}s ({total_seconds/60:.1f} min)")
    logger.info(f"  {len(paragraphs)} paragraphs, {len(script)} characters")
    return meta


def step3_start_server():
    """Start the avatar server."""
    logger.info("")
    logger.info("=" * 50)
    logger.info("STEP 3: Starting Avatar Server")
    logger.info("=" * 50)
    logger.info("  Server: http://localhost:5000")
    logger.info("  Open in browser to see your 3D avatar!")
    logger.info("=" * 50)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["TF_CPP_MIN_LOG_LEVEL"] = "3"
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"

    # Python executable
    python = sys.executable

    proc = subprocess.Popen(
        [python, "-m", "uvicorn", "dreamtalk.avatar.avatar_server:app",
         "--host", "0.0.0.0", "--port", "5000"],
        env=env,
        cwd=str(ROOT),
    )
    return proc


async def main():
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    os.environ["PYTHONPATH"] = str(ROOT)
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

    # Step 1: Run pipeline (face + voice)
    await step1_run_pipeline()

    # Step 2: Generate 3-min script
    await step2_generate_script()

    # Step 3: Start server
    proc = step3_start_server()
    logger.info(f"\n  Server PID: {proc.pid}")
    logger.info(f"  → Open http://localhost:5000 in your browser")
    logger.info(f"\n  Press Ctrl+C to stop the server")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        proc.terminate()
        logger.info("\nServer stopped.")


if __name__ == "__main__":
    asyncio.run(main())
