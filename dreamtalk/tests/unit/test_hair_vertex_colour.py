"""The hair shell carried one colour for 489 vertices.

A single baseColorFactor renders hair as a silhouette: no highlight where the
light falls, no darker mass underneath, no parting. It was tolerable while the
shell was a skullcap. Now that the shell is the size of the subject's actual
hair, the flat mass is bigger and reads worse.

The vertices are already spread across the hair, and the same mapping that
decides how far to push each one - face widths about the middle of the top of
the face - decides which pixel of the photograph it lands on. So each vertex
can carry the tone of the hair where it sits, as COLOR_0, which every glTF
renderer multiplies with baseColorFactor.

Two things are pinned: that the sampling reproduces the photograph's variation
rather than inventing it, and that the exporter actually writes the attribute -
the hair shell itself was written, committed and silently never run once, so
"the code exists" is not evidence that anything reaches the file.
"""

import json
import os
import struct
import tempfile
import unittest

import numpy as np

from dreamtalk.pipeline.avatar_export import AvatarExporter
from dreamtalk.pipeline.face_hair import sample_hair_vertex_colours

HAIR, SKIN = 17, 1


class _Frame:
    up, side, fwd = 1, 0, 2
    up_sign = 1.0
    fwd_sign = 1.0


def _scene():
    """A parse with a bright top half of hair and a dark bottom half."""
    parse = np.zeros((512, 512), np.uint8)
    parse[200:310, 206:306] = SKIN            # width 99, top row 200
    yy, xx = np.mgrid[0:512, 0:512]
    disc = ((yy - 200) ** 2 + (xx - 256) ** 2) <= (0.8 * 99) ** 2
    parse[disc & (parse == 0)] = HAIR

    img = np.zeros((512, 512, 3), np.uint8)
    img[parse == HAIR] = 40
    top = (parse == HAIR) & (yy < 170)
    img[top] = 200                            # a highlight across the crown
    return img, parse


def _head(radius=0.5):
    """Vertices on a shell above the face, and a face region to measure from."""
    face = np.array([[-radius, 0.18, 0.2], [radius, 0.18, 0.2],
                     [0.0, -0.5, 0.2], [0.0, 0.18, 0.2]], np.float64)
    shell = []
    for frac in (0.70, 0.35):
        for ang in np.radians([30, 60, 90, 120, 150]):
            shell.append([np.cos(ang) * frac * 2 * radius,
                          0.18 + np.sin(ang) * frac * 2 * radius, 0.0])
    verts = np.vstack([face, np.asarray(shell, np.float64)])
    masks = {"face": np.arange(4)}
    return verts, masks, np.asarray(shell, np.float64)


class SamplingFollowsThePhotograph(unittest.TestCase):
    def test_vertices_take_the_tone_where_they_land(self):
        img, parse = _scene()
        verts, masks, shell = _head()
        out = sample_hair_vertex_colours(shell, verts, masks, _Frame(),
                                         img, parse, HAIR)
        self.assertIsNotNone(out, "sampling declined on a clean synthetic hair")
        cols, factor = out
        self.assertEqual(cols.shape, (len(shell), 3))
        self.assertTrue(np.all((cols >= 0) & (cols <= 1)),
                        "COLOR_0 must stay inside 0..1 for a float accessor")
        # The outer ring reaches the highlight; the inner ring does not. A flat
        # colour cannot tell them apart, which is the whole point.
        outer = cols[:5].mean()
        inner = cols[5:].mean()
        self.assertGreater(outer, inner * 1.5,
                           "outer %.3f vs inner %.3f - no variation recovered"
                           % (outer, inner))

    def test_a_flat_head_of_hair_gives_a_flat_result(self):
        img, parse = _scene()
        img[parse == HAIR] = 40                # remove the highlight
        verts, masks, shell = _head()
        cols, _ = sample_hair_vertex_colours(shell, verts, masks, _Frame(),
                                             img, parse, HAIR)
        self.assertLess(float(cols.std()), 0.05,
                        "invented variation where the photograph has none")

    def test_the_shell_is_as_dark_as_the_hair_it_came_from(self):
        """Spread is not level.

        The first version of this got the variation right - 93% of the
        photograph's - and rendered black hair as a grey helmet, because a
        plain blur near the silhouette mixed in the pale backdrop and every
        rim vertex came back far too light. Matching the spread alone cannot
        catch that; the mean has to be checked too.
        """
        img, parse = _scene()
        verts, masks, shell = _head()
        cols, factor = sample_hair_vertex_colours(shell, verts, masks,
                                                  _Frame(), img, parse, HAIR)
        luma = np.array([0.299, 0.587, 0.114])

        def linear(x):
            x = np.asarray(x, np.float64)
            return np.where(x <= 0.04045, x / 12.92,
                            ((x + 0.055) / 1.055) ** 2.4)

        # cols * factor is already linear - it is what a renderer multiplies
        # and sends to the framebuffer. Converting it again is how the first
        # run of this test "failed": 0.0699 against 0.2538 was one sRGB
        # transform too many, not a dark shell.
        shell_mean = float(((cols * factor) @ luma).mean())
        photo_mean = float(
            (linear(img[parse == HAIR].astype(np.float64) / 255.0) @ luma).mean())
        self.assertLess(abs(shell_mean - photo_mean), photo_mean * 0.35,
                        "shell mean %.4f against the hair's %.4f"
                        % (shell_mean, photo_mean))

    def test_a_pale_background_does_not_lighten_the_rim(self):
        img, parse = _scene()
        img[parse == 0] = 245                  # a bright studio backdrop
        verts, masks, shell = _head()
        cols, factor = sample_hair_vertex_colours(shell, verts, masks,
                                                  _Frame(), img, parse, HAIR)
        self.assertLess(float((cols * factor).max()), 0.85,
                        "the backdrop bled into the shell")

    def test_no_hair_in_the_parse_declines(self):
        img, parse = _scene()
        parse[parse == HAIR] = 0
        verts, masks, shell = _head()
        self.assertIsNone(sample_hair_vertex_colours(
            shell, verts, masks, _Frame(), img, parse, HAIR))

    def test_missing_photo_declines(self):
        _, parse = _scene()
        verts, masks, shell = _head()
        self.assertIsNone(sample_hair_vertex_colours(
            shell, verts, masks, _Frame(), None, parse, HAIR))


def _read_glb(path):
    data = open(path, "rb").read()
    off, js = 12, None
    while off < len(data):
        ln, ty = struct.unpack_from("<II", data, off)
        off += 8
        if ty == 0x4E4F534A:
            js = json.loads(data[off:off + ln])
        off += ln
    return js


class ExporterWritesTheAttribute(unittest.TestCase):
    def _export(self, part):
        d = tempfile.mkdtemp()
        obj = os.path.join(d, "head.obj")
        with open(obj, "w") as f:
            for v in ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)):
                f.write("v %f %f %f\n" % v)
            for tri in ((1, 2, 3), (1, 3, 4), (1, 4, 2), (2, 4, 3)):
                f.write("f %d %d %d\n" % tri)
        out = os.path.join(d, "out.glb")
        AvatarExporter().obj_to_glb(obj, None, out, extra_parts=[part])
        return _read_glb(out)

    def _part(self, colors=None):
        p = {
            "name": "hair",
            "vertices": np.array([[0, 1, 0], [1, 1, 0], [0, 2, 0]], np.float32),
            "faces": np.array([[0, 1, 2]], np.uint32),
            "color": (0.1, 0.09, 0.07),
        }
        if colors is not None:
            p["colors"] = colors
        return p

    def test_color_0_reaches_the_file(self):
        js = self._export(self._part(
            np.array([[1.0, 1.0, 1.0], [0.5, 0.5, 0.5], [0.2, 0.2, 0.2]])))
        hair = [m for m in js["meshes"] if m.get("name") == "hair"][0]
        attrs = hair["primitives"][0]["attributes"]
        self.assertIn("COLOR_0", attrs, "the attribute never reached the GLB")
        acc = js["accessors"][attrs["COLOR_0"]]
        self.assertEqual(acc["type"], "VEC3")
        self.assertEqual(acc["count"], 3)

    def test_without_colours_nothing_changes(self):
        js = self._export(self._part())
        hair = [m for m in js["meshes"] if m.get("name") == "hair"][0]
        self.assertNotIn("COLOR_0", hair["primitives"][0]["attributes"])

    def test_a_wrong_length_array_is_ignored(self):
        js = self._export(self._part(np.zeros((2, 3))))
        hair = [m for m in js["meshes"] if m.get("name") == "hair"][0]
        self.assertNotIn("COLOR_0", hair["primitives"][0]["attributes"])


if __name__ == "__main__":
    unittest.main()
