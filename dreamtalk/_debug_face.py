"""Debug face detection on user's image."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ["PYTHONPATH"] = os.path.dirname(__file__)

import cv2
import numpy as np

from dreamtalk.pipeline.face_pipeline import FacePipeline

fp = FacePipeline()
img_path = r"local_upload_testing\image\testing image1.jpeg"
image = fp._load_image(img_path)
print(f"Image loaded: {image.shape if image is not None else None}")

faces = fp.detect_faces(image)
print(f"Detect faces result: {len(faces)}")
for f in faces:
    print(f"  {f.get('backend','?')}: bbox={f['bbox']}, conf={f['confidence']}")

haar_faces = fp._detect_faces_haar(image)
print(f"Haar directly: {len(haar_faces)}")

import asyncio
async def test():
    result = await fp.run([img_path])
    print(f"Full run: face_detected={result.face_detected}, backend={result.detection_backend}")

asyncio.run(test())
