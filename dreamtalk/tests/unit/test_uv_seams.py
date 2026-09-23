"""The head's UV seams must survive into the GLB.

FLAME has 5118 UVs for 5023 vertices: 95 vertices sit on a seam and carry a
different UV on each side of it. The export wrote one UV per vertex, so every
triangle straddling a seam took the wrong UV at one corner and stretched across
a third of the atlas - 136 such triangles down the back of the head.

glTF allows one UV per vertex, so seam vertices have to be duplicated, and the
duplicates must stay one surface: same position, same normal, same motion in
every morph target, or the head tears open along the seam when it blinks.
"""

import json
import os
import struct
import tempfile
import unittest

import numpy as np

from dreamtalk.pipeline.avatar_export import AvatarExporter, split_uv_seams


def _square():
    """Two triangles sharing vertex 1, which sits on a UV seam: each triangle
    gives it a different UV. (A first draft put the second UV on a vertex only
    one triangle uses - no seam at all - and the split rightly left it alone.)"""
    v = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], np.float32)
    n = np.tile([0, 0, 1], (4, 1)).astype(np.float32)
    uv = np.array([[0.0, 0.0], [0.5, 0.0], [0.0, 0.5], [0.5, 0.5],
                   [0.9, 0.9]], np.float32)            # vt 4: vertex 1's other UV
    faces = np.array([[0, 1, 2], [1, 3, 2]], np.uint32)
    face_uv = np.array([[0, 1, 2], [4, 3, 2]], np.uint32)
    morph = {"blink": np.array([[0, 0, 0], [0, 0, 0.1], [0, 0, 0], [0, 0, 0]], np.float32)}
    return v, n, uv, faces, face_uv, morph


class SplitUvSeams(unittest.TestCase):
    def test_each_corner_gets_its_own_uv(self):
        v, n, uv, faces, face_uv, morph = _square()
        ov, on, ouv, of, om = split_uv_seams(v, n, uv, faces, face_uv, morph)
        for fi in range(len(faces)):
            for k in range(3):
                np.testing.assert_allclose(ouv[of[fi, k]], uv[face_uv[fi, k]])
                np.testing.assert_allclose(ov[of[fi, k]], v[faces[fi, k]])

    def test_only_seam_vertices_are_duplicated(self):
        v, n, uv, faces, face_uv, morph = _square()
        ov, *_ = split_uv_seams(v, n, uv, faces, face_uv, morph)
        self.assertEqual(len(ov), 5)                    # four plus one twin

    def test_twins_move_together(self):
        v, n, uv, faces, face_uv, morph = _square()
        ov, on, ouv, of, om = split_uv_seams(v, n, uv, faces, face_uv, morph)
        twins = [i for i in range(len(ov))
                 if np.allclose(ov[i], v[1])]
        self.assertEqual(len(twins), 2)
        np.testing.assert_allclose(om["blink"][twins[0]], om["blink"][twins[1]])
        np.testing.assert_allclose(on[twins[0]], on[twins[1]])


class SeamsReachTheGlb(unittest.TestCase):
    def test_a_face_varying_obj_exports_split(self):
        d = tempfile.mkdtemp()
        obj = os.path.join(d, "head.obj")
        v, n, uv, faces, face_uv, morph = _square()
        with open(obj, "w") as f:
            for p in v:
                f.write("v %f %f %f\n" % tuple(p))
            for t in uv:
                f.write("vt %f %f\n" % tuple(t))
            for q in n:
                f.write("vn %f %f %f\n" % tuple(q))
            for fv, ft in zip(faces, face_uv):
                f.write("f " + " ".join("%d/%d/%d" % (a + 1, b + 1, a + 1)
                                        for a, b in zip(fv, ft)) + "\n")
        out = os.path.join(d, "head.glb")
        AvatarExporter().obj_to_glb(obj, None, out, morph_targets=morph)
        data = open(out, "rb").read()
        ln = struct.unpack_from("<I", data, 12)[0]
        js = json.loads(data[20:20 + ln])
        prim = js["meshes"][0]["primitives"][0]
        self.assertEqual(js["accessors"][prim["attributes"]["POSITION"]]["count"], 5)
        self.assertEqual(js["accessors"][prim["attributes"]["TEXCOORD_0"]]["count"], 5)
        self.assertEqual(js["accessors"][prim["targets"][0]["POSITION"]]["count"], 5)


if __name__ == "__main__":
    unittest.main()
