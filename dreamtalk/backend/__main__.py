"""Entry point: run the DreamTalk backend from the dreamtalk/ root directory.

Usage:
  cd dreamtalk/
  python -m dreamtalk.backend

  # OR:
  python -m uvicorn dreamtalk.backend.main:app --host 0.0.0.0 --port 5001
"""
import os
import sys
from pathlib import Path

# ── Windows torch DLL preload (before any torch import) ───────────────
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

if sys.platform == "win32":
    try:
        _torch_lib = None
        _site_pkg = Path(sys.prefix) / "Lib" / "site-packages" / "torch" / "lib"
        if _site_pkg.exists():
            _torch_lib = str(_site_pkg)
        if _torch_lib:
            if _torch_lib not in os.environ.get("PATH", ""):
                os.environ["PATH"] = _torch_lib + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(_torch_lib)
                except Exception:
                    pass
    except Exception:
        pass

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_backend_dir)
os.chdir(_project_root)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "dreamtalk.backend.main:app",
        host="0.0.0.0",
        port=5001,
    )
