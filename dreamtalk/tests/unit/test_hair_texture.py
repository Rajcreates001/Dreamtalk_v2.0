"""The hair carries the subject's own curls, from every side.

A colour per vertex got the hair's tone right and could not carry a curl, so
the shell read as a smooth mass. It now has UVs and a texture read off the
photograph. Two ways that goes wrong, both seen while building it:

  a straight projection squeezes every side-facing vertex into a thin band at
  the edge of the hair, so from the side the texture streaked along the head;

  back vertices project onto the FACE in the photograph, so without a fill
  they would wear skin.

These pin the texture being hair everywhere, the front coming from the
photograph, the sides keeping their spacing, and the exporter actually
writing a second image with UVs - the hair shell itself was once written,
committed and never run.
"""

import json
import os
import struct
import tempfile
import unittest

import numpy as np

from dreamtalk.pipeline.avatar_export import AvatarExporter
from dreamtalk.pipeline.face_hair import (
    HAIR_PROFILE_BINS, bake_hair_texture, build_hair,
)
from dreamtalk.tests.unit.test_hair_shell_profile import _Frame, _head

HAIR, SKIN = 17, 1
HAIR_RGB = np.array([40, 200, 60])        # unmistakable: green hair
SKIN_RGB = np.array([220, 140, 90])


def _photo(size=1024):
    """A square head crop and its parse: a face rectangle with a disc of hair."""
    parse = np.zeros((512, 512), np.uint8)
    parse[200:310, 206:306] = SKIN
    yy, xx = np.mgrid[0:512, 0:512]
    disc = ((yy - 200) ** 2 + (xx - 256) ** 2) <= (0.8 * 99) ** 2
    parse[disc & (parse == 0)] = HAIR
    big = np.kron(parse, np.ones((size // 512, size // 512), np.uint8))
    rng = np.random.default_rng(0)
    img = np.full((size, size, 3), 128, np.uint8)
    img[big == HAIR] = np.clip(HAIR_RGB + rng.integers(-20, 20, (int((big == HAIR).sum()), 3)),
                               0, 255)
    img[big == SKIN] = SKIN_RGB
    return img, parse


def _shell():
    verts, faces, masks = _head()
    part = build_hair(verts, faces, masks, _Frame(),
                      metrics={"profile": [0.80] * HAIR_PROFILE_BINS})["parts"][0]
    return verts, masks, part


def _bake():
    verts, masks, part = _shell()
    img, parse = _photo()
    uvs, tex = bake_hair_texture(np.asarray(part["vertices"], np.float64), verts, masks,
                                 _Frame(), img, parse, HAIR, size=512,
                                 shell_faces=part["faces"])
    return verts, part, uvs, tex


def _near(tex, rgb, tol=45):
    return np.abs(tex.astype(int) - rgb).max(axis=-1) < tol


class HairTexture(unittest.TestCase):
    def test_uvs_are_inside_the_texture(self):
        _, part, uvs, tex = _bake()
        self.assertEqual(uvs.shape, (len(part["vertices"]), 2))
        self.assertTrue(np.all((uvs >= 0) & (uvs <= 1)))
        self.assertEqual(tex.shape, (512, 512, 3))

    def test_the_texture_is_hair_everywhere(self):
        """No skin, no backdrop: the face and the surround are filled with tile."""
        _, _, _, tex = _bake()
        self.assertLess(float(_near(tex, SKIN_RGB).mean()), 0.01, "skin in the hair texture")
        self.assertLess(float(_near(tex, np.array([128, 128, 128]), 12).mean()), 0.01,
                        "backdrop in the hair texture")
        self.assertGreater(float(_near(tex, HAIR_RGB).mean()), 0.8)

    def test_the_front_samples_the_photograph_where_it_is(self):
        """Front-facing vertices keep their projected position: registration."""
        verts, part, uvs, tex = _bake()
        from dreamtalk.pipeline.face_hair import _vertex_normals
        n = _vertex_normals(np.asarray(part["vertices"], np.float64),
                            np.asarray(part["faces"], np.int64))
        front = n[:, 2] > 0.95
        self.assertGreater(int(front.sum()), 3)
        px = (uvs[front] * 511).astype(int)
        self.assertTrue(_near(tex[px[:, 1], px[:, 0]], HAIR_RGB).all())

    def test_the_sides_keep_their_spacing(self):
        """Edges running INTO the head, on its sides, must keep texture length.

        A front projection squeezes exactly those edges to nothing - which is
        what streaked. Edges running along the silhouette it leaves alone, so
        a median over all side edges could not tell the two apart (a first
        draft of this test passed the streaky version at 0.77).
        """
        verts, part, uvs, _ = _bake()
        v = np.asarray(part["vertices"], np.float64)
        f = np.asarray(part["faces"], np.int64)
        edges = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
        d3 = v[edges[:, 1]] - v[edges[:, 0]]
        length = np.linalg.norm(d3, axis=1)
        into = np.abs(d3[:, 2]) > 0.8 * length                    # runs in depth
        on_side = np.abs(v[edges].mean(axis=1)[:, 0]) > 0.35       # side of the head
        sel = into & on_side
        self.assertGreater(int(sel.sum()), 5)
        uv_len = np.linalg.norm(uvs[edges[sel, 1]] - uvs[edges[sel, 0]], axis=1)
        front = np.abs(d3[:, 2]) < 0.2 * length
        front &= np.abs(v[edges].mean(axis=1)[:, 0]) < 0.1
        ref = np.median(np.linalg.norm(uvs[edges[front, 1]] - uvs[edges[front, 0]], axis=1)
                        / length[front])
        ratio = float(np.median(uv_len / length[sel])) / ref
        self.assertGreater(ratio, 0.5,
                           "depth-running side edges keep %.2f of the front's "
                           "texel density" % ratio)


class ExporterWritesTheHairTexture(unittest.TestCase):
    def test_second_image_and_uvs_reach_the_file(self):
        import cv2

        d = tempfile.mkdtemp()
        obj = os.path.join(d, "head.obj")
        with open(obj, "w") as f:
            for p in ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)):
                f.write("v %f %f %f\n" % p)
            for tri in ((1, 2, 3), (1, 3, 4), (1, 4, 2), (2, 4, 3)):
                f.write("f %d %d %d\n" % tri)
        ok, enc = cv2.imencode(".jpg", np.full((8, 8, 3), 90, np.uint8))
        part = {"name": "hair",
                "vertices": np.array([[0, 1, 0], [1, 1, 0], [0, 2, 0]], np.float32),
                "faces": np.array([[0, 1, 2]], np.uint32),
                "uvs": np.array([[0, 0], [1, 0], [0, 1]], np.float32),
                "texture": enc.tobytes(), "texture_mime": "image/jpeg",
                "color": (1.0, 1.0, 1.0)}
        out = os.path.join(d, "out.glb")
        AvatarExporter().obj_to_glb(obj, None, out, extra_parts=[part])
        data = open(out, "rb").read()
        ln = struct.unpack_from("<I", data, 12)[0]
        js = json.loads(data[20:20 + ln])
        hair = [m for m in js["meshes"] if m["name"] == "hair"][0]["primitives"][0]
        self.assertIn("TEXCOORD_0", hair["attributes"])
        mat = js["materials"][hair["material"]]["pbrMetallicRoughness"]
        self.assertIn("baseColorTexture", mat)
        tex = js["textures"][mat["baseColorTexture"]["index"]]
        self.assertEqual(js["images"][tex["source"]]["mimeType"], "image/jpeg")


if __name__ == "__main__":
    unittest.main()
