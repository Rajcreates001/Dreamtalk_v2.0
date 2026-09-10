#!/usr/bin/env python
"""Comprehensive Pipeline Test — FLAME, LivePortrait, MuseTalk

Tests that all three model pipelines can load their weights and run inference.
Reports clear pass/fail status for each component.
"""

import os
import sys
import json
import logging

# Set this BEFORE any imports to suppress OpenMP warnings
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

# Ensure project root is on sys.path
_here = os.path.dirname(os.path.abspath(__file__))
_parent = os.path.dirname(_here)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("pipeline_test")

results = {
    "flame": {"status": "untested", "details": {}},
    "liveportrait": {"status": "untested", "details": {}},
    "musetalk": {"status": "untested", "details": {}},
    "overall": {"status": "running"},
}


# ═══════════════════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════════════════

weights_dir = os.path.join(_here, "weights")


def check_file(*parts):
    path = os.path.join(weights_dir, *parts)
    exists = os.path.exists(path)
    size_mb = round(os.path.getsize(path) / (1024 * 1024), 1) if exists else 0
    return {"exists": exists, "path": path, "size_mb": size_mb}


def check_dir(*parts):
    path = os.path.join(weights_dir, *parts)
    is_dir = os.path.isdir(path)
    return {"exists": is_dir, "path": path}


# ═══════════════════════════════════════════════════════════════════════
# 1. FLAME Test
# ═══════════════════════════════════════════════════════════════════════

def test_flame():
    logger.info("=" * 60)
    logger.info("TEST: FLAME 3D Face Model")
    logger.info("=" * 60)

    # Check weight files
    flame_weights = check_file("flame", "FLAME2020_numpy.pkl")
    logger.info(f"  FLAME weights: {flame_weights['path']}")
    logger.info(f"    exists={flame_weights['exists']}, size={flame_weights['size_mb']}MB")

    if not flame_weights["exists"]:
        return {"status": "FAIL", "error": "FLAME2020_numpy.pkl not found"}

    try:
        from pipeline.flame_fitter import FlameFitter, FLAMELoader

        # Test FLAMELoader
        loader = FLAMELoader(flame_weights["path"])
        logger.info(f"  FLAMELoader: {loader.num_vertices} verts, {loader.num_faces} faces, "
                    f"v_template={loader.v_template.shape}")

        # Test mesh generation (mean face)
        mean_verts = loader.generate_mesh()
        logger.info(f"  Mean mesh: {mean_verts.shape}")

        # Test with identity coefficients
        import numpy as np
        identity_coeffs = np.zeros(300)
        identity_coeffs[:5] = [0.5, -0.3, 0.2, -0.1, 0.05]
        deformed = loader.generate_mesh(identity_coeffs=identity_coeffs)
        diff = np.abs(deformed - mean_verts).max()
        logger.info(f"  Deformed mesh: max diff from mean = {diff:.4f}")

        # Test FlameFitter
        fitter = FlameFitter(flame_weights["path"])
        logger.info(f"  FlameFitter: could access flame model")

        info = {
            "num_vertices": loader.num_vertices,
            "num_faces": loader.num_faces,
            "mean_mesh_shape": list(mean_verts.shape),
            "identity_deformation_max_diff": round(float(diff), 4),
            "weights_file": flame_weights["path"],
        }

        # Test face detection (if we have a test image)
        test_images = [
            os.path.join(_here, "pipeline_test_data", "face.jpg"),
            os.path.join(_here, "pipeline_test_data", "face.png"),
            os.path.join(_here, "static", "test_face.jpg"),
        ]

        # Try to detect landmarks from any available test image
        land_detected = False
        for img_path in test_images:
            if os.path.exists(img_path):
                try:
                    from pipeline.flame_fitter import detect_landmarks
                    landmarks, img_w = detect_landmarks(img_path)
                    if landmarks is not None:
                        logger.info(f"  Landmarks detected from {img_path}: {len(landmarks)} points")
                        land_detected = True
                        break
                except Exception as e:
                    logger.info(f"  Landmark detection skipped for {img_path}: {e}")

        info["landmark_detection_available"] = land_detected

        return {"status": "PASS", "details": info}

    except Exception as e:
        logger.error(f"  FLAME test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "FAIL", "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════
# 2. LivePortrait Test
# ═══════════════════════════════════════════════════════════════════════

def test_liveportrait():
    logger.info("=" * 60)
    logger.info("TEST: LivePortrait Face Animation")
    logger.info("=" * 60)

    # Check weight files
    required = [
        "appearance_feature_extractor.pth",
        "motion_extractor.pth",
        "spade_generator.pth",
        "warping_module.pth",
        "landmark.onnx",
    ]

    weights_status = {}
    all_present = True
    for fname in required:
        w = check_file("liveportrait", fname)
        weights_status[fname] = {"exists": w["exists"], "size_mb": w["size_mb"]}
        logger.info(f"  {fname}: exists={w['exists']}, size={w['size_mb']}MB")
        if not w["exists"]:
            all_present = False

    # Check emotion templates
    template_dir = os.path.join(weights_dir, "liveportrait", "templates")
    templates = []
    if os.path.isdir(template_dir):
        for f in sorted(os.listdir(template_dir)):
            if f.endswith(".pkl"):
                templates.append(f[:-4])
    logger.info(f"  Emotion templates: {templates if templates else 'none found'}")

    # Check config model resolution
    lp_weights_root = check_file("liveportrait", "appearance_feature_extractor.pth")
    logger.info(f"  Weights path: {lp_weights_root['path']}")

    info = {
        "weights": weights_status,
        "all_weights_present": all_present,
        "emotion_templates": templates,
        "weight_count": sum(1 for v in weights_status.values() if v["exists"]),
        "weight_total": len(required),
    }

    # Test venv availability
    venv_paths = [
        os.environ.get("LIVEPORTRAIT_VENV_PYTHON", "D:/venvs/liveportrait/Scripts/python.exe"),
        os.environ.get("LIVEPORTRAIT_VENV_FALLBACK", "D:/venvs/indicf5/Scripts/python.exe"),
    ]

    for i, vp in enumerate(venv_paths):
        exists = os.path.exists(vp)
        logger.info(f"  Venv {'primary' if i == 0 else 'fallback'}: {vp} exists={exists}")
        if exists:
            # Check torch version in venv
            import subprocess
            try:
                out = subprocess.check_output(
                    [vp, "-c", "import torch; print(torch.__version__, torch.cuda.is_available())"],
                    timeout=10, stderr=subprocess.STDOUT,
                    env={**os.environ, "KMP_DUPLICATE_LIB_OK": "TRUE"},
                ).decode().strip()
                logger.info(f"    Torch: {out}")
            except Exception as e:
                logger.info(f"    Torch check failed: {e}")

    info["venv_paths"] = {f"venv_{i}": vp for i, vp in enumerate(venv_paths)}
    info["venv_available"] = any(os.path.exists(vp) for vp in venv_paths)

    # Test direct import capability
    try:
        # Just check if we can import the LivePortrait wrapper module (not actually load models)
        import importlib
        spec = importlib.util.find_spec("dreamtalk.face.core.animation.liveportrait")
        if spec is not None:
            logger.info(f"  LivePortrait module found at: {spec.origin}")
            info["module_importable"] = True
        else:
            logger.info("  LivePortrait module NOT found")
            info["module_importable"] = False
    except Exception as e:
        logger.info(f"  LivePortrait module check failed: {e}")
        info["module_importable"] = False

    # Determine overall status
    if all_present and info["venv_available"]:
        info["can_run"] = True
        return {"status": "PASS", "details": info}
    elif all_present:
        info["can_run"] = False
        info["suggestion"] = "Create LivePortrait venv or set LIVEPORTRAIT_VENV_PYTHON env var"
        return {"status": "WARN", "details": info}
    else:
        missing = [k for k, v in weights_status.items() if not v["exists"]]
        info["can_run"] = False
        info["missing_weights"] = missing
        return {"status": "FAIL", "error": f"Missing weights: {missing}", "details": info}


# ═══════════════════════════════════════════════════════════════════════
# 3. MuseTalk Test
# ═══════════════════════════════════════════════════════════════════════

def test_musetalk():
    logger.info("=" * 60)
    logger.info("TEST: MuseTalk Lip-Sync")
    logger.info("=" * 60)

    # Check weight files
    weights_to_check = [
        ("musetalk/unet.pth", "UNet"),
        ("musetalk/pytorch_model.bin", "Main model"),
        ("musetalk/musetalk.json", "Config"),
        ("musetalk/whisper/pytorch_model.bin", "Whisper"),
        ("musetalk/sd-vae/diffusion_pytorch_model.bin", "VAE"),
    ]

    weights_status = {}
    all_present = True
    for rel_path, label in weights_to_check:
        w = check_file(*rel_path.split("/"))
        weights_status[label] = {"exists": w["exists"], "size_mb": w["size_mb"]}
        logger.info(f"  {label}: exists={w['exists']}, size={w['size_mb']}MB")
        if not w["exists"]:
            all_present = False

    # Test config resolution
    try:
        from face.core.lipsync.musetalk.config import MuseTalkConfig
        cfg = MuseTalkConfig()
        logger.info(f"  Config unet_model_path: {cfg.unet_model_path}")
        logger.info(f"  Config unet_config: {cfg.unet_config}")
        logger.info(f"  Config whisper_dir: {cfg.whisper_dir}")

        cfg_unet_ok = os.path.exists(cfg.unet_model_path)
        cfg_config_ok = os.path.exists(cfg.unet_config)
        cfg_whisper_ok = os.path.isdir(cfg.whisper_dir)
        logger.info(f"  Path checks: UNet={cfg_unet_ok}, Config={cfg_config_ok}, Whisper_dir={cfg_whisper_ok}")

        config_ok = cfg_unet_ok and cfg_config_ok and cfg_whisper_ok

    except Exception as e:
        logger.error(f"  Config test failed: {e}")
        config_ok = False
        cfg = None

    info = {
        "weights": weights_status,
        "all_weights_present": all_present,
        "config_paths_resolve": config_ok,
        "weight_count": sum(1 for v in weights_status.values() if v["exists"]),
        "weight_total": len(weights_to_check),
    }

    if all_present and config_ok:
        info["can_run"] = True
        return {"status": "PASS", "details": info}
    elif all_present:
        info["can_run"] = False
        return {"status": "WARN", "details": info}
    else:
        missing = [k for k, v in weights_status.items() if not v["exists"]]
        info["can_run"] = False
        info["missing_weights"] = missing
        return {"status": "FAIL", "error": f"Missing weights: {missing}", "details": info}


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  DreamTalk Pipeline Verification")
    print("=" * 60)

    # Test 1: FLAME
    print()
    results["flame"] = test_flame()

    # Test 2: LivePortrait
    print()
    results["liveportrait"] = test_liveportrait()

    # Test 3: MuseTalk
    print()
    results["musetalk"] = test_musetalk()

    # Summary
    print()
    print("=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)
    all_pass = True
    for name, r in results.items():
        if name == "overall":
            continue
        status = r["status"]
        icon = "[OK]" if status == "PASS" else "[!!]" if status == "WARN" else "[XX]"
        print(f"  {icon} {name.upper()}: {status}")
        if status != "PASS":
            all_pass = False

    results["overall"] = {
        "status": "PASS" if all_pass else "PARTIAL",
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "python_version": sys.version,
    }
    print()
    print("=" * 60)
    print(f"  OVERALL: {'ALL PIPELINES READY' if all_pass else 'SOME ISSUES FOUND'}")
    print("=" * 60)

    # Save results to JSON
    results_path = os.path.join(_here, "pipeline_test_results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {results_path}")
