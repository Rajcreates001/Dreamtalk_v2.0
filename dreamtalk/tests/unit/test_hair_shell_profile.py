"""The hair shell has to reach the subject's hair, not hug their skull.

The shell used to be a single outward offset sized from one number, the ratio
of the hair's width to the face's. A head of hair is not described by one
number: measured on a real subject the shell reached 0.43 face widths at the
crown where the hair reaches 0.64, while at the sides it was already right, so
no single offset could fix the crown without overshooting the sides. Recall
against the segmented hair was 0.46.

These tests pin the two halves of the replacement:

  the measurement   a radius per direction, in face widths, read off the
                    segmentation
  the construction  each scalp vertex pushed out to the radius its own
                    direction asks for

Both assertions are written so the previous construction fails them: a shell
that ignores the profile does not reach the profile's radius, and it is the
distance reached, not the fact that a shell exists, that is checked.
"""

import unittest

import numpy as np

from dreamtalk.pipeline.face_hair import (
    HAIR_PROFILE_BINS,
    MAX_HAIR_RADIUS,
    build_hair,
    hair_metrics_from_parsing,
)

HAIR, SKIN = 17, 1


class _Frame:
    """The axes build_hair expects, as face_blendshapes reports them."""

    up, side, fwd = 1, 0, 2
    up_sign = 1.0
    fwd_sign = 1.0


def _sphere(nu=32, nv=20, r=0.5):
    """A closed UV sphere - a stand-in skull with real faces and normals."""
    verts = []
    for i in range(nv + 1):
        phi = np.pi * i / nv
        for j in range(nu):
            th = 2.0 * np.pi * j / nu
            verts.append([r * np.sin(phi) * np.cos(th),
                          r * np.cos(phi),
                          r * np.sin(phi) * np.sin(th)])
    faces = []
    for i in range(nv):
        for j in range(nu):
            a, b = i * nu + j, i * nu + (j + 1) % nu
            c, d = (i + 1) * nu + j, (i + 1) * nu + (j + 1) % nu
            faces.append([a, c, b])
            faces.append([b, c, d])
    return np.asarray(verts, np.float64), np.asarray(faces, np.int64)


def _head():
    verts, faces = _sphere()
    y, z = verts[:, 1], verts[:, 2]
    scalp = np.nonzero(y > 0.08)[0]
    face = np.nonzero((y < 0.18) & (y > -0.45) & (z > -0.05))[0]
    masks = {
        "scalp": scalp,
        "face": face,
        "forehead": np.nonzero(y > 0.3)[0],
        "neck": np.nonzero(y < -0.4)[0],
        "nose": np.nonzero((z > 0.4) & (np.abs(y) < 0.1))[0],
    }
    return verts, faces, masks


def _shell_reach(part, verts, masks):
    """How far the shell's top rises above the top of the face, in face widths."""
    face = verts[masks["face"]]
    width = float(face[:, 0].max() - face[:, 0].min())
    top = float(face[:, 1].max())
    return (float(np.asarray(part["vertices"])[:, 1].max()) - top) / width


class RadialProfileMeasurement(unittest.TestCase):
    def _parse(self, radius_ratio):
        """A square parse: a face rectangle with a disc of hair around it."""
        img = np.zeros((512, 512), np.uint8)
        img[200:310, 206:306] = SKIN              # width 99, top row 200
        cy, cx = 200, 256
        rad = radius_ratio * 99.0
        yy, xx = np.mgrid[0:512, 0:512]
        disc = ((yy - cy) ** 2 + (xx - cx) ** 2) <= rad * rad
        img[disc & (img == 0)] = HAIR
        return img

    def test_profile_reports_the_radius_the_hair_reaches(self):
        m = hair_metrics_from_parsing(self._parse(0.80), HAIR, SKIN)
        self.assertIsNotNone(m)
        prof = np.asarray(m["profile"], float)
        self.assertEqual(len(prof), HAIR_PROFILE_BINS)
        # Every direction above the brow line sees the same disc, so every one
        # of those bins must read its radius back.
        upper = prof[HAIR_PROFILE_BINS // 4: 3 * HAIR_PROFILE_BINS // 4]
        self.assertTrue(np.all(np.abs(upper - 0.80) < 0.06),
                        "profile read %s, expected ~0.80" % np.round(upper, 3))

    def test_profile_tracks_a_bigger_head_of_hair(self):
        small = np.asarray(hair_metrics_from_parsing(
            self._parse(0.60), HAIR, SKIN)["profile"], float)
        large = np.asarray(hair_metrics_from_parsing(
            self._parse(1.00), HAIR, SKIN)["profile"], float)
        mid = slice(HAIR_PROFILE_BINS // 4, 3 * HAIR_PROFILE_BINS // 4)
        self.assertGreater(large[mid].mean() - small[mid].mean(), 0.3)

    def test_absurd_segmentation_is_clamped(self):
        # A dark background parsed as hair must not be allowed to ask for a
        # shell the size of the frame.
        prof = hair_metrics_from_parsing(self._parse(3.0), HAIR, SKIN)["profile"]
        self.assertLessEqual(max(prof), MAX_HAIR_RADIUS + 1e-9)

    def test_no_hair_gives_no_metrics(self):
        img = np.zeros((512, 512), np.uint8)
        img[200:310, 206:306] = SKIN
        self.assertIsNone(hair_metrics_from_parsing(img, HAIR, SKIN))


class ShellReachesTheProfile(unittest.TestCase):
    def test_shell_is_pushed_out_to_the_profile_radius(self):
        verts, faces, masks = _head()
        want = 0.70
        built = build_hair(verts, faces, masks, _Frame(),
                           metrics={"width_ratio": 1.35,
                                    "profile": [want] * HAIR_PROFILE_BINS})
        self.assertIsNotNone(built)
        reach = _shell_reach(built["parts"][0], verts, masks)
        self.assertAlmostEqual(reach, want, delta=0.05,
                               msg="shell reached %.3f face widths, asked for "
                                   "%.2f" % (reach, want))

    def test_a_taller_profile_builds_a_taller_shell(self):
        verts, faces, masks = _head()
        reaches = [
            _shell_reach(build_hair(verts, faces, masks, _Frame(),
                                    metrics={"profile": [r] * HAIR_PROFILE_BINS}
                                    )["parts"][0], verts, masks)
            for r in (0.45, 0.70, 0.95)
        ]
        self.assertTrue(reaches[0] < reaches[1] < reaches[2], reaches)

    def test_a_direction_that_asks_for_nothing_is_not_pushed(self):
        # Half the profile flat against the face, half tall. The shell must be
        # lopsided, which a uniform offset cannot be.
        verts, faces, masks = _head()
        prof = [0.05] * (HAIR_PROFILE_BINS // 2) + [0.95] * (HAIR_PROFILE_BINS // 2)
        part = build_hair(verts, faces, masks, _Frame(),
                          metrics={"profile": prof})["parts"][0]
        xs = np.asarray(part["vertices"])[:, 0]
        self.assertGreater(abs(float(xs.max()) + float(xs.min())), 0.15,
                           "shell came out symmetric on an asymmetric profile")

    def test_without_a_profile_it_still_builds_the_old_shell(self):
        verts, faces, masks = _head()
        built = build_hair(verts, faces, masks, _Frame(),
                           metrics={"width_ratio": 1.35})
        self.assertIsNotNone(built)
        self.assertEqual(built["parts"][0]["name"], "hair")
        # and that fallback is the thing the profile beats
        fallback = _shell_reach(built["parts"][0], verts, masks)
        radial = _shell_reach(
            build_hair(verts, faces, masks, _Frame(),
                       metrics={"width_ratio": 1.35,
                                "profile": [0.70] * HAIR_PROFILE_BINS}
                       )["parts"][0], verts, masks)
        self.assertGreater(radial, fallback + 0.2)

    def test_no_scalp_region_is_survivable(self):
        verts, faces, masks = _head()
        masks = dict(masks, scalp=np.asarray([], np.int64))
        self.assertIsNone(build_hair(verts, faces, masks, _Frame()))


if __name__ == "__main__":
    unittest.main()
