#!/usr/bin/env python3
"""
DreamTalk — Comprehensive Weight Downloader

Downloads ALL required model weights for:
- Voice: Kokoro, GPT-SoVITS, IndicF5, RVC
- Face: LivePortrait, MuseTalk, FLAME, RetinaFace, GFPGAN, Real-ESRGAN
- Brain: SNN models
- Embeddings: BGE-M3

Usage:
    python scripts/download_all_weights.py                    # Download everything
    python scripts/download_all_weights.py --component voice  # Download voice weights only
    python scripts/download_all_weights.py --list             # List current status
    python scripts/download_all_weights.py --check            # Check what's missing
"""

import argparse
import os
import sys
import hashlib
import zipfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import requests
    from tqdm import tqdm
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

ROOT = Path(__file__).resolve().parent.parent
WEIGHTS_DIR = ROOT / "weights"

# ════════════════════════════════════════════════════════════════════════
# WEIGHT REGISTRY — Every model weight needed by DreamTalk
# ════════════════════════════════════════════════════════════════════════

WEIGHTS = [
    # ── Voice: Kokoro TTS ────────────────────────────────────────────
    {
        "component": "voice",
        "name": "Kokoro TTS Model",
        "url": "https://github.com/hexgrad/kokoro/releases/download/v1.0/kokoro-v1_0.pth",
        "dest": "weights/kokoro/kokoro-v1_0.pth",
        "size": "~350 MB",
        "already_present": True,
        "check_file": "weights/kokoro/kokoro-v1_0.pth",
    },

    # ── Voice: GPT-SoVITS (for voice cloning reference) ──────────────
    {
        "component": "voice",
        "name": "GPT-SoVITS T2S Weights (v1)",
        "url": "https://huggingface.co/lj1995/GPT-SoVITS-v2/resolve/main/s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt",
        "dest": "weights/voice/gpt-sovits/s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt",
        "size": "~800 MB",
    },
    {
        "component": "voice",
        "name": "GPT-SoVITS VITS Weights (v1)",
        "url": "https://huggingface.co/lj1995/GPT-SoVITS-v2/resolve/main/s2G488k.pth",
        "dest": "weights/voice/gpt-sovits/s2G488k.pth",
        "size": "~300 MB",
    },

    # ── Voice: IndicF5 (Indian language TTS) ─────────────────────────
    {
        "component": "voice",
        "name": "IndicF5 Model",
        "url": "https://huggingface.co/AI4Bharat/IndicF5/resolve/main/model.safetensors",
        "dest": "weights/voice/indic_tts/IndicF5/model.safetensors",
        "size": "~1.3 GB",
    },
    {
        "component": "voice",
        "name": "IndicF5 Vocab",
        "url": "https://huggingface.co/AI4Bharat/IndicF5/resolve/main/checkpoints/vocab.txt",
        "dest": "weights/voice/indic_tts/IndicF5/checkpoints/vocab.txt",
        "size": "~50 KB",
    },
    {
        "component": "voice",
        "name": "IndicF5 Config",
        "url": "https://huggingface.co/AI4Bharat/IndicF5/resolve/main/config.json",
        "dest": "weights/voice/indic_tts/IndicF5/config.json",
        "size": "~1 KB",
    },

    # ── Face: LivePortrait ───────────────────────────────────────────
    {
        "component": "face",
        "name": "LivePortrait Appearance Feature Extractor",
        "url": "https://huggingface.co/KlingTeam/LivePortrait/resolve/main/liveportrait/base_models/appearance_feature_extractor.pth",
        "dest": "weights/liveportrait/appearance_feature_extractor.pth",
        "size": "~350 MB",
    },
    {
        "component": "face",
        "name": "LivePortrait Motion Extractor",
        "url": "https://huggingface.co/KlingTeam/LivePortrait/resolve/main/liveportrait/base_models/motion_extractor.pth",
        "dest": "weights/liveportrait/motion_extractor.pth",
        "size": "~350 MB",
    },
    {
        "component": "face",
        "name": "LivePortrait SPADE Generator",
        "url": "https://huggingface.co/KlingTeam/LivePortrait/resolve/main/liveportrait/base_models/spade_generator.pth",
        "dest": "weights/liveportrait/spade_generator.pth",
        "size": "~350 MB",
    },
    {
        "component": "face",
        "name": "LivePortrait Warping Module",
        "url": "https://huggingface.co/KlingTeam/LivePortrait/resolve/main/liveportrait/base_models/warping_module.pth",
        "dest": "weights/liveportrait/warping_module.pth",
        "size": "~350 MB",
    },
    {
        "component": "face",
        "name": "LivePortrait Stitching Retargeting",
        "url": "https://huggingface.co/KlingTeam/LivePortrait/resolve/main/liveportrait/retargeting_models/stitching_retargeting_module.pth",
        "dest": "weights/liveportrait/stitching_retargeting_module.pth",
        "size": "~2.3 MB",
        "sha256": "3652d5a3f95099141a56986aaddec92fadf0a73c87a20fac9a2c07c32b28b611",
    },

    # ── Face: MuseTalk ───────────────────────────────────────────────
    {
        "component": "face",
        "name": "MuseTalk UNet",
        "url": "https://huggingface.co/TMElyralab/MuseTalk/resolve/main/musetalk/musetalk.pth",
        "dest": "weights/musetalk/pytorch_model.bin",
        "size": "~1.5 GB",
    },

    # ── Face: RetinaFace Detection ───────────────────────────────────
    {
        "component": "face",
        "name": "RetinaFace MobileNet",
        "url": "https://github.com/biubug6/Pytorch_Retinaface/raw/master/weights/mobilenet0.25_Final.pth",
        "dest": "weights/face/detection/mobilenet0.25_Final.pth",
        "size": "~4 MB",
        "already_present": True,
    },

    # ── Face: restoration and identity-preserving enhancement ───────
    {
        "component": "face",
        "name": "GFPGAN v1.4 Face Restoration",
        "url": "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
        "dest": "weights/face/restoration/GFPGANv1.4.pth",
        "size": "~333 MB",
        "sha256": "e2cd4703ab14f4d01fd1383a8a8b266f9a5833dacee8e6a79d3bf21a1b6be5ad",
    },
    {
        "component": "face",
        "name": "Real-ESRGAN x2plus Background Upscaler",
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
        "dest": "weights/face/restoration/RealESRGAN_x2plus.pth",
        "size": "~64 MB",
        "sha256": "49fafd45f8fd7aa8d31ab2a22d14d91b536c34494a5cfe31eb5d89c2fa266abb",
    },
    {
        "component": "face",
        "name": "facexlib ResNet50 Face Detector",
        "url": "https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth",
        "dest": "weights/face/restoration/detection_Resnet50_Final.pth",
        "size": "~104 MB",
        "sha256": "6d1de9c2944f2ccddca5f5e010ea5ae64a39845a86311af6fdf30841b0a5a16d",
    },
    {
        "component": "face",
        "name": "facexlib ParseNet Face Parser",
        "url": "https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth",
        "dest": "weights/face/restoration/parsing_parsenet.pth",
        "size": "~81 MB",
        "sha256": "3d558d8d0e42c20224f13cf5a29c79eba2d59913419f945545d8cf7b72920de2",
    },

    # ── Brain: SNN Models ────────────────────────────────────────────
    {
        "component": "brain",
        "name": "Brain SNN ResNet CBAM",
        "url": "",
        "dest": "weights/brain/resnet_cbam_mtf_final.h5",
        "size": "~40 MB",
        "already_present": True,
        "note": "Trained model — may need custom training",
    },

    # ── Embeddings: BGE-M3 ──────────────────────────────────────────
    {
        "component": "embeddings",
        "name": "BGE-M3 Sentence Transformer",
        "url": "",
        "dest": "weights/bge-m3/",
        "size": "~2.2 GB",
        "already_present": True,
        "note": "Installed via HuggingFace transformers",
    },
]


def check_status() -> List[Dict]:
    """Check which weights are present, missing, or partial."""
    results = []
    for w in WEIGHTS:
        dest_path = ROOT / w["dest"]
        if w.get("already_present"):
            status = "present" if dest_path.exists() else "missing"
        elif dest_path.is_dir():
            size = sum(f.stat().st_size for f in dest_path.rglob("*") if f.is_file())
            status = "present" if size > 1000 else "partial"
        elif dest_path.exists():
            size = dest_path.stat().st_size
            status = "present" if size > 1000 else "partial"
        else:
            status = "missing"

        actual_sha256 = None
        expected_sha256 = w.get("sha256")
        if status == "present" and expected_sha256 and dest_path.is_file():
            actual_sha256 = _sha256(dest_path)
            if actual_sha256.lower() != expected_sha256.lower():
                status = "corrupt"

        results.append({
            **w,
            "status": status,
            "local_path": str(dest_path),
            "exists": dest_path.exists(),
            "actual_sha256": actual_sha256,
            "checksum_verified": bool(expected_sha256 and actual_sha256 == expected_sha256.lower()),
        })
    return results


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, dest: Path, desc: str = "", expected_sha256: str = ""):
    """Download a file with progress bar."""
    if not HAS_REQUESTS:
        print(f"  [SKIP] requests not installed. Manual download: {url}")
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        print(f"  Downloading: {desc or url}")
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()

        total = int(resp.headers.get("content-length", 0))
        with open(dest, "wb") as f:
            with tqdm(total=total, unit="B", unit_scale=True, desc=desc) as pbar:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    pbar.update(len(chunk))

        if expected_sha256 and _sha256(dest).lower() != expected_sha256.lower():
            dest.unlink(missing_ok=True)
            raise ValueError("downloaded file failed SHA-256 verification")
        print(f"  ✓ Saved: {dest} ({dest.stat().st_size / (1024*1024):.1f} MB)")
        return True

    except Exception as e:
        print(f"  ✗ Failed: {e}")
        if dest.exists():
            dest.unlink()
        return False


def download_weights(component: Optional[str] = None, force: bool = False):
    """Download missing weights."""
    results = check_status()

    to_download = [
        r for r in results
        if r["status"] in {"missing", "partial", "corrupt"} and r.get("url")
    ]
    if component:
        to_download = [r for r in to_download if r["component"] == component]

    if not to_download:
        print("All weights are present!")
        return

    print(f"\n{'='*60}")
    print(f"  Downloading {len(to_download)} missing weight files")
    print(f"{'='*60}\n")

    success = 0
    failed = 0
    for w in to_download:
        dest = ROOT / w["dest"]
        if dest.exists() and not force:
            print(f"  [SKIP] Already exists: {w['dest']}")
            continue

        if not w.get("url"):
            print(f"  [SKIP] No download URL: {w['name']}")
            print(f"         Manual download needed: {w.get('note', '')}")
            continue

        if download_file(w["url"], dest, w["name"], w.get("sha256", "")):
            success += 1
        else:
            failed += 1

    print(f"\n{'='*60}")
    print(f"  Done: {success} downloaded, {failed} failed")
    print(f"{'='*60}")


def print_status():
    """Print current weight status."""
    results = check_status()

    print(f"\n{'='*70}")
    print(f"  DreamTalk Weight Status")
    print(f"{'='*70}\n")

    by_component = {}
    for r in results:
        comp = r["component"]
        if comp not in by_component:
            by_component[comp] = []
        by_component[comp].append(r)

    for comp, items in by_component.items():
        print(f"  [{comp.upper()}]")
        for item in items:
            status_icon = "✓" if item["status"] == "present" else "✗" if item["status"] in {"missing", "corrupt"} else "~"
            print(f"    {status_icon} {item['name']}: {item['size']} ({item['status']})")
        print()

    present = sum(1 for r in results if r["status"] == "present")
    total = len(results)
    print(f"  Summary: {present}/{total} weights present\n")


def main():
    parser = argparse.ArgumentParser(description="DreamTalk Weight Downloader")
    parser.add_argument("--list", action="store_true", help="List current weight status")
    parser.add_argument("--check", action="store_true", help="Check what's missing")
    parser.add_argument("--component", choices=["voice", "face", "brain", "embeddings"],
                        help="Download weights for a specific component")
    parser.add_argument("--force", action="store_true", help="Re-download even if present")
    args = parser.parse_args()

    if args.list or args.check:
        print_status()
    else:
        download_weights(component=args.component, force=args.force)


if __name__ == "__main__":
    main()
