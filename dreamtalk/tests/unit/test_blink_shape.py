"""The blink has to close the eye, and only the eyelid may do it.

The shipped blink moved every vertex of FLAME's eye region straight down,
weighted by how high it sat in the region - so the vertices that moved most
were at the top, which is the brow. On a fitted head the brow slid 31 mm, its
hair smeared into a dark block over each eye, and the eyeballs stayed 43-55%
uncovered: it never closed. The browser fires it every few seconds, and
nothing tested it.

The replacement rotates each upper lid about its eyeball's centre until it
meets the lower lid. These tests use synthetic geometry (the FLAME files are
not in the repository): a head sphere for orientation, two eyeballs, and around
each a lid shell with a real aperture between upper and lower lid, plus a brow
strip above. They pin the three things that were wrong - the aperture closes,
the brow stays, nothing sinks into the eyeball - and the old construction fails
the first two.
"""

import unittest

import numpy as np

from dreamtalk.pipeline import face_blendshapes as fb

EYE_R = 0.055
EYES = {"left": np.array([0.15, 0.08, 0.40]), "right": np.array([-0.15, 0.08, 0.40])}
LID_R = EYE_R * 1.06


def _sphere(c, r, nu=24, nv=14):
    out = []
    for i in range(1, nv):
        phi = np.pi * i / nv
        for j in range(nu):
            th = 2 * np.pi * j / nu
            out.append(c + r * np.array([np.sin(phi) * np.cos(th), np.cos(phi),
                                         np.sin(phi) * np.sin(th)]))
    out.append(c + [0, r, 0])
    out.append(c - [0, r, 0])
    return np.asarray(out)


def _shell(c, r, elev_deg, azim_deg=(-55, 55), n=(9, 12)):
    """Points on a sphere about c at the given elevations above straight ahead."""
    out = []
    for e in np.radians(np.linspace(*elev_deg, n[0])):
        for a in np.radians(np.linspace(*azim_deg, n[1])):
            out.append(c + r * np.array([np.cos(e) * np.sin(a), np.sin(e),
                                         np.cos(e) * np.cos(a)]))
    return np.asarray(out)


def _scene():
    head = _sphere(np.zeros(3), 0.5, nu=32, nv=20)
    parts, masks, n = [head], {}, len(head)
    x, y, z = head[:, 0], head[:, 1], head[:, 2]
    masks["forehead"] = np.nonzero((y > 0.3) & (z > 0.2))[0]
    masks["neck"] = np.nonzero(y < -0.4)[0]
    masks["nose"] = np.nonzero((z > 0.45) & (np.abs(x) < 0.06) & (y > -0.12) & (y < 0.02))[0]
    masks["lips"] = np.nonzero((z > 0.35) & (np.abs(x) < 0.13) & (y > -0.27) & (y < -0.13))[0]
    masks["face"] = np.nonzero(z > 0.1)[0]
    groups = {}
    for side, c in EYES.items():
        ball = _sphere(c, EYE_R)
        upper = _shell(c, LID_R, (10, 55))
        lower = _shell(c, LID_R, (-55, -10))
        brow = _shell(c, LID_R * 1.1, (65, 80))
        idx = {}
        for name, pts in (("ball", ball), ("upper", upper), ("lower", lower), ("brow", brow)):
            idx[name] = np.arange(n, n + len(pts))
            parts.append(pts)
            n += len(pts)
        masks[side + "_eyeball"] = idx["ball"]
        masks[side + "_eye_region"] = np.concatenate([idx["upper"], idx["lower"], idx["brow"]])
        groups[side] = idx
    return np.vstack(parts).astype(np.float32), masks, groups


def _elev(p, c):
    return np.degrees(np.arctan2(p[:, 1] - c[1], p[:, 2] - c[2]))


def _blink(verts, masks, weight=1.0):
    return verts + weight * fb.build_blendshapes(verts, masks, shapes=("blink",))["blink"]


class LidRotationBlink(unittest.TestCase):
    def setUp(self):
        self.v, self.masks, self.groups = _scene()

    def test_the_aperture_closes(self):
        shut = _blink(self.v, self.masks)
        for side, c in EYES.items():
            g = self.groups[side]
            gap_before = _elev(self.v[g["upper"]], c).min() - _elev(self.v[g["lower"]], c).max()
            gap_after = _elev(shut[g["upper"]], c).min() - _elev(shut[g["lower"]], c).max()
            self.assertGreater(gap_before, 15.0)
            self.assertLess(gap_after, 2.0,
                            "%s eye still open by %.1f deg at full blink" % (side, gap_after))

    def test_the_brow_stays_where_it_is(self):
        d = fb.build_blendshapes(self.v, self.masks, shapes=("blink",))["blink"]
        for side in EYES:
            g = self.groups[side]
            margin = np.linalg.norm(d[g["upper"]], axis=1).max()
            brow = np.linalg.norm(d[g["brow"]], axis=1).max()
            self.assertLess(brow, 0.05 * margin,
                            "%s brow moves %.4f against a lid margin of %.4f"
                            % (side, brow, margin))

    def test_nothing_sinks_into_the_eyeball(self):
        shut = _blink(self.v, self.masks)
        for side, c in EYES.items():
            g = self.groups[side]
            lid = np.concatenate([g["upper"], g["lower"]])
            self.assertGreaterEqual(float(np.linalg.norm(shut[lid] - c, axis=1).min()),
                                    EYE_R * 0.999)

    def test_half_a_blink_is_half_closed(self):
        half = _blink(self.v, self.masks, 0.5)
        for side, c in EYES.items():
            g = self.groups[side]
            gap0 = _elev(self.v[g["upper"]], c).min() - _elev(self.v[g["lower"]], c).max()
            gap = _elev(half[g["upper"]], c).min() - _elev(half[g["lower"]], c).max()
            self.assertTrue(0.3 * gap0 < gap < 0.7 * gap0, (gap0, gap))

    def test_surprise_still_lifts_the_brows(self):
        # eyes_wide keeps the old whole-region lift: right for surprise.
        d = fb.build_blendshapes(self.v, self.masks, shapes=("surprised",))["surprised"]
        brow = np.concatenate([self.groups[s]["brow"] for s in EYES])
        self.assertGreater(float(d[brow, 1].mean()), 0.0)


if __name__ == "__main__":
    unittest.main()
