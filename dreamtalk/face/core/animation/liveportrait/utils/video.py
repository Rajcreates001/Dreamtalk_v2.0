# Dreamtalk - Face Engine
# Extracted from LivePortrait
import cv2
import numpy as np
import subprocess
import os


def get_fps(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    return fps


def has_audio_stream(video_path):
    result = subprocess.run(
        ['ffprobe', '-i', video_path, '-show_streams', '-select_streams', 'a', '-loglevel', 'error'],
        capture_output=True, text=True
    )
    return 'index' in result.stdout


def images2video(img_lst, wfp, fps=25):
    h, w = img_lst[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(wfp, fourcc, fps, (w, h))
    for img in img_lst:
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        writer.write(img_bgr)
    writer.release()


def concat_frames(driving_lst, source_lst, gen_lst):
    # Make all same height
    h = max(driving_lst[0].shape[0], source_lst[0].shape[0], gen_lst[0].shape[0])
    result = []
    n = len(gen_lst)
    for i in range(n):
        d_idx = i if i < len(driving_lst) else len(driving_lst) - 1
        s_idx = i if i < len(source_lst) else len(source_lst) - 1
        d = cv2.resize(driving_lst[d_idx], (h, h))
        s = cv2.resize(source_lst[s_idx], (h, h))
        g = cv2.resize(gen_lst[i], (h, h))
        concat = np.concatenate([d, s, g], axis=1)
        result.append(concat)
    return result


def add_audio_to_video(video_path, audio_path, output_path):
    cmd = [
        'ffmpeg', '-y', '-i', video_path, '-i', audio_path,
        '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0',
        '-shortest', output_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
