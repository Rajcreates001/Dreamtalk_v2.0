#!/bin/bash
set -e
echo "=== Setting up WSL environment ==="

# Create virtual env
cd /mnt/d/Black\ folder/DreamTalk_Startup/Dreamtalk-Integrated
python3 -m venv /tmp/dt-venv
source /tmp/dt-venv/bin/activate

# Install kokoro
echo "Installing kokoro..."
pip install -e repos-used/kokoro 2>&1 | tail -5
python -c "import kokoro; print('kokoro', kokoro.__version__)"

# Install torch
echo "Installing torch..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 2>&1 | tail -5
python -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"

# Install scipy
pip install scipy numpy 2>&1 | tail -3

# Run pipeline
echo "=== Running pipeline ==="
PYTHONPATH=. python3 generate_pipeline_samples.py 2>&1

echo "=== Pipeline complete ==="

# Check Docker pull
PID_FILE=/tmp/docker_pull.pid
if [ -f "$PID_FILE" ]; then
    kill -0 $(cat $PID_FILE) 2>/dev/null && echo "Docker pull still running" || echo "Docker pull finished"
fi

# Check results
ls -la pipeline_outputs/ 2>&1
head -50 pipeline_outputs/pipeline_samples_summary.json 2>/dev/null || echo "No summary"
