"""Regression coverage for how the photograph's texture reaches the render.

These tests originally asserted that _restore_detail must be independent of
its reference - that a render must never take anything from the photograph,
to avoid stamping a closed mouth over an open one. Measurement overturned
that. Refusing the donor everywhere is what left the beard at 4% of the
photograph's texture and the jaw at 11%, the washed-out lower face that made
renders read as fake, while the face-box average still reported 65% recovered.

The guarantee is narrower than "never" and narrower than "always": the donor
is used where the face does not move and refused where it does. The tests
below pin both halves, because the failure has come from each direction once.
"""
import importlib.util
from pathlib import Path
import unittest

import numpy as np

spec = importlib.util.spec_from_file_location(
    "mouth_blending",
    Path(__file__).resolve().parents[2]
    / "face/core/lipsync/musetalk/utils/blending.py",
)
blending = importlib.util.module_from_spec(spec)
spec.loader.exec_module(blending)


def _textured(shape=(64, 64, 3), seed=0):
    """A patch with high-frequency content to borrow."""
    rng = np.random.default_rng(seed)
    base = np.full(shape, 150, dtype=np.int16)
    base += rng.integers(-40, 41, size=shape, dtype=np.int16)
    return np.clip(base, 0, 255).astype(np.uint8)


def _detail(patch):
    import cv2

    grey = cv2.cvtColor(patch, cv2.COLOR_RGB2GRAY)
    return float(cv2.Laplacian(grey, cv2.CV_64F).var())


class MouthExclusionTests(unittest.TestCase):
    """The shape that decides where the donor is refused."""

    def test_refuses_the_donor_over_the_lips(self):
        keep = blending._mouth_exclusion((100, 100))
        # Lip centre: centre_y of the ellipse, middle of the patch.
        self.assertGreater(keep[68, 50], 0.3,
                           "the lips must keep some refusal of a still donor")

    def test_does_not_refuse_the_donor_over_the_jaw(self):
        """The ellipse once spanned x 0.10-0.90 and y 0.40-0.92 of the patch.

        That is the whole lower face, so the jaw and cheeks - which do not
        move - were refused the photograph's texture and measured 11-14% of
        it. Anything that widens the ellipse back over them should fail here.
        """
        keep = blending._mouth_exclusion((100, 100))
        # These points are chosen to DISCRIMINATE: each one sits inside the
        # old 0.40 x 0.26 ellipse and outside the current 0.24 x 0.16 one. An
        # earlier version of this test sampled the far corners instead, where
        # even the wide ellipse had faded to 0.06, and so passed on the bug it
        # was written to catch.
        for name, (y, x) in (("left jaw", (75, 20)),
                             ("right jaw", (75, 80)),
                             ("upper cheek", (50, 22))):
            self.assertLess(keep[y, x], 0.15,
                            "%s must be free to take photographic texture" % name)

    def test_refusal_is_partial_not_total(self):
        """A total refusal left the lips and chin at 24% and 10% of the source."""
        keep = blending._mouth_exclusion((100, 100))
        self.assertLess(float(keep.max()), 0.95,
                        "even the lips should keep a fraction of the donor")


class RestoreDetailTests(unittest.TestCase):
    def test_borrows_texture_from_the_reference(self):
        """The whole point: a flat generated patch gains the donor's texture."""
        reference = _textured()
        generated = np.full((64, 64, 3), 150, dtype=np.uint8)
        out = blending._restore_detail(generated, reference)
        self.assertGreater(_detail(out), _detail(generated) + 5.0,
                           "the reference's texture must reach the output")

    def test_output_depends_on_the_reference(self):
        """A different donor must produce a different result.

        The superseded version of this file asserted the opposite.
        """
        generated = np.full((64, 64, 3), 150, dtype=np.uint8)
        a = blending._restore_detail(generated, _textured(seed=1))
        b = blending._restore_detail(generated, _textured(seed=2))
        self.assertGreater(int(np.abs(a.astype(int) - b.astype(int)).max()), 2,
                           "two different photographs must not give one render")

    def test_lips_take_less_than_the_jaw(self):
        """The refusal has to actually bite where the mouth moves."""
        reference = _textured()
        generated = np.full((64, 64, 3), 150, dtype=np.uint8)
        out = blending._restore_detail(generated, reference).astype(int)
        base = generated.astype(int)
        change = np.abs(out - base).mean(axis=2)
        lips = change[38:46, 24:40].mean()      # centre of the exclusion
        jaw = change[52:62, 2:14].mean()        # outer lower corner
        self.assertLess(lips, jaw,
                        "the lips must take less donor texture than the jaw")

    def test_mismatched_reference_is_safe(self):
        generated = np.full((64, 64, 3), 150, dtype=np.uint8)
        np.testing.assert_array_equal(
            blending._restore_detail(generated, generated[:32]), generated
        )

    def test_output_stays_in_range(self):
        out = blending._restore_detail(_textured(seed=3), _textured(seed=4))
        self.assertEqual(out.dtype, np.uint8)
        self.assertGreaterEqual(int(out.min()), 0)
        self.assertLessEqual(int(out.max()), 255)


if __name__ == "__main__":
    unittest.main()
