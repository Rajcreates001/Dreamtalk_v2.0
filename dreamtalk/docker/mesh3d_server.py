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

import asyncio
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


def _bake(mesh, model, scene_code, resolution: int):
    """Unwrap and bake a texture, falling back to vertex colours.

    Baking needs xatlas for the UV unwrap and is the part of this pipeline
    most likely to be missing or to fail on a degenerate mesh. Vertex colours
    are always available and carry the same colour information at lower
    spatial frequency, so a failed bake should downgrade the texture rather
    than fail the reconstruction.
    """
    try:
        import numpy as _np
        from PIL import Image as _Image
        from tsr.bake_texture import bake_texture as tsr_bake

        baked = tsr_bake(mesh, model, scene_code, resolution)
        mesh.visual = _mesh_texture_visual(mesh, baked)
        logger.info("baked %dx%d texture", resolution, resolution)
        return mesh
    except Exception as exc:
        # Only truthful because extract_mesh is now always called with
        # has_vertex_color=True. Say which fallback actually applies.
        kept = getattr(getattr(mesh, "visual", None), "vertex_colors", None)
        logger.warning("texture bake unavailable (%s); %s", exc,
                       "keeping vertex colours" if kept is not None
                       else "AND THE MESH HAS NO VERTEX COLOURS EITHER")
        return mesh


def _mesh_texture_visual(mesh, baked):
    """Attach a baked texture to a trimesh mesh."""
    import numpy as _np
    import trimesh
    from PIL import Image as _Image

    image = baked["colors"]
    if isinstance(image, _np.ndarray):
        # bake_texture returns float RGB in 0..1 with the origin at the
        # bottom, which is OpenGL's convention and not glTF's.
        if image.dtype != _np.uint8:
            image = (_np.clip(image, 0, 1) * 255).astype(_np.uint8)
        image = _Image.fromarray(image[::-1])
    return trimesh.visual.TextureVisuals(
        uv=baked["uvs"], image=image)


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

    # Everything below is synchronous GPU work, so it runs in a worker thread.
    # Doing it inline blocked the event loop for the whole reconstruction:
    # /health stopped answering, which meant the container's own healthcheck
    # reported it unhealthy for exactly as long as it was busy being useful.
    return await asyncio.to_thread(
        _reconstruct_sync, pil, bake_texture, texture_resolution,
        remove_background, foreground_ratio, started,
    )


def _reconstruct_sync(pil, bake_texture, texture_resolution,
                      remove_background, foreground_ratio, started):
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
            # TSR.extract_mesh(scene_codes, has_vertex_color, resolution=...).
            # The second argument is NOT "bake a texture" - it is the opposite
            # of it. Always ask for vertex colours, regardless of whether a
            # texture is wanted on top.
            #
            # Passing `not bake_texture` here produced a mesh with neither.
            # Baking needs an OpenGL context and there is none in a headless
            # container ("XOpenDisplay: cannot open display"), so the bake fell
            # back to "keeping vertex colours" that had never been extracted.
            # The GLB came out carrying POSITION and nothing else: 60697
            # vertices of correct geometry with no colour anywhere, which
            # renders as a featureless grey blob and detects as no face at all.
            meshes = model.extract_mesh(codes, True, resolution=MC_RESOLUTION)
        mesh = meshes[0]
        has_colour = getattr(getattr(mesh, "visual", None), "vertex_colors",
                             None) is not None

        if bake_texture:
            mesh = _bake(mesh, model, codes[0], texture_resolution)

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
                "X-Mesh-Has-Colour": "1" if has_colour else "0",
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
