"""
DreamTalk - Model Weight Downloader

Downloads all required model weights for DreamTalk's AI pipelines.
Weights are organized into the project's weights/ directory.

Usage:
    python download_weights.py                          # Download all weights
    python download_weights.py --list                   # List current status
    python download_weights.py --component liveportrait # Download specific component
"""

import argparse
import os
import shutil
import sys
import zipfile
from pathlib import Path

try:
    import requests
    from tqdm import tqdm
except ImportError as e:
    print(f"[ERROR] Missing dependency: {e}")
    print()
    print("Please install required packages:")
    print(f"  {sys.executable} -m pip install requests tqdm")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent

WEIGHT_REGISTRY = [
    # ===== Kokoro TTS - ALREADY PRESENT =====
    {
        "component": "kokoro",
        "name": "kokoro-v1_0.pth",
        "url": "https://github.com/hexgrad/kokoro/releases/download/v1.0/kokoro-v1_0.pth",
        "dest": "weights/kokoro/kokoro-v1_0.pth",
        "size": "~350 MB",
        "already_present": True,
    },
    # ===== BGE-M3 Embedding - ALREADY PRESENT =====
    {
        "component": "bge-m3",
        "name": "BGE-M3 Sentence Transformer",
        "url": "",
        "dest": "weights/bge-m3/",
        "size": "~2.2 GB",
        "already_present": True,
    },
    # ===== LivePortrait (Face Animation) =====
    {
        "component": "liveportrait",
        "name": "appearance_feature_extractor.pth",
        "url": "https://huggingface.co/KlingTeam/LivePortrait/resolve/main/liveportrait/base_models/appearance_feature_extractor.pth",
        "dest": "weights/liveportrait/appearance_feature_extractor.pth",
        "size": "~350 MB",
    },
    {
        "component": "liveportrait",
        "name": "motion_extractor.pth",
        "url": "https://huggingface.co/KlingTeam/LivePortrait/resolve/main/liveportrait/base_models/motion_extractor.pth",
        "dest": "weights/liveportrait/motion_extractor.pth",
        "size": "~350 MB",
    },
    {
        "component": "liveportrait",
        "name": "spade_generator.pth",
        "url": "https://huggingface.co/KlingTeam/LivePortrait/resolve/main/liveportrait/base_models/spade_generator.pth",
        "dest": "weights/liveportrait/spade_generator.pth",
        "size": "~350 MB",
    },
    {
        "component": "liveportrait",
        "name": "warping_module.pth",
        "url": "https://huggingface.co/KlingTeam/LivePortrait/resolve/main/liveportrait/base_models/warping_module.pth",
        "dest": "weights/liveportrait/warping_module.pth",
        "size": "~350 MB",
    },
    {
        "component": "liveportrait",
        "name": "landmark.onnx",
        "url": "https://huggingface.co/KlingTeam/LivePortrait/resolve/main/liveportrait/landmark.onnx",
        "dest": "weights/liveportrait/landmark.onnx",
        "size": "~10 MB",
    },
    # ===== MuseTalk (Lip Sync) =====
    {
        "component": "musetalk",
        "name": "musetalk.json",
        "url": "https://huggingface.co/TMElyralab/MuseTalk/resolve/main/musetalk/musetalk.json",
        "dest": "weights/musetalk/musetalk.json",
        "size": "~1 KB",
    },
    {
        "component": "musetalk",
        "name": "pytorch_model.bin",
        "url": "https://huggingface.co/TMElyralab/MuseTalk/resolve/main/musetalk/pytorch_model.bin",
        "dest": "weights/musetalk/pytorch_model.bin",
        "size": "~2.3 GB",
    },
    {
        "component": "musetalk",
        "name": "musetalkV15-unet.pth",
        "url": "https://huggingface.co/TMElyralab/MuseTalk/resolve/main/models/musetalkV15/unet.pth",
        "dest": "weights/musetalk/unet.pth",
        "size": "~2.3 GB",
    },
    {
        "component": "musetalk",
        "name": "sd-vae-ft-mse",
        "url": "https://huggingface.co/stabilityai/sd-vae-ft-mse/resolve/main/diffusion_pytorch_model.bin",
        "dest": "weights/musetalk/sd-vae/diffusion_pytorch_model.bin",
        "size": "~350 MB",
    },
    {
        "component": "musetalk",
        "name": "whisper-tiny",
        "url": "https://huggingface.co/openai/whisper-tiny/resolve/main/pytorch_model.bin",
        "dest": "weights/musetalk/whisper/pytorch_model.bin",
        "size": "~150 MB",
    },
    # ===== FLAME 3D Face Model =====
    # The FLAMEModel class loads a pickle with keys: v_template, shapedirs, f, J_regressor, etc.
    # Backend endpoint uses "FLAME2020.pkl", so we download FLAME_MALE.pkl as FLAME2020.pkl
    {
        "component": "flame",
        "name": "FLAME2020.pkl (FLAME_MALE.pkl)",
        "url": "https://huggingface.co/camenduru/show/resolve/main/data/flame/FLAME_MALE.pkl",
        "dest": "weights/flame/FLAME2020.pkl",
        "size": "~53 MB",
    },
    {
        "component": "flame",
        "name": "FLAME_masks.pkl",
        "url": "https://huggingface.co/bEijuuu/Portrait4D/resolve/main/models/FLAME/mask/FLAME_masks.pkl",
        "dest": "weights/flame/FLAME_masks.pkl",
        "size": "~96 KB",
    },
    {
        "component": "flame",
        "name": "FLAME_texture.npz",
        "url": "https://huggingface.co/camenduru/show/resolve/main/data/flame/FLAME_texture.npz",
        "dest": "weights/flame/FLAME_texture.npz",
        "size": "~1.26 GB",
    },
    # ===== RetinaFace (Face Detection) =====
    {
        "component": "retinaface",
        "name": "RetinaFace-R50.pth",
        "url": "https://huggingface.co/camenduru/video-retalking/resolve/main/RetinaFace-R50.pth",
        "dest": "weights/retinaface/RetinaFace-R50.pth",
        "size": "~180 MB",
    },
    # ===== BiSeNet (Face Parsing) =====
    # Required by MuseTalk face parsing pipeline
    {
        "component": "retinaface",
        "name": "79999_iter.pth (BiSeNet Face Parsing)",
        "url": "https://huggingface.co/vivym/face-parsing-bisenet/resolve/main/79999_iter.pth",
        "dest": "weights/retinaface/79999_iter.pth",
        "size": "~53 MB",
    },
    # ===== PFLD (Landmark Detection) =====
    {
        "component": "flame",
        "name": "pfld_model.pth (from py-feat/pfld)",
        "url": "https://huggingface.co/py-feat/pfld/resolve/main/pfld_model_best.pth.tar",
        "dest": "weights/flame/pfld_model.pth",
        "size": "~9 MB",
    },
    # ===== RVC (Retrieval-based Voice Conversion) =====
    {
        "component": "rvc",
        "name": "hubert_base.pt (content encoder)",
        "url": "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/hubert_base.pt",
        "dest": "weights/voice/rvc/hubert_base.pt",
        "size": "~390 MB",
    },
    {
        "component": "rvc",
        "name": "rmvpe.pt (pitch extraction)",
        "url": "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/rmvpe.pt",
        "dest": "weights/voice/rvc/rmvpe.pt",
        "size": "~60 MB",
    },
    {
        "component": "rvc",
        "name": "f0G48k.pth (v2 generator 48kHz)",
        "url": "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/pretrained_v2/f0G48k.pth",
        "dest": "weights/voice/rvc/pretrained_v2/f0G48k.pth",
        "size": "~50 MB",
    },
    {
        "component": "rvc",
        "name": "f0D48k.pth (v2 discriminator 48kHz)",
        "url": "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/pretrained_v2/f0D48k.pth",
        "dest": "weights/voice/rvc/pretrained_v2/f0D48k.pth",
        "size": "~50 MB",
    },
    {
        "component": "rvc",
        "name": "f0G40k.pth (v2 generator 40kHz)",
        "url": "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/pretrained_v2/f0G40k.pth",
        "dest": "weights/voice/rvc/pretrained_v2/f0G40k.pth",
        "size": "~50 MB",
    },
    {
        "component": "rvc",
        "name": "f0D40k.pth (v2 discriminator 40kHz)",
        "url": "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/pretrained_v2/f0D40k.pth",
        "dest": "weights/voice/rvc/pretrained_v2/f0D40k.pth",
        "size": "~50 MB",
    },
]


def get_directory_size(path):
    """Calculate total size of all files in a directory."""
    total_bytes = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total_bytes


def check_weight(entry):
    dest_path = ROOT / entry["dest"]
    if dest_path.exists():
        if dest_path.is_dir():
            total_bytes = get_directory_size(dest_path)
            file_count = sum(1 for _ in dest_path.rglob("*") if _.is_file())
            if total_bytes > 0:
                size_mb = total_bytes / (1024 * 1024)
                return f"[OK] ({size_mb:.0f} MB across {file_count} files)"
            else:
                return "[MISS] (empty directory)"
        else:
            size_mb = dest_path.stat().st_size / (1024 * 1024)
            if size_mb > 0:
                return f"[OK] ({size_mb:.0f} MB)"
            else:
                dest_path.unlink()  # Remove empty file
                return "[MISS]"
    return "[MISS]"


def list_weights():
    print("=" * 70)
    print("  DreamTalk Model Weight Status")
    print("=" * 70)

    by_component = {}
    for entry in WEIGHT_REGISTRY:
        by_component.setdefault(entry["component"], []).append(entry)

    present_count = 0
    missing_count = 0

    for component in sorted(by_component.keys()):
        entries = by_component[component]
        print(f"\n  [{component.upper()}]:")
        for entry in entries:
            status = check_weight(entry)
            print(f"    {status}  {entry['name']:50s}  ({entry.get('size', '?')})")
            if status.startswith("[OK]"):
                present_count += 1
            else:
                missing_count += 1

    total = present_count + missing_count
    print(f"\n{'='*70}")
    if total > 0:
        pct = present_count * 100 // total
        print(f"  Summary: {present_count}/{total} files present ({pct}%)")
    print(f"  Missing: {missing_count} file(s) to download")
    print(f"{'='*70}\n")


def download_file(url, dest, desc="", timeout=30):
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest.with_suffix(dest.suffix + ".download")

    try:
        response = requests.get(
            url, stream=True, timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        block_size = 1024 * 1024  # 1 MB chunks

        with tqdm(total=total_size, unit="B", unit_scale=True, desc=desc or dest.name, ncols=80) as pbar:
            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

        temp_path.rename(dest)
        return True
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        print(f"  [FAIL] {e}")
        return False


def download_component(component):
    entries = [e for e in WEIGHT_REGISTRY if e["component"] == component]
    if not entries:
        print(f"  Unknown component: {component}")
        return

    print(f"\n{'='*50}")
    print(f"  Downloading {component.upper()} weights...")
    print(f"{'='*50}")

    all_success = True
    for entry in entries:
        if entry.get("already_present"):
            print(f"  [OK] {entry['name']} - already present, skipping")
            continue
        if not entry.get("url"):
            url_hint = entry.get("manual_url", "")
            note = entry.get("manual_note", "")
            print(f"  [--] {entry['name']} - manual download required")
            if url_hint:
                print(f"        Download from: {url_hint}")
            if note:
                print(f"        Note: {note}")
            print(f"        Place at: {entry['dest']}")
            continue

        dest = ROOT / entry["dest"]
        if dest.exists():
            if dest.is_dir():
                dir_size = get_directory_size(dest)
                if dir_size > 0:
                    mb = dir_size / (1024 * 1024)
                    print(f"  [OK] {entry['name']} - already exists ({mb:.0f} MB in {sum(1 for _ in dest.rglob('*') if _.is_file())} files)")
                    continue
            else:
                mb = dest.stat().st_size / (1024 * 1024)
                if mb > 0:
                    print(f"  [OK] {entry['name']} - already exists ({mb:.0f} MB)")
                    continue
                else:
                    dest.unlink()

        print(f"  [>>] Downloading {entry['name']} ({entry.get('size', '?')})...")
        success = download_file(entry["url"], dest, desc=entry["name"])

        if success and entry.get("is_zip"):
            try:
                extract_dir = dest.parent / "extracted"
                with zipfile.ZipFile(dest, "r") as zf:
                    zf.extractall(extract_dir)
                print(f"  [OK] Extracted to {extract_dir}")
                for f in extract_dir.rglob("*.pth"):
                    shutil.move(str(f), str(dest.parent / f.name))
                shutil.rmtree(extract_dir)
                dest.unlink()
            except Exception as e:
                print(f"  [WARN] Extraction: {e}")

        if not success:
            all_success = False

    if all_success:
        print(f"  [OK] {component.upper()} done!")
    else:
        print(f"  [DONE] {component.upper()} - some files had issues")
    print()


def download_all():
    components = sorted(set(e["component"] for e in WEIGHT_REGISTRY))
    for component in components:
        download_component(component)

    print(f"\n{'='*50}")
    print(f"  ALL DOWNLOADS COMPLETE!")
    print(f"{'='*50}")
    list_weights()


def main():
    parser = argparse.ArgumentParser(description="DreamTalk Model Weight Downloader")
    parser.add_argument("--list", "-l", action="store_true", help="List current status")
    parser.add_argument("--component", "-c", type=str, default="all",
                        help="Component: kokoro, bge-m3, liveportrait, musetalk, flame, retinaface")
    parser.add_argument("--force", "-f", action="store_true", help="Re-download existing")

    args = parser.parse_args()

    if args.list:
        list_weights()
        return

    if args.force:
        for entry in WEIGHT_REGISTRY:
            entry["already_present"] = False

    if args.component == "all":
        download_all()
    else:
        download_component(args.component)

    print("Tip: After downloading, verify with: python run_pipeline_test.py")


if __name__ == "__main__":
    main()
