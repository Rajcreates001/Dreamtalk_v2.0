"""
IndicF5 Venv Runner — Standalone entry point for the dedicated venv.

This script is designed to be run using the Python interpreter from the
dedicated IndicF5 venv (D:\\venvs\\indicf5\\Scripts\\python.exe). It starts
a FastAPI microservice identical to the Docker version, but runs directly
without Docker.

Usage (from the venv):
    python -m dreamtalk.voice.core.vc.indicf5_venv_runner [--port 8002]

Or via subprocess from the main app:
    subprocess.run([
        "D:/venvs/indicf5/Scripts/python.exe",
        "-m", "dreamtalk.voice.core.vc.indicf5_venv_runner",
        "--port", "8002"
    ])

The venv isolates torch and its DLLs from the main process, avoiding
the Windows OpenMP DLL conflict (libomp.dll vs libiomp5md.dll).
"""

import os
import sys

# ---------------------------------------------------------------------------
# Fix OpenMP before any other imports
# ---------------------------------------------------------------------------
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

# Ensure the project root is on sys.path
_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("dreamtalk.indicf5.venv")


def main():
    parser = argparse.ArgumentParser(description="IndicF5 Venv Runner")
    parser.add_argument("--port", type=int, default=8002, help="Port to listen on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    # Import the microservice app (reuses the same FastAPI app)
    from dreamtalk.voice.core.vc.indicf5_microservice import app
    import uvicorn

    logger.info("Starting IndicF5 venv runner on %s:%s", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
