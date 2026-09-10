"""Migrate Ollama models from C: to D: drive and configure environment."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

OLLAMA_SRC = Path("C:/Users/Maharaj/.ollama/models")
OLLAMA_DST = Path("D:/OllamaModels")

print("=" * 60)
print("Ollama Model Migration to D: Drive")
print("=" * 60)

# Step 1: Check source
print(f"\n[1/5] Checking source: {OLLAMA_SRC}")
if not OLLAMA_SRC.exists():
    print(f"  Source not found at {OLLAMA_SRC}")
    print(f"  Checking if OLLAMA_MODELS env var is set...")
    alt = os.environ.get("OLLAMA_MODELS", "")
    if alt:
        print(f"  OLLAMA_MODELS = {alt}")
        OLLAMA_SRC = Path(alt)
    else:
        print("  No OLLAMA_MODELS set either. Models may be elsewhere.")
        # Try the default C drive location
        default = Path.home() / ".ollama" / "models"
        if default.exists():
            OLLAMA_SRC = default
            print(f"  Found at home dir: {OLLAMA_SRC}")
        else:
            print(f"  ERROR: Cannot find ollama models directory!")
            sys.exit(1)

# Calculate source size
total_size = 0
file_count = 0
for f in OLLAMA_SRC.rglob("*"):
    if f.is_file():
        total_size += f.stat().st_size
        file_count += 1
print(f"  Found {file_count} files, {total_size / 1024 / 1024:.1f} MB")

# Step 2: Check D: drive space
print(f"\n[2/5] Checking D: drive...")
if not OLLAMA_DST.parent.exists():
    print(f"  ERROR: D: drive not accessible!")
    print(f"  Available drives: {[str(p) for p in Path('C:/').parent.iterdir() if p.drive]}")
    sys.exit(1)

d_free = shutil.disk_usage(OLLAMA_DST.parent).free
print(f"  D: drive free space: {d_free / 1024 / 1024 / 1024:.1f} GB")
if total_size > d_free:
    print(f"  ERROR: Not enough space on D: drive!")
    sys.exit(1)

# Step 3: Create destination and copy
print(f"\n[3/5] Copying models to {OLLAMA_DST}...")
OLLAMA_DST.mkdir(parents=True, exist_ok=True)

# Use shutil.copytree for the blobs directory
blobs_src = OLLAMA_SRC / "blobs"
blobs_dst = OLLAMA_DST / "blobs"
if blobs_src.exists():
    blobs_dst.mkdir(exist_ok=True)
    for f in blobs_src.iterdir():
        if f.is_file():
            shutil.copy2(f, blobs_dst / f.name)
            print(f"  Copied: {f.name} ({f.stat().st_size / 1024 / 1024:.1f} MB)")

# Copy manifest files
for f in OLLAMA_SRC.iterdir():
    if f.is_file() or (f.is_dir() and f.name != "blobs"):
        if f.is_dir():
            shutil.copytree(f, OLLAMA_DST / f.name, dirs_exist_ok=True)
        else:
            shutil.copy2(f, OLLAMA_DST / f.name)
        print(f"  Copied: {f.name}")

# Step 4: Set environment variable
print(f"\n[4/5] Setting OLLAMA_MODELS environment variable...")
# Use setx for persistent user-level env var
result = subprocess.run(
    ["setx", "OLLAMA_MODELS", str(OLLAMA_DST)],
    capture_output=True, text=True
)
print(f"  setx output: {result.stdout.strip()}")
if result.stderr:
    print(f"  setx errors: {result.stderr.strip()}")

# Also set for current process
os.environ["OLLAMA_MODELS"] = str(OLLAMA_DST)
print(f"  OLLAMA_MODELS = {OLLAMA_DST}")

# Create backup marker
marker = OLLAMA_SRC.parent / "MIGRATED_TO_D_DRIVE.txt"
marker.write_text(f"Migrated to {OLLAMA_DST} on {__import__('datetime').datetime.now()}")
print(f"  Marker created: {marker}")

# Step 5: Verify
print(f"\n[5/5] Verification...")
print(f"  D: drive models: ", end="")
dst_files = list(OLLAMA_DST.rglob("*"))
print(f"{len(dst_files)} items")
print(f"  Source marker: {'EXISTS' if marker.exists() else 'MISSING'}")

print("\n" + "=" * 60)
print("MIGRATION COMPLETE!")
print("=" * 60)
print(f"\nNext steps:")
print(f"  1. Kill Ollama from system tray (right-click → Quit)")
print(f"  2. Launch Ollama again from Start menu")
print(f"  3. Run: ollama list")
print(f"  4. Run: ollama run llama3.1:8b")
print(f"\nOLLAMA_MODELS is now set to: {OLLAMA_DST}")
