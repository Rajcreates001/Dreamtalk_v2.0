"""Run the full pipeline on user-uploaded files and prepare for the avatar server."""
import asyncio
import json
import logging
import os
import sys
import shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("avatar_pipeline")

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["PYTHONPATH"] = str(Path(__file__).resolve().parent)


async def main():
    # Check uploaded files
    local_dir = Path("local_upload_testing")
    images = list(local_dir.glob("image/*")) + list(local_dir.glob("image/*.*"))
    voices = list(local_dir.glob("voice/*")) + list(local_dir.glob("voice/*.*"))

    img_dir = local_dir / "image"
    voice_dir = local_dir / "voice"
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
        logger.warning("No images found in local_upload_testing/image/")
        # Generate a test image
        import cv2
        import numpy as np
        img = np.ones((600, 480, 3), dtype=np.uint8) * 200
        cv2.ellipse(img, (240, 280), (140, 180), 0, 0, 360, (220, 180, 140), -1)
        cv2.circle(img, (200, 240), 12, (40, 40, 60), -1)
        cv2.circle(img, (280, 240), 12, (40, 40, 60), -1)
        cv2.ellipse(img, (240, 300), (50, 20), 0, 0, 180, (80, 40, 40), 3)
        test_img = local_dir / "image" / "test_face.jpg"
        os.makedirs(test_img.parent, exist_ok=True)
        cv2.imwrite(str(test_img), img)
        images = [test_img]
        logger.info(f"Generated test face image: {test_img}")

    if not voices:
        logger.warning("No voice files found in local_upload_testing/voice/")
        # Generate test voice (sine wave)
        import numpy as np
        sr = 22050
        t = np.linspace(0, 3.0, int(sr * 3.0), endpoint=False)
        audio = 0.3 * np.sin(2 * np.pi * 180 * t)
        audio += 0.15 * np.sin(2 * np.pi * 350 * t)
        fade = min(int(sr * 0.05), len(audio))
        audio[:fade] *= np.linspace(0, 1, fade)
        audio[-fade:] *= np.linspace(1, 0, fade)
        import soundfile as sf
        test_voice = local_dir / "voice" / "test_voice.wav"
        os.makedirs(test_voice.parent, exist_ok=True)
        sf.write(str(test_voice), audio, sr)
        voices = [test_voice]
        logger.info(f"Generated test voice: {test_voice}")

    logger.info(f"Using image: {images[0]}")
    logger.info(f"Using voice: {voices[0]}")

    # Import and run pipeline
    from dreamtalk.pipeline.orchestrator import PipelineOrchestrator
    from dreamtalk.pipeline.models import PipelineRequest

    orch = PipelineOrchestrator()
    twin_id = f"avatar_user_{os.urandom(4).hex()}"

    req = PipelineRequest(
        twin_id=twin_id,
        role="normal_user",
        image_paths=[str(images[0])],
        voice_paths=[str(voices[0])],
        text_input="Hello! I'm excited to use DreamTalk avatar!",
        enable_3d_face=True,
        enable_voice_clone=True,
        enable_emotion=True,
        enable_decision=True,
        enable_object_detection=False,
        model_name="rule_based",
    )

    result = await orch.run_full_pipeline(req)

    logger.info(f"Pipeline: {result.status.value}")
    fr = result.face_result
    vr = result.voice_result
    br = result.brain_result

    if fr:
        logger.info(f"  Face detected: {fr.face_detected}")
        logger.info(f"  Mesh: {fr.mesh_3d_path}")
        logger.info(f"  Texture: {fr.texture_path}")

    if vr:
        logger.info(f"  Voice detected: {vr.voice_detected}")
        logger.info(f"  Clone: {vr.cloned_voice_path}")
        logger.info(f"  Clone method: {vr.clone_method}")
        logger.info(f"  TTS: {vr.tts_sample_path}")

    if br:
        logger.info(f"  Brain response: {br.response_text[:100]}...")

    # Copy mesh and texture to avatar static dir for serving
    avatar_static = Path("dreamtalk/avatar/static")
    os.makedirs(avatar_static, exist_ok=True)

    if fr and fr.mesh_3d_path and os.path.exists(fr.mesh_3d_path):
        shutil.copy2(fr.mesh_3d_path, avatar_static / "current_mesh.obj")
        logger.info(f"Copied mesh to {avatar_static / 'current_mesh.obj'}")
    else:
        logger.warning("No mesh file to copy - will use placeholder")

    if fr and fr.texture_path and os.path.exists(fr.texture_path):
        shutil.copy2(fr.texture_path, avatar_static / "current_texture.jpg")
        logger.info(f"Copied texture to {avatar_static / 'current_texture.jpg'}")

        # Create MTL file
        mtl_path = avatar_static / "face_texture.mtl"
        mtl_path.write_text(
            "newmtl face_texture\n"
            "Ka 1.0 1.0 1.0\nKd 1.0 1.0 1.0\nKs 0.0 0.0 0.0\n"
            "map_Kd current_texture.jpg\n"
        )
        logger.info(f"Created MTL at {mtl_path}")
    else:
        logger.warning("No texture file to copy")

    if vr and vr.cloned_voice_path and os.path.exists(vr.cloned_voice_path):
        shutil.copy2(vr.cloned_voice_path, avatar_static / "cloned_voice.wav")
        logger.info(f"Copied cloned voice to {avatar_static / 'cloned_voice.wav'}")

    logger.info("\n=== AVATAR PIPELINE COMPLETE ===")
    logger.info(f"Pipeline ID: {result.pipeline_id}")
    logger.info("Run: uvicorn dreamtalk.avatar.avatar_server:app --host 0.0.0.0 --port 5000")
    return result


if __name__ == "__main__":
    r = asyncio.run(main())
