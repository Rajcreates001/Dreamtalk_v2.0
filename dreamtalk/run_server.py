"""Start the DreamTalk backend server with correct sys.path setup.

Run from the **project virtual environment** (dt_venv):
    dt_venv/Scripts/python run_server.py

Alternatively, activate the venv first:
    dt_venv/Scripts/activate
    python run_server.py

If you see import errors related to transformers/sentence-transformers,
you are likely running with the wrong Python (use dt_venv Python 3.11).
"""
import os
import sys
from pathlib import Path

# Warn if not running from dt_venv
if sys.prefix == sys.base_prefix:
    _venv_python = Path(__file__).resolve().parent / "dt_venv" / "Scripts" / "python.exe"
    print("=" * 60)
    print("WARNING: Not running inside the project's virtual environment!")
    print("  System Python: " + sys.executable)
    print("  Project venv:  " + str(_venv_python))
    print("  Activate:      dt_venv/Scripts/activate")
    print("  Or run:        dt_venv/Scripts/python run_server.py")
    print("=" * 60)

# Ensure the parent directory (Dreamtalk-Integrated/) is on sys.path
# NOT the project root (dreamtalk/) - this avoids namespace conflicts
here = os.path.dirname(os.path.abspath(__file__))
parent = os.path.dirname(here)

# Remove project root from sys.path if present
sys.path = [p for p in sys.path if os.path.abspath(p) != os.path.abspath(here)]

if parent not in sys.path:
    sys.path.insert(0, parent)

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("PHONEMIZER_ESPEAK_LIBRARY", os.path.join(here, "espeak-ng", "libespeak-ng.dll"))
os.environ.setdefault("ESPEAK_DATA_PATH", os.path.join(here, "espeak-ng", "espeak-ng-data"))

import uvicorn
uvicorn.run("dreamtalk.backend.main:app", host="0.0.0.0", port=5001)
