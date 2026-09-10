"""Create test assets for LivePortrait API testing."""
import cv2
import numpy as np
import os

# Find an existing sample image
img_path = None
candidates = [
    'local_upload_testing/Image_local/sample1.jpeg',
    'local_upload_testing/image/sample1.jpeg',
    'local_upload_testing/upload_img_78e8edb51559407e8dcc86159eb45336.jpeg',
]

for p in candidates:
    if os.path.exists(p):
        img_path = p
        break

if img_path is None:
    # Create synthetic test face
    img = np.ones((480, 640, 3), dtype=np.uint8) * 200
    cv2.ellipse(img, (320, 240), (160, 200), 0, 0, 360, (220, 180, 140), -1)
    cv2.circle(img, (260, 200), 15, (50, 50, 50), -1)
    cv2.circle(img, (380, 200), 15, (50, 50, 50), -1)
    cv2.ellipse(img, (320, 300), (80, 25), 0, 0, 180, (80, 60, 40), 3)
    img_path = 'local_upload_testing/test_face.jpg'
    cv2.imwrite(img_path, img)
    print(f'Created synthetic test face: {img_path}')
else:
    print(f'Using existing sample: {img_path}')

# Read source image
img = cv2.imread(img_path)
if img is None:
    print(f'ERROR: Could not read {img_path}')
    exit(1)
h, w = img.shape[:2]
print(f'Source image: {img_path} ({w}x{h})')

# Create a 3-second driving video (static for minimal test)
out_path = 'local_upload_testing/driving_test.mp4'
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
fps = 30
out = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
for i in range(fps * 3):
    out.write(img)
out.release()
size_mb = os.path.getsize(out_path) / (1024*1024)
print(f'Created driving video: {out_path} ({size_mb:.1f} MB, {fps*3}frames)')

# Create a driving image (copy)
src2_path = 'local_upload_testing/driving_image.jpg'
cv2.imwrite(src2_path, img)
print(f'Created driving image: {src2_path}')

print('All test assets ready!')
