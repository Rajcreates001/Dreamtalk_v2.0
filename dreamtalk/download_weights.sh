#!/usr/bin/env bash
# 🎯 DreamTalk — Model Weight Downloader (Bash)
#
# Downloads model weights for DreamTalk's AI pipelines.
# Usage:
#   bash download_weights.sh              # Download all missing weights
#   bash download_weights.sh --list       # Show weight status
#   bash download_weights.sh liveportrait # Download specific component
#
# Components: kokoro, bge-m3, liveportrait, musetalk, flame, retinaface

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
WEIGHTS_DIR="$ROOT/weights"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}   $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERR]${NC}  $1"; }

download_file() {
    local url="$1"
    local dest="$2"
    local desc="${3:-$(basename "$dest")}"

    mkdir -p "$(dirname "$dest")"

    if [ -f "$dest" ]; then
        local size_mb
        size_mb=$(du -h "$dest" 2>/dev/null | cut -f1)
        ok "$desc — already exists ($size_mb)"
        return 0
    fi

    info "Downloading $desc..."
    if command -v wget &>/dev/null; then
        wget -q --show-progress "$url" -O "$dest" || {
            err "Failed to download $desc"
            return 1
        }
    elif command -v curl &>/dev/null; then
        curl -#L "$url" -o "$dest" || {
            err "Failed to download $desc"
            return 1
        }
    else
        err "Neither wget nor curl found. Install one and retry."
        return 1
    fi

    local size_mb
    size_mb=$(du -h "$dest" 2>/dev/null | cut -f1)
    ok "Downloaded $desc ($size_mb)"
}

check_weight() {
    local dest="$1"
    local name="$2"

    if [ -f "$dest" ]; then
        local size_mb
        size_mb=$(du -h "$dest" 2>/dev/null | cut -f1)
        echo -e "${GREEN}✅ PRESENT${NC} ($size_mb)  $name"
        return 0
    else
        echo -e "${RED}❌ MISSING${NC}           $name"
        return 1
    fi
}

list_weights() {
    echo ""
    echo "=========================================="
    echo "  DreamTalk Model Weight Status"
    echo "=========================================="

    local total=0
    local present=0

    while IFS='|' read -r component name url dest size; do
        [[ "$component" =~ ^#.* ]] && continue
        [ -z "$component" ] && continue

        check_weight "$ROOT/$dest" "$name"
        total=$((total + 1))
        if [ -f "$ROOT/$dest" ]; then
            present=$((present + 1))
        fi
    done < <(sed -n '/^# WEIGHT_REGISTRY_START/,/^# WEIGHT_REGISTRY_END/p' "$0" | grep -v "^#" | grep "|")

    echo ""
    echo "=========================================="
    echo "  Summary: $present/$total files present"
    if [ $total -gt 0 ]; then
        echo "  Progress: $((present * 100 / total))%"
    fi
    echo "=========================================="
    echo ""
}

download_component() {
    local target="$1"

    echo ""
    echo "=========================================="
    echo "  Downloading $target weights..."
    echo "=========================================="

    local found=0
    while IFS='|' read -r component name url dest size; do
        [[ "$component" =~ ^#.* ]] && continue
        [ -z "$component" ] && continue
        [ "$component" != "$target" ] && continue

        found=1
        download_file "$url" "$ROOT/$dest" "$name"
    done < <(sed -n '/^# WEIGHT_REGISTRY_START/,/^# WEIGHT_REGISTRY_END/p' "$0" | grep -v "^#" | grep "|")

    if [ "$found" -eq 0 ]; then
        err "Unknown component: $target"
        info "Available: $(sed -n '/^# WEIGHT_REGISTRY_START/,/^# WEIGHT_REGISTRY_END/p' "$0" | grep -v "^#" | grep "|" | cut -d'|' -f1 | sort -u | tr '\n' ' ')"
    fi

    echo ""
    ok "$target download complete!"
}

download_all() {
    local components
    components=$(sed -n '/^# WEIGHT_REGISTRY_START/,/^# WEIGHT_REGISTRY_END/p' "$0" | grep -v "^#" | grep "|" | cut -d'|' -f1 | sort -u)

    for component in $components; do
        download_component "$component"
    done

    echo ""
    echo "=========================================="
    echo "  🎯 ALL DOWNLOADS COMPLETE!"
    echo "=========================================="
    list_weights
}

# ── Main ──────────────────────────────────────────────────────────────────────

case "${1:-all}" in
    --list|-l)
        list_weights
        ;;
    --help|-h)
        echo "Usage: bash $0 [--list|--help|<component>]"
        echo ""
        echo "  --list         List weight status"
        echo "  --help         Show this help"
        echo "  all            Download ALL missing weights (default)"
        echo "  <component>    Download specific component (liveportrait, musetalk, flame, etc.)"
        ;;
    all)
        download_all
        ;;
    *)
        download_component "$1"
        ;;
esac

# ═══════════════════════════════════════════════════════════════════════════════
# WEIGHT REGISTRY
# Format: component|name|url|dest_path|size_hint
# ═══════════════════════════════════════════════════════════════════════════════
# WEIGHT_REGISTRY_START
# NOTE: Already-downloaded weights (kokoro, bge-m3) are listed for status only
kokoro|kokoro-v1_0.pth|https://github.com/hexgrad/kokoro/releases/download/v1.0/kokoro-v1_0.pth|weights/kokoro/kokoro-v1_0.pth|~350 MB
liveportrait|LivePortrait Base|https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/liveportrait-base.pth|weights/liveportrait/liveportrait-base.pth|~1.5 GB
liveportrait|Feature Extractor|https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/feature_extractor.pth|weights/liveportrait/feature_extractor.pth|~350 MB
liveportrait|Landmark ONNX|https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/landmark.onnx|weights/liveportrait/landmark.onnx|~10 MB
musetalk|MuseTalk Config|https://huggingface.co/TMElyralab/MuseTalk/resolve/main/musetalk.json|weights/musetalk/musetalk.json|~1 MB
musetalk|MuseTalk Model|https://huggingface.co/TMElyralab/MuseTalk/resolve/main/pytorch_model.bin|weights/musetalk/pytorch_model.bin|~2.3 GB
musetalk|MuseTalkV15 UNet|https://huggingface.co/TMElyralab/MuseTalk/resolve/main/musetalkV15/unet.pth|weights/musetalk/unet.pth|~2.3 GB
musetalk|SD-VAE|https://huggingface.co/stabilityai/sd-vae-ft-mse/resolve/main/diffusion_pytorch_model.bin|weights/musetalk/sd-vae/diffusion_pytorch_model.bin|~350 MB
musetalk|Whisper Tiny|https://huggingface.co/openai/whisper-tiny/resolve/main/pytorch_model.bin|weights/musetalk/whisper/pytorch_model.bin|~150 MB
flame|FLAME Model|https://huggingface.co/YadiraF/FLAME/resolve/main/FLAME_model.pth|weights/flame/FLAME_model.pth|~20 MB
flame|FLAME Masks|https://huggingface.co/YadiraF/FLAME/resolve/main/FLAME_masks.pkl|weights/flame/FLAME_masks.pkl|~5 MB
flame|FLAME Texture|https://huggingface.co/YadiraF/FLAME/resolve/main/FLAME_texture.npz|weights/flame/FLAME_texture.npz|~5 MB
flame|PFLD Model|https://github.com/polarisZhao/PFLD-pytorch/raw/master/models/PFLD_GHost_1.1_9.1mb.pth|weights/flame/pfld_model.pth|~9 MB
retinaface|RetinaFace R50|https://github.com/deepinsight/insightface/releases/download/v0.7/retinaface-R50.zip|weights/retinaface/retinaface-R50.zip|~180 MB
retinaface|BiSeNet 79999|https://drive.google.com/uc?id=154JgKpzCPW82qINcVieuPH3fZ2e0P812&export=download|weights/retinaface/79999_iter.pth|~50 MB
# WEIGHT_REGISTRY_END
