"""Alias: run the integrated backend instead."""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import uvicorn

if __name__ == "__main__":
    print("Running integrated backend (avatar + pipeline + API logging)")
    print("Open: http://localhost:5000/api/avatar/viewer")
    uvicorn.run(
        "dreamtalk.backend.main:app",
        host="0.0.0.0",
        port=5000,
        log_level="info",
    )
