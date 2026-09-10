#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "=== Building dreamtalk-backend ==="
echo "Start: $(date)"
docker build -f Dockerfile -t dreamtalk-backend:latest .. 2>&1
echo "=== Build complete: $(date) ==="
echo "Image:"
docker images dreamtalk-backend --format "{{.Repository}}:{{.Tag}} {{.Size}}"
