"""Exercise a stored test avatar through the authenticated public API.

Run inside the backend container. Uses the existing deep_e2e test account;
never prints or persists its access token. Media stays in ignored e2e_deep.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    state = json.loads((root / "e2e_deep/state.json").read_text())
    base = os.environ.get("API", "http://localhost:5000")
    with httpx.Client(base_url=base, timeout=900) as client:
        login = client.post("/api/v1/auth/login", json={
            "email": state["email"],
            "password": os.environ.get("E2E_TEST_PASSWORD", "E2eTest!2345"),
        })
        login.raise_for_status()
        client.headers["Authorization"] = "Bearer " + login.json()["tokens"]["access_token"]
        start = time.perf_counter()
        if args.video:
            response = client.post(f"/api/v1/avatar/profiles/{state['pid']}/speak-2d", json={
                "text": "नमस्ते। आप कैसे हैं?", "language": "hi",
                "emotion": "happy", "strict_clone": True, "engine": "musetalk",
            })
            response.raise_for_status()
            result = response.json()
            assert result["audio"]["cloned"] is True, "Cloned voice required"
            video = result["video"]
            assert video.get("neural") is True, "Neural renderer required"
            url = video.get("video_url") or video.get("url")
            assert url, "Missing video URL"
            media = client.get(url)
            media.raise_for_status()
            output = root / "e2e_deep/acceptance_current.mp4"
            output.write_bytes(media.content)
            probe = subprocess.run([
                "ffprobe", "-v", "error", "-show_streams", "-of", "json", str(output),
            ], check=True, capture_output=True, text=True)
            streams = json.loads(probe.stdout)["streams"]
            assert {s["codec_type"] for s in streams} >= {"audio", "video"}
            print(json.dumps({"passed": True, "cloned": True, "neural": True,
                              "elapsed_seconds": round(time.perf_counter()-start, 2),
                              "output": str(output)}, indent=2), flush=True)
        else:
            response = client.post(f"/api/v1/avatar/profiles/{state['pid']}/respond", json={
                "message": "Say hello in one short sentence.", "language": "en",
                "emotion": "sad", "synthesize": False,
            })
            response.raise_for_status()
            result = response.json()
            assert result["emotion"] == "sad"
            assert result["response_emotion"]["source"] == "explicit"
            assert result["brain"].get("fallback") is False
            print("PASS: authenticated conversation, real LLM, explicit emotion", flush=True)


if __name__ == "__main__":
    main()
