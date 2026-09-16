"""Client for the self-hosted mesh reconstruction service.

The 3D head is currently produced by fitting FLAME: a fixed 5023-vertex
template deformed by ~300 coefficients, with the photograph projected on as
texture. Measured against the photo it is recognisably the right person
(Facenet512 distance 0.1445 against a 0.300 threshold) and the outline is
wrong (silhouette IoU 0.5561, covering 72% of the photographed head's area).
The missing third is hair and the crown of the skull, because the template
does not have any and no texture fixes a silhouette.

`dreamtalk-mesh3d` runs TripoSR, which infers geometry from the image instead
of deforming a template. It is a separate container because it wants ~6GB of
VRAM on a card that also holds vLLM and MuseTalk, so it has to be startable
and stoppable around a build rather than resident.

Everything here degrades to None rather than raising. A reconstruction that
fails should cost the avatar its generated geometry and nothing else: the
FLAME path still produces a head, and a head with a poor outline beats an
avatar that failed to build.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Inside the compose network the service is reachable by name. The env var
# exists so the same code works when the backend runs outside Docker.
BASE_URL = os.environ.get("MESH3D_URL", "http://dreamtalk-mesh3d:8003")
# Reconstruction is a batch step in avatar creation, not a realtime path, and
# TripoSR's first call also pays a cold model load.
TIMEOUT = float(os.environ.get("MESH3D_TIMEOUT", "600"))
HEALTH_TIMEOUT = float(os.environ.get("MESH3D_HEALTH_TIMEOUT", "5"))


def _client():
    import httpx
    return httpx.Client(base_url=BASE_URL, timeout=TIMEOUT)


def available() -> bool:
    """Is the service up? Cheap, and never raises.

    Note that this only says the process is answering. It deliberately does
    not report `model_loaded`, because the model is loaded lazily on the first
    reconstruction and "not loaded yet" is the normal idle state, not a fault.
    The pattern worth avoiding is the opposite one - a green /health beside a
    capability that does not work - so the real check is calling reconstruct.
    """
    try:
        import httpx
        with httpx.Client(base_url=BASE_URL, timeout=HEALTH_TIMEOUT) as client:
            response = client.get("/health")
            return response.status_code == 200
    except Exception as exc:
        logger.info("mesh3d unavailable at %s (%s)", BASE_URL, exc)
        return False


def status() -> Optional[dict]:
    try:
        import httpx
        with httpx.Client(base_url=BASE_URL, timeout=HEALTH_TIMEOUT) as client:
            response = client.get("/health")
            response.raise_for_status()
            return response.json()
    except Exception:
        return None


def reconstruct(image_path: str, destination: str,
                bake_texture: bool = True,
                texture_resolution: int = 2048,
                remove_background: bool = True) -> Optional[dict]:
    """Reconstruct a mesh from one photograph. Returns metadata, or None.

    `destination` receives a GLB. The returned dict carries the vertex and
    face counts the service reports, which are worth logging: a mesh that
    comes back with a few hundred vertices did not reconstruct a head, and
    that is visible in the numbers long before anybody looks at it.
    """
    if not os.path.exists(image_path):
        logger.warning("mesh3d: source image missing: %s", image_path)
        return None

    started = time.time()
    try:
        with _client() as client, open(image_path, "rb") as handle:
            response = client.post(
                "/reconstruct",
                files={"image": (os.path.basename(image_path), handle,
                                 "image/jpeg")},
                data={"bake_texture": str(bake_texture).lower(),
                      "texture_resolution": str(texture_resolution),
                      "remove_background": str(remove_background).lower()},
            )
        if response.status_code != 200:
            logger.warning("mesh3d: HTTP %d: %s", response.status_code,
                           response.text[:300])
            return None
        os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)
        with open(destination, "wb") as out:
            out.write(response.content)
        info = {
            "path": destination,
            "bytes": len(response.content),
            "vertices": int(response.headers.get("X-Mesh-Vertices", 0)),
            "faces": int(response.headers.get("X-Mesh-Faces", 0)),
            "service_seconds": float(response.headers.get("X-Elapsed-Seconds", 0)),
            "total_seconds": round(time.time() - started, 2),
        }
        logger.info("mesh3d: %d verts / %d faces in %.1fs -> %s",
                    info["vertices"], info["faces"], info["total_seconds"],
                    destination)
        return info
    except Exception as exc:
        logger.warning("mesh3d: reconstruction failed (%s); keeping the "
                       "template fit", exc)
        return None


def unload() -> bool:
    """Ask the service to drop the model and give the card back.

    Worth calling after a batch of avatar builds. TripoSR idle costs nothing
    until it has been used once; after that it holds its weights until told
    otherwise, and on an 8GB card that is the difference between MuseTalk
    loading and MuseTalk failing.
    """
    try:
        import httpx
        with httpx.Client(base_url=BASE_URL, timeout=60) as client:
            return client.post("/unload").status_code == 200
    except Exception:
        return False
