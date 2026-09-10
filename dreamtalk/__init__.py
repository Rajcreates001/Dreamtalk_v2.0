"""Dreamtalk - AI Digital Twin Platform"""

import os
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════
# Platform-specific torch fixes (MUST run before any torch imports)
# ═══════════════════════════════════════════════════════════════════
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

if sys.platform == "win32":
    try:
        _torch_lib = None
        # Try to locate torch lib directory
        try:
            import torch as _t
            _torch_lib = str(Path(_t.__file__).resolve().parent / "lib")
            del _t
        except (ImportError, OSError):
            # torch not installed yet or DLL broken - search common locations
            _site_pkg = Path(sys.prefix) / "Lib" / "site-packages" / "torch" / "lib"
            if _site_pkg.exists():
                _torch_lib = str(_site_pkg)
            else:
                _site_pkg_alt = Path(sys.prefix) / "lib" / "site-packages" / "torch" / "lib"
                if _site_pkg_alt.exists():
                    _torch_lib = str(_site_pkg_alt)
        
        if _torch_lib:
            if _torch_lib not in os.environ.get("PATH", ""):
                os.environ["PATH"] = _torch_lib + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(_torch_lib)
                except Exception:
                    pass
    except Exception:
        pass  # Non-fatal - torch-dependent features will degrade gracefully

# Ensure the PARENT of project root is on sys.path so sub-packages can import correctly
# (e.g. dreamtalk.media, dreamtalk.voice, etc.)
_project_root = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_project_root)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)
