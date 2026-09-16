"""Phase 2: reconstruct with TripoSR and put it beside FLAME on the same photo.

Runs in the backend container so it can reach both the mesh service and the
avatar runtime:

  docker exec -i dreamtalk-backend python - < phase2_generated_vs_flame.py

The comparison is deliberately narrow. It answers whether geometry inferred
from the image beats geometry fitted from a template, on identity and on
outline, for this photograph. It does not answer whether the generated mesh
can be animated - that is Phase 3, and the answer here decides whether Phase 3
is worth attempting at all.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, "/app")

RUNTIME = "/app/dreamtalk/media/avatar_runtime"
OUT = "/tmp/mesh_compare"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default="71d2b3f8-51eb-4435-a4ee-665f60049850")
    ap.add_argument("--photo", default=None)
    ap.add_argument("--no-bake", action="store_true",
                    help="vertex colours instead of a baked texture")
    ap.add_argument("--reuse", action="store_true",
                    help="skip reconstruction if the GLB is already there")
    args = ap.parse_args()

    from dreamtalk.pipeline import mesh3d_client

    photo = args.photo or sorted(
        glob.glob(os.path.join(RUNTIME, args.profile, "appearance/source/*.jpg")))[0]
    os.makedirs(OUT, exist_ok=True)
    destination = os.path.join(OUT, "generated.glb")

    status = mesh3d_client.status()
    print("mesh3d status: %s" % json.dumps(status))
    if status is None:
        print("mesh3d is not reachable at %s" % mesh3d_client.BASE_URL,
              file=sys.stderr)
        return 2

    if args.reuse and os.path.exists(destination):
        print("reusing %s" % destination)
    else:
        print("reconstructing from %s ..." % photo)
        started = time.time()
        info = mesh3d_client.reconstruct(
            photo, destination, bake_texture=not args.no_bake)
        if info is None:
            print("reconstruction failed; see the mesh3d container log",
                  file=sys.stderr)
            return 1
        print("reconstructed in %.1fs: %s" % (time.time() - started,
                                              json.dumps(info)))
        # A head that comes back with a few hundred vertices did not
        # reconstruct; say so here rather than letting it fail later as a
        # confusing rendering problem.
        if info["vertices"] < 5000:
            print("WARNING: only %d vertices - that is not a head at this "
                  "marching-cubes resolution" % info["vertices"])

    cmd = [sys.executable, "/app/dreamtalk/scripts/qa/mesh_compare.py",
           "--profile", args.profile, "--generated-glb", destination]
    print("\n" + " ".join(cmd))
    env = dict(os.environ)
    # RetinaFace runs on TensorFlow, whose bundled cuDNN does not match the
    # one in this image ("Loaded runtime CuDNN library: 9.1.0 but source was
    # compiled with: 9.3.0"). On GPU every detection silently returns no face
    # and the orientation search then has nothing to choose between.
    env["CUDA_VISIBLE_DEVICES"] = ""
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    sys.exit(main())
