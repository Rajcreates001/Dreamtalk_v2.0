"""Check the landmark features match the bundled eye retargeter's input."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np

spec = importlib.util.spec_from_file_location(
    "eye_ratios", Path(__file__).resolve().parents[2]
    / "face/core/animation/liveportrait/utils/retargeting_utils.py",
)
ratios = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ratios)


class EyeRetargetingTests(unittest.TestCase):
    def test_two_source_eyes_plus_target_match_checkpoint(self):
        source = ratios.calc_eye_close_ratio(np.zeros((2, 203, 2), np.float32))
        self.assertEqual(source.shape, (2, 2))
        self.assertEqual(63 + source.shape[1] + 1, 66)
        self.assertTrue(np.isfinite(source).all())

    def test_missing_landmarks_keep_same_feature_width(self):
        self.assertEqual(ratios.calc_eye_close_ratio(None).shape, (1, 2))


if __name__ == "__main__":
    unittest.main()
