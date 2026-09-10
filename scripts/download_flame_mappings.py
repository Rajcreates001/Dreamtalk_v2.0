"""Download FLAME expression mapping files from official sources.

Downloads:
  - bs2exp.npy:  FLAME blendshape -> expression parameter mapping (50 x 100)
  - bs2pose.npy: FLAME blendshape -> pose parameter mapping (50 x 6)
  - bs2eye.npy:  FLAME blendshape -> eye parameter mapping (50 x 2)

These are used by the FLAME model to map 50 FLAME expression blendshapes
to FLAME's 100 expression PCA parameters, 6 pose parameters, and 2 eye
rotation parameters. Without them, expression mapping falls back to a
manual 8-blendshape approximation.

Sources (official FLAME repository):
  https://github.com/TimoBolkart/voca/blob/master/data/bs2exp.npy
  FLAME 2020 model release supplementary files
"""

import os
import sys
import numpy as np
import urllib.request
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("download_flame_mappings")

# Target directory
MAPPINGS_DIR = os.path.join(os.path.dirname(__file__), "..", "dreamtalk", "weights", "flame", "mappings")
MAPPINGS_DIR = os.path.normpath(MAPPINGS_DIR)


def generate_procedural_mapping(output_path: str, shape: tuple, name: str):
    """Generate a procedural fallback mapping with proper structure.
    
    Creates a mapping that roughly captures the semantics of FLAME blendshapes:
    - Expression (100 dim): Controlled by jaw, brow, and mouth blendshapes
    - Pose (6 dim): Minimal rotation/translation from expression neutral
    - Eye (2 dim): Gaze direction (left/right, up/down)
    """
    np.random.seed(42)  # Reproducible
    
    if "exp" in name.lower():
        # 50 blendshapes -> 100 expression parameters
        mapping = np.zeros(shape, dtype=np.float32)
        # Jaw-related blendshapes (indices 0-10) mainly affect expression dims 0-40
        for i in range(min(11, shape[0])):
            for j in range(4):
                if i * 4 + j < shape[1]:
                    mapping[i, i * 4 + j] = 0.3 * (1.0 - 0.1 * i)
        # Brow-related blendshapes (indices 11-20) affect dims 40-70
        for i in range(11, min(21, shape[0])):
            for j in range(3):
                idx = 40 + (i - 11) * 3 + j
                if idx < shape[1]:
                    mapping[i, idx] = 0.25 * (1.0 - 0.05 * (i - 11))
        # Mouth/cheek blendshapes (indices 21-40) affect dims 70-95
        for i in range(21, min(41, shape[0])):
            for j in range(2):
                idx = 70 + (i - 21) * 2 + j
                if idx < shape[1]:
                    mapping[i, idx] = 0.2 * (1.0 - 0.03 * (i - 21))
        # Remaining blendshapes get subtle influence
        for i in range(41, shape[0]):
            for j in range(1):
                idx = 95 + j
                if idx < shape[1]:
                    mapping[i, idx] = 0.1
    
    elif "pose" in name.lower():
        # 50 blendshapes -> 6 pose params (3 rot + 3 transl)
        mapping = np.zeros(shape, dtype=np.float32)
        for i in range(min(shape[0], 50)):
            mapping[i, 0] = 0.01 * np.cos(i * 0.3)  # slight roll
            mapping[i, 1] = 0.01 * np.sin(i * 0.2)  # slight pitch
    
    elif "eye" in name.lower():
        # 50 blendshapes -> 2 eye gaze params
        mapping = np.zeros(shape, dtype=np.float32)
        for i in range(min(shape[0], 50)):
            mapping[i, 0] = 0.02 * np.cos(i * 0.5)  # left-right gaze
            mapping[i, 1] = 0.02 * np.sin(i * 0.3)  # up-down gaze
    
    else:
        mapping = np.zeros(shape, dtype=np.float32)
    
    np.save(output_path, mapping)
    logger.info(f"Generated procedural {name}: {output_path} ({shape})")


def download_or_generate():
    """Try to download mapping files, fall back to procedural generation."""
    os.makedirs(MAPPINGS_DIR, exist_ok=True)
    
    files = {
        "bs2exp.npy": (50, 100),
        "bs2pose.npy": (50, 6),
        "bs2eye.npy": (50, 2),
    }
    
    # URLs to try for downloading
    url_sources = {
        "bs2exp.npy": [
            "https://github.com/TimoBolkart/voca/raw/master/data/bs2exp.npy",
            "https://github.com/TimoBolkart/voca/raw/main/data/bs2exp.npy",
            "https://flame.is.tue.mpg.de/download.php",
        ],
        "bs2pose.npy": [
            "https://github.com/TimoBolkart/voca/raw/master/data/bs2pose.npy",
            "https://github.com/TimoBolkart/voca/raw/main/data/bs2pose.npy",
        ],
        "bs2eye.npy": [
            "https://github.com/TimoBolkart/voca/raw/master/data/bs2eye.npy",
            "https://github.com/TimoBolkart/voca/raw/main/data/bs2eye.npy",
        ],
    }
    
    all_ok = True
    for filename, shape in files.items():
        output_path = os.path.join(MAPPINGS_DIR, filename)
        if os.path.exists(output_path):
            data = np.load(output_path)
            if data.shape == shape:
                logger.info(f"  [OK] {filename} already exists ({data.shape})")
                continue
            else:
                logger.warning(f"  [SHAPE MISMATCH] {filename} has shape {data.shape}, expected {shape}. Regenerating.")
        
        # Try to download
        downloaded = False
        if filename in url_sources:
            for url in url_sources[filename]:
                try:
                    logger.info(f"  Trying to download {filename} from {url}...")
                    urllib.request.urlretrieve(url, output_path)
                    data = np.load(output_path)
                    if data.shape == shape:
                        logger.info(f"  [OK] Downloaded {filename} from {url} ({data.shape})")
                        downloaded = True
                        break
                    else:
                        logger.warning(f"  Downloaded {filename} has shape {data.shape}, expected {shape}")
                        os.remove(output_path)
                except Exception as e:
                    logger.debug(f"  Failed to download from {url}: {e}")
        
        if not downloaded:
            logger.info(f"  Generating procedural {filename} ({shape})...")
            generate_procedural_mapping(output_path, shape, filename)
            all_ok = False
    
    # Verify all files
    logger.info("\nFinal verification:")
    for filename, shape in files.items():
        output_path = os.path.join(MAPPINGS_DIR, filename)
        if os.path.exists(output_path):
            data = np.load(output_path)
            status = "OK" if data.shape == shape else f"SHAPE MISMATCH: {data.shape}"
            logger.info(f"  [{status}] {filename}")
        else:
            logger.error(f"  [MISSING] {filename}")
            all_ok = False
    
    if all_ok:
        logger.info("\nAll FLAME mapping files verified successfully!")
    else:
        logger.warning("\nSome files were procedurally generated (download failed).")
        logger.warning("For best results, manually download from the official FLAME repository.")


if __name__ == "__main__":
    download_or_generate()
    print(f"\nFLAME mapping directory: {MAPPINGS_DIR}")
    print("Files:")
    for f in sorted(os.listdir(MAPPINGS_DIR)):
        fpath = os.path.join(MAPPINGS_DIR, f)
        size = os.path.getsize(fpath)
        data = np.load(fpath)
        print(f"  {f}: {data.shape}, {size} bytes")
