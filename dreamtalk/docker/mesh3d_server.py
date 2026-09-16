"""TripoSR as an HTTP service: one photo in, a real mesh out.

This exists because the 3D head was being produced by fitting FLAME — a
pre-built statistical template whose fixed 5023-vertex topology is deformed
by ~300 coefficients, with the photograph projected on as texture. That
approach cannot represent anything the template does not already contain,
which is why hair had no volume and the silhouette followed a bare skull.
TripoSR infers geometry from the image itself.

The model is loaded lazily and can be dropped again, because it wants ~6GB
of VRAM on a card that also holds vLLM (~3.7GB) and MuseTalk (~2GB).
Reconstruction is a batch step in avatar creation, not a realtime path, so
the caller is expected to free the others around it rather than to keep all
three resident.
"""
from __future__ import annotations

import io
import logging
import os
import tempfile
import time

import numpy as np
import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dreamtalk.mesh3d")

PORT = int(os.environ.get("MESH3D_PORT", "8003"))
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# TripoSR's default chunk size targets ~6GB. Lowering it trades throughput
# for headroom, which is the right trade on a shared 8GB card.
CHUNK_SIZE = int(os.environ.get("MESH3D_CHUNK_SIZE", "4096"))
MC_RESOLUTION = int(os.environ.get("MESH3D_MC_RESOLUTION", "256"))

app = FastAPI(title="DreamTalk mesh3d (TripoSR)")
_model = None
_loaded_at = None


def _load():
    """Load TripoSR. Lazy, so the container can idle without holding VRAM."""
    global _model, _loaded_at
    if _model is not None:
        return _model
    import sys
    sys.path.insert(0, "/opt/triposr")
    from tsr.system import TSR

    started = time.time()
    model = TSR.from_pretrained(
        "stabilityai/TripoSR",
        config_name="config.yaml",
        weight_name="model.ckpt",
    )
    model.renderer.set_chunk_size(CHUNK_SIZE)
    model.to(DEVICE)
    _model = model
    _loaded_at = time.time()
    logger.info("TripoSR loaded on %s in %.1fs (chunk=%d)",
                DEVICE, time.time() - started, CHUNK_SIZE)
    return _model


@app.get("/health")
def health():
    free = total = None
    if torch.cuda.is_available():
        f, t = torch.cuda.mem_get_info()
        free, total = f // 2**20, t // 2**20
    return {
        "status": "ok",
        "model_loaded": _model is not None,
        "device": DEVICE,
        "chunk_size": CHUNK_SIZE,
        "mc_resolution": MC_RESOLUTION,
        "vram_free_mb": free,
        "vram_total_mb": total,
    }


@app.post("/unload")
def unload():
    """Drop the model so MuseTalk or vLLM can have the card back."""
    global _model
    _model = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
    return {"unloaded": True}


@app.post("/reconstruct")
async def reconstruct(
    image: UploadFile = File(...),
    bake_texture: bool = Form(True),
    texture_resolution: int = Form(2048),
    remove_background: bool = Form(True),
    foreground_ratio: float = Form(0.85),
):
    """Reconstruct a mesh from one image. Returns a GLB."""
    try:
        raw = await image.read()
        pil = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        raise HTTPException(400, f"unreadable image: {exc}") from exc

    started = time.time()
    model = _load()

    try:
        import rembg
        from tsr.utils import remove_background as tsr_rm, resize_foreground

        if remove_background:
            session = rembg.new_session()
            pil = tsr_rm(pil, session)
            pil = resize_foreground(pil, foreground_ratio)
            # TripoSR expects the subject composited onto mid grey; leaving
            # the alpha in place makes the network hallucinate geometry where
            # the cutout is transparent.
            arr = np.array(pil).astype(np.float32) / 255.0
            if arr.shape[-1] == 4:
                arr = arr[:, :, :3] * arr[:, :, 3:4] + 0.5 * (1 - arr[:, :, 3:4])
            pil = Image.fromarray((arr * 255.0).astype(np.uint8))

        with torch.no_grad():
            codes = model([pil], device=DEVICE)
            meshes = model.extract_mesh(
                codes, bake_texture, resolution=MC_RESOLUTION,
                texture_resolution=texture_resolution,
            )
        mesh = meshes[0]

        out = tempfile.NamedTemporaryFile(suffix=".glb", delete=False)
        out.close()
        mesh.export(out.name)
        elapsed = time.time() - started
        logger.info("reconstructed %d verts / %d faces in %.1fs",
                    len(mesh.vertices), len(mesh.faces), elapsed)
        return FileResponse(
            out.name, media_type="model/gltf-binary", filename="mesh.glb",
            headers={
                "X-Mesh-Vertices": str(len(mesh.vertices)),
                "X-Mesh-Faces": str(len(mesh.faces)),
                "X-Elapsed-Seconds": f"{elapsed:.2f}",
            },
        )
    except torch.cuda.OutOfMemoryError as exc:
        # Say what to do about it. On this card the usual cause is MuseTalk or
        # vLLM still holding memory, not TripoSR being too large.
        logger.error("CUDA OOM during reconstruction: %s", exc)
        raise HTTPException(
            507,
            "out of VRAM; free the other models first or lower "
            "MESH3D_CHUNK_SIZE / MESH3D_MC_RESOLUTION",
        ) from exc
    except Exception as exc:
        logger.exception("reconstruction failed")
        raise HTTPException(500, f"reconstruction failed: {exc}") from exc


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
