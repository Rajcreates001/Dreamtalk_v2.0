"""Regression tests for the render acceptance gate, without loading AI models."""
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, mock_open, patch

import e2e_avatar as qa


class LipSyncVerificationTests(unittest.TestCase):
    def verify(self, files, motion):
        response = Mock(status_code=200)
        response.json.return_value = {
            "video_url": "/api/v1/avatar/assets/profile/responses/new.mp4?signature=test",
            "engine": "musetalk",
        }
        with ExitStack() as stack:
            stack.enter_context(patch.object(qa, "token", return_value="test"))
            stack.enter_context(patch.object(qa.subprocess, "run"))
            stack.enter_context(patch("builtins.open", mock_open(read_data=b"audio")))
            stack.enter_context(patch("httpx.post", return_value=response))
            stack.enter_context(patch.object(qa.glob, "glob", return_value=files))
            measure = stack.enter_context(patch.object(qa, "_frame_motion", return_value=motion))
            result = qa.phase_lipsync()
            return result, measure.call_count

    def test_rejects_an_older_video(self):
        result, calls = self.verify(["/tmp/old.mp4"], {})
        self.assertFalse(result["ok"])
        self.assertEqual(calls, 0)

    def test_rejects_a_motionless_new_video(self):
        result, _ = self.verify(["/tmp/new.mp4"], {
            "mouth": 0, "mouth_over_eyes": 0, "background": 0,
        })
        self.assertFalse(result["ok"])

    def test_accepts_measured_mouth_motion(self):
        result, calls = self.verify(["/tmp/new.mp4"], {
            "mouth": 2, "mouth_over_eyes": 4, "background": 0.1,
        })
        self.assertTrue(result["ok"])
        self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
