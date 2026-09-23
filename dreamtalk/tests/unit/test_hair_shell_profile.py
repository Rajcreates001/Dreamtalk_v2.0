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
    """A closed UV sphere with single poles - a stand-in skull.

    Single poles matter. Stacking nu coincident vertices at each pole gives
    zero-length edges, and an edge of no length can carry no difference in
    thickness, so the fold clamp propagates the smallest value around the
    whole ring and the shell comes out half height. That is the test mesh
    misleading the test, which is the failure mode this whole file exists to
    avoid.
    """
    verts = [[0.0, r, 0.0]]
    for i in range(1, nv):
        phi = np.pi * i / nv
        for j in range(nu):
            th = 2.0 * np.pi * j / nu
            verts.append([r * np.sin(phi) * np.cos(th),
                          r * np.cos(phi),
                          r * np.sin(phi) * np.sin(th)])
    verts.append([0.0, -r, 0.0])
    south = len(verts) - 1

    def ring(i, j):
        return 1 + (i - 1) * nu + (j % nu)

    faces = []
    for j in range(nu):
        faces.append([0, ring(1, j + 1), ring(1, j)])
    for i in range(1, nv - 1):
        for j in range(nu):
            a, b = ring(i, j), ring(i, j + 1)
            c, d = ring(i + 1, j), ring(i + 1, j + 1)
            faces.append([a, c, b])
            faces.append([b, c, d])
    for j in range(nu):
        faces.append([south, ring(nv - 1, j), ring(nv - 1, j + 1)])
    faces = np.asarray(faces, np.int64)

    # Wind every face outward. Written by hand the rings came out facing IN -
    # 1152 of 1216 faces - so every vertex normal pointed into the skull and
    # the shell was offset inwards, folding itself inside out. The builder was
    # doing exactly what it was told; the sphere was inside out.
    verts = np.asarray(verts, np.float64)
    tri = verts[faces]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    flip = (fn * tri.mean(axis=1)).sum(axis=1) < 0
    faces[flip] = faces[flip][:, ::-1]
    return verts, faces


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


def _dihedral(part):
    """The angle between neighbouring faces - how folded the shell is."""
    from collections import defaultdict
    v = np.asarray(part["vertices"], np.float64)
    f = np.asarray(part["faces"], np.int64)
    tri = v[f]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    em = defaultdict(list)
    for i, (a, b, c) in enumerate(f):
        for e in ((a, b), (b, c), (c, a)):
            em[(min(e), max(e))].append(i)
    return np.asarray([
        np.degrees(np.arccos(float(np.clip(fn[x[0]] @ fn[x[1]], -1, 1))))
        for x in em.values() if len(x) == 2])


class ShellCoversTheHair(unittest.TestCase):
    def test_the_silhouette_reaches_the_profile(self):
        verts, faces, masks = _head()
        want = 0.70
        built = build_hair(verts, faces, masks, _Frame(),
                           metrics={"width_ratio": 1.35,
                                    "profile": [want] * HAIR_PROFILE_BINS})
        self.assertIsNotNone(built)
        reach = _shell_reach(built["parts"][0], verts, masks)
        self.assertGreater(reach, want * 0.75,
                           "shell reached %.3f face widths, asked for %.2f"
                           % (reach, want))

    def test_a_taller_profile_builds_a_taller_shell(self):
        verts, faces, masks = _head()
        reaches = [
            _shell_reach(build_hair(verts, faces, masks, _Frame(),
                                    metrics={"profile": [r] * HAIR_PROFILE_BINS}
                                    )["parts"][0], verts, masks)
            for r in (0.45, 0.70, 0.95)
        ]
        self.assertTrue(reaches[0] < reaches[1] < reaches[2], reaches)


class ShellIsShapedLikeHair(unittest.TestCase):
    """The checks that would have caught the disc.

    The first profile-driven shell pushed every vertex outward in the frontal
    plane. Head on it covered 84% of the photograph's hair and every number
    said it was right. Turned thirty degrees it was a brim standing out past
    the head, because every metric was a frontal one and a frontal metric
    cannot see the shape of what it scores. These two are not frontal.
    """

    def test_the_shell_wraps_the_head_rather_than_standing_out_from_it(self):
        verts, faces, masks = _head()
        part = build_hair(verts, faces, masks, _Frame(),
                          metrics={"profile": [0.80] * HAIR_PROFILE_BINS}
                          )["parts"][0]
        sv = np.asarray(part["vertices"], np.float64)
        head_depth = float(verts[:, 2].max() - verts[:, 2].min())
        past = max(float(sv[:, 2].max()) - float(verts[:, 2].max()),
                   float(verts[:, 2].min()) - float(sv[:, 2].min()))
        self.assertLess(past, head_depth * 0.35,
                        "shell reaches %.3f past the head, %.0f%% of its depth"
                        % (past, 100 * past / head_depth))

    def test_nothing_is_left_folded(self):
        verts, faces, masks = _head()
        part = build_hair(verts, faces, masks, _Frame(),
                          metrics={"profile": [0.80] * HAIR_PROFILE_BINS}
                          )["parts"][0]
        ang = _dihedral(part)
        self.assertLess(float(ang.max()), 90.0,
                        "worst dihedral %.0f deg - a triangle has folded over"
                        % ang.max())

    def test_the_rim_stays_on_the_scalp(self):
        # Hair thickness at the hairline is zero. Without that the rim stands
        # off the head by its own thickness and the hair floats with daylight
        # under it.
        verts, faces, masks = _head()
        part = build_hair(verts, faces, masks, _Frame(),
                          metrics={"profile": [0.80] * HAIR_PROFILE_BINS}
                          )["parts"][0]
        sv = np.asarray(part["vertices"], np.float64)
        scalp = verts[np.asarray(masks["scalp"], np.int64)]
        low = scalp[:, 1].min()
        near_rim = sv[sv[:, 1] < low + 0.02]
        self.assertGreater(len(near_rim), 0)
        radius = np.linalg.norm(near_rim[:, [0, 2]], axis=1)
        self.assertLess(float(radius.max()), 0.56,
                        "the rim has lifted off the skull")

    def test_the_shell_never_coincides_with_the_scalp(self):
        """A surface lying on another is drawn as whichever the depth buffer
        prefers, pixel by pixel. Sealing the rim at zero thickness did exactly
        that along the nape and it rendered as dark and skin-coloured blocks
        down the neck - stripes no texture fix could touch."""
        verts, faces, masks = _head()
        part = build_hair(verts, faces, masks, _Frame(),
                          metrics={"profile": [0.80] * HAIR_PROFILE_BINS}
                          )["parts"][0]
        sv = np.asarray(part["vertices"], np.float64)
        # On the sphere the scalp is at radius 0.5; every shell vertex must
        # stand clear of it.
        clearance = np.linalg.norm(sv, axis=1) - 0.5
        self.assertGreater(float(clearance.min()), 0.002,
                           "shell touches the scalp: min clearance %.4f"
                           % clearance.min())

    def test_the_hair_stops_at_the_nape(self):
        """FLAME's scalp runs down to the base of the neck. Hair does not."""
        verts, faces, masks = _head()
        y = verts[:, 1]
        masks = dict(masks,
                     scalp=np.nonzero(y > -0.35)[0],
                     left_ear=np.nonzero((np.abs(y) < 0.05) & (verts[:, 0] > 0.45))[0],
                     right_ear=np.nonzero((np.abs(y) < 0.05) & (verts[:, 0] < -0.45))[0])
        part = build_hair(verts, faces, masks, _Frame(),
                          metrics={"width_ratio": 1.35})["parts"][0]
        lobe = min(y[masks["left_ear"]].min(), y[masks["right_ear"]].min())
        sv = np.asarray(part["vertices"], np.float64)
        self.assertGreater(float(sv[:, 1].min()), lobe - 0.1,
                           "hair runs %.3f below the ear lobes" % (lobe - sv[:, 1].min()))

    def test_the_shell_carries_normals(self):
        verts, faces, masks = _head()
        part = build_hair(verts, faces, masks, _Frame(),
                          metrics={"profile": [0.70] * HAIR_PROFILE_BINS}
                          )["parts"][0]
        n = part.get("normals")
        self.assertIsNotNone(n, "shell shipped with no normals at all")
        self.assertEqual(len(n), len(part["vertices"]))
        self.assertTrue(np.allclose(np.linalg.norm(np.asarray(n, np.float64),
                                                   axis=1), 1.0, atol=1e-3))


class Fallbacks(unittest.TestCase):
    def test_without_a_profile_it_still_builds_a_shell(self):
        verts, faces, masks = _head()
        built = build_hair(verts, faces, masks, _Frame(),
                           metrics={"width_ratio": 1.35})
        self.assertIsNotNone(built)
        self.assertEqual(built["parts"][0]["name"], "hair")
        self.assertGreater(_shell_reach(built["parts"][0], verts, masks), 0.0)

    def test_no_scalp_region_is_survivable(self):
        verts, faces, masks = _head()
        masks = dict(masks, scalp=np.asarray([], np.int64))
        self.assertIsNone(build_hair(verts, faces, masks, _Frame()))


if __name__ == "__main__":
    unittest.main()
