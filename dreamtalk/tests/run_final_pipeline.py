"""Run final pipeline, generate script, and copy assets."""
import asyncio
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


async def main():
    # Step 1: Run pipeline
    print("=== STEP 1: Pipeline ===")
    from dreamtalk.pipeline.orchestrator import PipelineOrchestrator
    from dreamtalk.pipeline.models import PipelineRequest

    img_dir = ROOT / "local_upload_testing" / "image"
    voice_dir = ROOT / "local_upload_testing" / "voice"
    images = sorted(
        [
            f
            for f in img_dir.rglob("*")
            if f.suffix.lower() in (".jpg", ".jpeg", ".png")
            and "diagnostic" not in f.name.lower()
            and "haar" not in f.name.lower()
        ]
    )
    voices = sorted(
        [
            f
            for f in voice_dir.rglob("*")
            if f.suffix.lower() in (".wav", ".mp3")
        ]
    )

    print(f"Image: {images[0].name if images else 'NONE'}")
    print(f"Voice: {voices[0].name if voices else 'NONE'}")

    orch = PipelineOrchestrator()
    req = PipelineRequest(
        twin_id="avatar_final",
        role="normal_user",
        image_paths=[str(images[0])] if images else [],
        voice_paths=[str(voices[0])] if voices else [],
        text_input="Hello! I am your Digital Twin.",
        enable_3d_face=True,
        enable_voice_clone=True,
        enable_emotion=True,
        enable_decision=True,
        enable_object_detection=False,
        model_name="rule_based",
    )
    result = await orch.run_full_pipeline(req)
    print(f"Status: {result.status.value}")
    print(
        f"Face: detected={result.face_result.face_detected if result.face_result else False}"
    )
    print(
        f"Voice: detected={result.voice_result.voice_detected if result.voice_result else False}"
    )

    # Copy to static
    static_dir = ROOT / "dreamtalk" / "avatar" / "static"
    os.makedirs(static_dir, exist_ok=True)

    if (
        result.face_result
        and result.face_result.mesh_3d_path
        and os.path.exists(result.face_result.mesh_3d_path)
    ):
        shutil.copy2(result.face_result.mesh_3d_path, static_dir / "current_mesh.obj")
        print(
            f"Copied mesh ({os.path.getsize(result.face_result.mesh_3d_path)} bytes)"
        )

    if (
        result.face_result
        and result.face_result.texture_path
        and os.path.exists(result.face_result.texture_path)
    ):
        shutil.copy2(
            result.face_result.texture_path, static_dir / "current_texture.jpg"
        )
        (static_dir / "face_texture.mtl").write_text(
            "newmtl face_texture\nKa 1.0 1.0 1.0\nKd 1.0 1.0 1.0\nKs 0.0 0.0 0.0\nmap_Kd current_texture.jpg\n"
        )
        print(
            f"Copied texture ({os.path.getsize(result.face_result.texture_path)} bytes)"
        )

    if (
        result.voice_result
        and result.voice_result.cloned_voice_path
        and os.path.exists(result.voice_result.cloned_voice_path)
    ):
        shutil.copy2(
            result.voice_result.cloned_voice_path, static_dir / "cloned_voice.wav"
        )
        print(
            f"Copied voice ({os.path.getsize(result.voice_result.cloned_voice_path)} bytes)"
        )

    print()

    # Step 2: Generate 3-minute script
    print("=== STEP 2: 3-Min Script ===")
    import edge_tts

    script_path = ROOT / "scripts" / "long_script.txt"
    script = script_path.read_text()
    print(f"Script: {len(script)} chars")

    full_path = static_dir / "script_3min.wav"
    c = edge_tts.Communicate(script, "en-US-JennyNeural")
    await c.save(str(full_path))
    s = os.path.getsize(full_path)
    seconds = s / 32000
    print(f"Script: {s} bytes = {seconds:.0f}s = {seconds/60:.1f} min")

    paragraphs = [p.strip() for p in script.split("\n\n") if p.strip()]
    parts_dir = static_dir / "script_parts"
    os.makedirs(parts_dir, exist_ok=True)
    for i, para in enumerate(paragraphs):
        pp = parts_dir / f"part_{i:02d}.wav"
        await edge_tts.Communicate(para, "en-US-JennyNeural").save(str(pp))

    meta = {
        "total_parts": len(paragraphs),
        "script_path": str(full_path),
        "total_chars": len(script),
    }
    json.dump(meta, open(static_dir / "script_meta.json", "w"))
    print(f"Split into {len(paragraphs)} parts")

    # Final verification
    print()
    print("=== FINAL STATIC FILES ===")
    for f in sorted(static_dir.iterdir()):
        if f.is_file():
            print(f"  {f.name}: {f.stat().st_size} bytes")
    print()
    print("=== ALL DONE ===")


if __name__ == "__main__":
    asyncio.run(main())
