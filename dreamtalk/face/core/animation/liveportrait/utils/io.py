# Dreamtalk - Face Engine
# Extracted from LivePortrait
import cv2
import numpy as np
import pickle


def load_image_rgb(path):
    img = cv2.imread(path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img


def load_video(path):
    cap = cv2.VideoCapture(path)
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(frame)
    cap.release()
    return frames


def resize_to_limit(img, max_dim, division=2):
    h, w = img.shape[:2]
    if max_dim > 0 and max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = cv2.resize(img, (new_w, new_h))
    if division > 1:
        h, w = img.shape[:2]
        new_h = h - (h % division)
        new_w = w - (w % division)
        if new_h != h or new_w != w:
            img = cv2.resize(img, (new_w, new_h))
    return img


def dump(path, obj):
    with open(path, 'wb') as f:
        pickle.dump(obj, f)


def load(path):
    with open(path, 'rb') as f:
        return pickle.load(f)
