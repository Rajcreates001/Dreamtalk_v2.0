"""Start DreamTalk backend server in a subprocess."""
import subprocess
import sys
import os
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
sys.path.insert(0, project_root)

# Start uvicorn process
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "dreamtalk.backend.main:app",
     "--host", "0.0.0.0", "--port", "5000", "--log-level", "info"],
    cwd=project_root,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

print(f"Backend started (PID: {proc.pid})")
