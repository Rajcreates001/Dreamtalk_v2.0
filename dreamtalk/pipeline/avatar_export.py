"""
DreamTalk — Avatar Export

Converts FLAME/OBJ face meshes to modern 3D formats:
  - GLB (glTF Binary) — for Three.js, web viewers
  - FBX — for Blender, Unreal Engine

Uses trimesh + pygltflib for GLB export (no Blender dependency needed).

Usage:
    exporter = AvatarExporter()
    glb_path = exporter.obj_to_glb(obj_path, texture_path, output_path)
    # → output.glb ready for Three.js
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

import numpy as np

logger = logging.getLogger("dreamtalk.avatar_export")


def split_uv_seams(vertices, normals, uvs, faces, face_uv, morph_targets=None):
    """Give every distinct (vertex, UV) pair its own glTF vertex.

    glTF has one UV per vertex. A mesh whose UV layout has seams - FLAME's has
    95 seam vertices, 5118 UVs for 5023 positions - therefore has to duplicate
    each seam vertex once per UV it carries. The duplicates share a position,
    a normal and every morph delta, so the head still deforms as one surface;
    only the texture lookup differs on either side of the seam.

    Returns (vertices, normals, uvs, faces, morph_targets) in the split
    numbering. Normals and morph deltas are carried by the ORIGINAL vertex
    index, which is what keeps the duplicates from tearing apart when the
    head blinks or speaks.
    """
    faces = np.asarray(faces, dtype=np.int64)
    face_uv = np.asarray(face_uv, dtype=np.int64)
    pairs = np.stack([faces.reshape(-1), face_uv.reshape(-1)], axis=1)
    uniq, inverse = np.unique(pairs, axis=0, return_inverse=True)
    inverse = np.asarray(inverse).reshape(-1)
    src = uniq[:, 0]
    out_v = np.asarray(vertices)[src]
    out_n = (np.asarray(normals)[src]
             if len(normals) == len(vertices) else np.zeros((0, 3), np.float32))
    out_uv = np.asarray(uvs)[uniq[:, 1]]
    out_f = inverse.reshape(-1, 3).astype(np.uint32)
    out_m = None
    if morph_targets:
        out_m = {name: np.asarray(d)[src] for name, d in morph_targets.items()
                 if np.asarray(d).shape == np.asarray(vertices).shape}
    logger.info("UV seams split: %d vertices -> %d (%d duplicated on seams)",
                len(vertices), len(out_v), len(out_v) - len(np.unique(src)))
    return out_v, out_n, out_uv, out_f, out_m


class AvatarExporter:
    """Export 3D face meshes to GLB/FBX format."""

    def obj_to_glb(
        self,
        obj_path: str,
        texture_path: Optional[str] = None,
        output_path: Optional[str] = None,
        metadata: Optional[Dict] = None,
        morph_targets: Optional[Dict[str, np.ndarray]] = None,
        extra_parts: Optional[list] = None,
    ) -> str:
        """Convert OBJ mesh to GLB (glTF Binary).

        Args:
            obj_path: Path to .obj file.
            texture_path: Optional path to texture image (.jpg/.png).
            output_path: Output .glb path. If None, replaces .obj extension.
            metadata: Optional metadata dict to embed in GLB.
            morph_targets: Optional ``{name: (N,3) delta}`` blendshapes. These
                become glTF morph targets so a browser can animate the head
                (visemes, blink, smile) without re-rendering server-side.

        Returns:
            Path to the generated .glb file.
        """
        if output_path is None:
            output_path = str(Path(obj_path).with_suffix(".glb"))

        # Native writer first: no third-party dependency, and the only path
        # that can emit morph targets. trimesh/pygltflib remain as fallbacks.
        try:
            vertices, normals, uvs, faces, face_uv = self._parse_obj_full(obj_path)
            if face_uv is not None:
                vertices, normals, uvs, faces, morph_targets = split_uv_seams(
                    vertices, normals, uvs, faces, face_uv, morph_targets)
            return self._export_glb_native(
                vertices, normals, uvs, faces,
                texture_path, output_path, metadata, morph_targets,
                extra_parts,
            )
        except Exception as exc:
            logger.warning("Native GLB export failed (%s) — falling back", exc)

        try:
            return self._export_with_pygltflib(
                obj_path, texture_path, output_path, metadata
            )
        except Exception as exc:
            logger.warning("pygltflib export unavailable (%s) — trying trimesh", exc)
            try:
                return self._export_with_trimesh(
                    obj_path, texture_path, output_path
                )
            except Exception as exc2:
                logger.warning("trimesh export unavailable (%s) — raw OBJ copy", exc2)
                return self._export_raw(obj_path, output_path)

    # ── Native glTF 2.0 binary writer ────────────────────────────────
    # Written by hand so the export has no third-party dependency and so we
    # can emit morph targets, which neither the trimesh nor the raw fallback
    # can produce.

    def _export_glb_native(
        self,
        vertices: np.ndarray,
        normals: np.ndarray,
        uvs: np.ndarray,
        faces: np.ndarray,
        texture_path: Optional[str],
        output_path: str,
        metadata: Optional[Dict],
        morph_targets: Optional[Dict[str, np.ndarray]] = None,
        extra_parts: Optional[list] = None,
    ) -> str:
        import json
        import struct

        if len(vertices) == 0 or len(faces) == 0:
            raise ValueError("mesh has no geometry to export")

        blob = bytearray()
        buffer_views: list = []
        accessors: list = []

        def add_view(data: bytes, target: Optional[int] = None) -> int:
            while len(blob) % 4:          # accessors must be 4-byte aligned
                blob.append(0)
            view = {"buffer": 0, "byteOffset": len(blob), "byteLength": len(data)}
            if target is not None:
                view["target"] = target
            blob.extend(data)
            buffer_views.append(view)
            return len(buffer_views) - 1

        def add_accessor(arr: np.ndarray, kind: str, comp: int,
                         target: Optional[int], minmax: bool = False) -> int:
            view = add_view(arr.tobytes(), target)
            acc = {"bufferView": view, "componentType": comp,
                   "count": int(arr.shape[0]), "type": kind}
            if minmax:
                acc["min"] = [float(x) for x in arr.min(axis=0)]
                acc["max"] = [float(x) for x in arr.max(axis=0)]
            accessors.append(acc)
            return len(accessors) - 1

        FLOAT, UINT = 5126, 5125
        ARRAY_BUF, ELEM_BUF = 34962, 34963

        pos = np.ascontiguousarray(vertices, dtype=np.float32)
        attributes = {"POSITION": add_accessor(pos, "VEC3", FLOAT, ARRAY_BUF, minmax=True)}
        if len(normals) == len(vertices) and len(normals) > 0:
            attributes["NORMAL"] = add_accessor(
                np.ascontiguousarray(normals, dtype=np.float32), "VEC3", FLOAT, ARRAY_BUF)
        if len(uvs) == len(vertices) and len(uvs) > 0:
            attributes["TEXCOORD_0"] = add_accessor(
                np.ascontiguousarray(uvs, dtype=np.float32), "VEC2", FLOAT, ARRAY_BUF)

        idx = np.ascontiguousarray(faces, dtype=np.uint32).reshape(-1)
        index_accessor = add_accessor(idx, "SCALAR", UINT, ELEM_BUF)

        primitive: Dict[str, Any] = {"attributes": attributes, "indices": index_accessor}

        # Morph targets — the whole point of the native writer.
        target_names: list = []
        if morph_targets:
            targets = []
            for name, delta in morph_targets.items():
                d = np.ascontiguousarray(delta, dtype=np.float32)
                if d.shape != pos.shape:
                    logger.warning("morph target %s has shape %s, expected %s — skipped",
                                   name, d.shape, pos.shape)
                    continue
                targets.append({"POSITION": add_accessor(d, "VEC3", FLOAT, ARRAY_BUF, minmax=True)})
                target_names.append(name)
            if targets:
                primitive["targets"] = targets

        gltf: Dict[str, Any] = {
            "asset": {"version": "2.0", "generator": "DreamTalk AvatarExporter"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0, "name": "Head"}],
            "meshes": [{"primitives": [primitive], "name": "Head"}],
        }
        if target_names:
            gltf["meshes"][0]["weights"] = [0.0] * len(target_names)
            gltf["meshes"][0]["extras"] = {"targetNames": target_names}

        # Extra solid-coloured parts (teeth, tongue). Each becomes its own mesh
        # + node so it can carry its own material and morph targets — FLAME has
        # no mouth interior, so without these an open viseme shows a void.
        extra_materials: list = []
        for part in (extra_parts or []):
            p_pos = np.ascontiguousarray(part["vertices"], dtype=np.float32)
            p_idx = np.ascontiguousarray(part["faces"], dtype=np.uint32).reshape(-1)
            p_attrs = {"POSITION": add_accessor(p_pos, "VEC3", FLOAT, ARRAY_BUF, minmax=True)}
            # Per-vertex colour, when the part brought one. glTF renderers
            # multiply COLOR_0 by baseColorFactor, so a part that carries both
            # still shows its flat colour in a viewer that ignores COLOR_0 -
            # which is why the factor is set to the part's brightest tone and
            # the attribute holds each vertex relative to it, rather than the
            # other way round. Float COLOR_0 must stay within 0..1.
            p_nrm = part.get("normals")
            if p_nrm is not None and len(p_nrm) == len(p_pos):
                p_attrs["NORMAL"] = add_accessor(
                    np.ascontiguousarray(p_nrm, dtype=np.float32),
                    "VEC3", FLOAT, ARRAY_BUF)
            p_col = part.get("colors")
            if p_col is not None and len(p_col) == len(p_pos):
                p_attrs["COLOR_0"] = add_accessor(
                    np.ascontiguousarray(np.clip(p_col, 0.0, 1.0),
                                         dtype=np.float32),
                    "VEC3", FLOAT, ARRAY_BUF)
            p_prim: Dict[str, Any] = {
                "attributes": p_attrs,
                "indices": add_accessor(p_idx, "SCALAR", UINT, ELEM_BUF),
            }
            p_names: list = []
            for name, delta in (part.get("morph_targets") or {}).items():
                d = np.ascontiguousarray(delta, dtype=np.float32)
                if d.shape != p_pos.shape:
                    continue
                p_prim.setdefault("targets", []).append(
                    {"POSITION": add_accessor(d, "VEC3", FLOAT, ARRAY_BUF, minmax=True)})
                p_names.append(name)

            r, g_, b_ = part.get("color", (0.9, 0.88, 0.84))
            extra_materials.append({
                "name": part["name"],
                "pbrMetallicRoughness": {
                    "baseColorFactor": [float(r), float(g_), float(b_), 1.0],
                    "metallicFactor": 0.0,
                    "roughnessFactor": float(part.get("roughness", 0.45)),
                },
            })
            mesh_entry: Dict[str, Any] = {"primitives": [p_prim], "name": part["name"]}
            if p_names:
                mesh_entry["weights"] = [0.0] * len(p_names)
                mesh_entry["extras"] = {"targetNames": p_names}
            gltf["meshes"].append(mesh_entry)
            gltf["nodes"].append({"mesh": len(gltf["meshes"]) - 1, "name": part["name"]})
            gltf["scenes"][0]["nodes"].append(len(gltf["nodes"]) - 1)
            p_prim["_material_slot"] = len(extra_materials) - 1

        if texture_path and os.path.exists(texture_path):
            with open(texture_path, "rb") as f:
                img_bytes = f.read()
            img_view = add_view(img_bytes)
            ext = Path(texture_path).suffix.lower().lstrip(".")
            mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                    "png": "image/png"}.get(ext, "image/jpeg")
            gltf["images"] = [{"bufferView": img_view, "mimeType": mime}]
            gltf["samplers"] = [{"magFilter": 9729, "minFilter": 9987,
                                 "wrapS": 10497, "wrapT": 10497}]
            gltf["textures"] = [{"source": 0, "sampler": 0}]
            gltf["materials"] = [{
                "name": "FaceTexture",
                "pbrMetallicRoughness": {
                    "baseColorTexture": {"index": 0},
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.75,
                },
            }]
            primitive["material"] = 0

        # Append the solid-colour materials after the textured head material so
        # their indices are stable whether or not a texture was supplied.
        if extra_materials:
            gltf.setdefault("materials", [])
            base = len(gltf["materials"])
            gltf["materials"].extend(extra_materials)
            for mesh_entry in gltf["meshes"][1:]:
                p = mesh_entry["primitives"][0]
                slot = p.pop("_material_slot", None)
                if slot is not None:
                    p["material"] = base + slot

        if metadata:
            gltf.setdefault("extras", {}).update(metadata)

        gltf["bufferViews"] = buffer_views
        gltf["accessors"] = accessors
        gltf["buffers"] = [{"byteLength": len(blob)}]

        json_chunk = json.dumps(gltf, separators=(",", ":")).encode("utf8")
        json_chunk += b" " * ((4 - len(json_chunk) % 4) % 4)
        bin_chunk = bytes(blob)
        bin_chunk += b"\x00" * ((4 - len(bin_chunk) % 4) % 4)

        total = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
        with open(output_path, "wb") as f:
            f.write(struct.pack("<III", 0x46546C67, 2, total))
            f.write(struct.pack("<II", len(json_chunk), 0x4E4F534A))
            f.write(json_chunk)
            f.write(struct.pack("<II", len(bin_chunk), 0x004E4942))
            f.write(bin_chunk)

        logger.info("GLB exported: %s (%d bytes, %d morph targets)",
                    output_path, os.path.getsize(output_path), len(target_names))
        return output_path

    def _export_with_pygltflib(
        self, obj_path, texture_path, output_path, metadata
    ) -> str:
        """Export using pygltflib (pure Python, no C deps)."""
        import pygltflib

        # Parse OBJ manually for maximum control
        vertices, normals, uvs, faces = self._parse_obj(obj_path)

        # Build glTF
        gltf = pygltflib.GLTF2()
        scene = pygltflib.Scene(nodes=[0])
        gltf.scenes.append(scene)

        # Create buffer with vertex data
        vertex_data = vertices.astype(np.float32).tobytes()
        normal_data = normals.astype(np.float32).tobytes() if len(normals) > 0 else b""
        uv_data = uvs.astype(np.float32).tobytes() if len(uvs) > 0 else b""
        index_data = faces.astype(np.uint32).tobytes()

        buffer_data = vertex_data + normal_data + uv_data + index_data
        buffer = pygltflib.Buffer(byteLength=len(buffer_data))
        gltf.buffers.append(buffer)

        # Accessors
        # Vertices
        vertex_accessor = pygltflib.Accessor(
            bufferView=0, componentType=pygltflib.FLOAT,
            count=len(vertices), type="VEC3",
            max=vertices.max(axis=0).tolist(),
            min=vertices.min(axis=0).tolist(),
        )
        gltf.accessors.append(vertex_accessor)

        offset = len(vertex_data)

        # Normals
        normal_accessor_idx = None
        if len(normals) > 0:
            normal_accessor_idx = len(gltf.accessors)
            gltf.accessors.append(pygltflib.Accessor(
                bufferView=1, componentType=pygltflib.FLOAT,
                count=len(normals), type="VEC3",
            ))
            offset += len(normal_data)

        # UVs
        uv_accessor_idx = None
        if len(uvs) > 0:
            uv_accessor_idx = len(gltf.accessors)
            gltf.accessors.append(pygltflib.Accessor(
                bufferView=2, componentType=pygltflib.FLOAT,
                count=len(uvs), type="VEC2",
            ))
            offset += len(uv_data)

        # Indices
        index_accessor_idx = len(gltf.accessors)
        gltf.accessors.append(pygltflib.Accessor(
            bufferView=3, componentType=pygltflib.UNSIGNED_INT,
            count=len(faces) * 3, type="SCALAR",
        ))

        # Buffer views
        gltf.bufferViews.append(pygltflib.BufferView(buffer=0, byteOffset=0, byteLength=len(vertex_data), target=pygltflib.ARRAY_BUFFER))
        bv_idx = 1
        if len(normal_data) > 0:
            gltf.bufferViews.append(pygltflib.BufferView(buffer=0, byteOffset=len(vertex_data), byteLength=len(normal_data), target=pygltflib.ARRAY_BUFFER))
            bv_idx += 1
        if len(uv_data) > 0:
            gltf.bufferViews.append(pygltflib.BufferView(buffer=0, byteOffset=len(vertex_data) + len(normal_data), byteLength=len(uv_data), target=pygltflib.ARRAY_BUFFER))
            bv_idx += 1
        gltf.bufferViews.append(pygltflib.BufferView(buffer=0, byteOffset=offset, byteLength=len(index_data), target=pygltflib.ELEMENT_ARRAY_BUFFER))

        # Mesh with attributes
        attributes = {"POSITION": 0}
        if normal_accessor_idx is not None:
            attributes["NORMAL"] = normal_accessor_idx
        if uv_accessor_idx is not None:
            attributes["TEXCOORD_0"] = uv_accessor_idx

        primitive = pygltflib.Primitive(
            attributes=pygltflib.Attributes(**attributes),
            indices=index_accessor_idx,
        )

        # Add texture/material if provided
        if texture_path and os.path.exists(texture_path):
            # Embed texture image
            with open(texture_path, "rb") as f:
                img_data = f.read()
            img_bv_idx = len(gltf.bufferViews)
            gltf.bufferViews.append(pygltflib.BufferView(buffer=0, byteOffset=len(buffer_data), byteLength=len(img_data)))
            buffer_data += img_data

            img_idx = len(gltf.images)
            ext = Path(texture_path).suffix.lower().replace(".", "")
            mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(ext, "image/jpeg")
            gltf.images.append(pygltflib.Image(bufferView=img_bv_idx, mimeType=mime))

            tex_idx = len(gltf.textures)
            gltf.textures.append(pygltflib.Texture(source=img_idx))

            mat_idx = len(gltf.materials)
            gltf.materials.append(pygltflib.Material(
                pbrMetallicRoughness=pygltflib.PbrMetallicRoughness(
                    baseColorTexture=pygltflib.TextureInfo(index=tex_idx),
                ),
                name="FaceTexture",
            ))
            primitive.material = mat_idx

        mesh = pygltflib.Mesh(primitives=[primitive], name="FaceMesh")
        gltf.meshes.append(mesh)

        node = pygltflib.Node(mesh=0, name="FaceNode")
        gltf.nodes.append(node)

        # Update buffer byte length
        buffer.byteLength = len(buffer_data)

        # Save as GLB
        gltf.set_binary_blob(buffer_data)
        gltf.save(output_path)
        logger.info(f"GLB exported: {output_path} ({os.path.getsize(output_path)} bytes)")
        return output_path

    def _export_with_trimesh(self, obj_path, texture_path, output_path) -> str:
        """Export using trimesh."""
        import trimesh
        mesh = trimesh.load(obj_path, force="mesh")
        if texture_path and os.path.exists(texture_path):
            mesh.visual = trimesh.visual.TextureVisuals(image=texture_path)
        mesh.export(output_path, file_type="glb")
        logger.info(f"GLB exported (trimesh): {output_path}")
        return output_path

    def _export_raw(self, obj_path, output_path) -> str:
        """Fallback: just copy the OBJ file."""
        import shutil
        shutil.copy2(obj_path, output_path)
        logger.info(f"Raw OBJ copied to: {output_path}")
        return output_path

    def _parse_obj_full(self, obj_path: str):
        """Parse an OBJ keeping each face corner's own UV index.

        Returns (vertices, normals, uvs, faces, face_uv). `face_uv` is None
        when every corner's vt index equals its v index - the one-UV-per-vertex
        layout - and an (F, 3) array otherwise, which is the case that needs
        its seams split before glTF can carry it.
        """
        vertices, normals, uvs, faces, fuv = [], [], [], [], []
        with open(obj_path, "r") as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                if parts[0] == "v":
                    vertices.append([float(x) for x in parts[1:4]])
                elif parts[0] == "vn":
                    normals.append([float(x) for x in parts[1:4]])
                elif parts[0] == "vt":
                    uvs.append([float(x) for x in parts[1:3]])
                elif parts[0] == "f":
                    face, tface = [], []
                    for p in parts[1:]:
                        idx = p.split("/")
                        face.append(int(idx[0]) - 1)
                        tface.append(int(idx[1]) - 1 if len(idx) > 1 and idx[1]
                                     else int(idx[0]) - 1)
                    faces.append(face)
                    fuv.append(tface)
        vertices = np.array(vertices, dtype=np.float32) if vertices else np.zeros((0, 3), np.float32)
        normals = np.array(normals, dtype=np.float32) if normals else np.zeros((0, 3), np.float32)
        uvs = np.array(uvs, dtype=np.float32) if uvs else np.zeros((0, 2), np.float32)
        faces = np.array(faces, dtype=np.uint32) if faces else np.zeros((0, 3), np.uint32)
        fuv = np.array(fuv, dtype=np.uint32) if fuv else np.zeros((0, 3), np.uint32)
        if len(uvs) == 0 or np.array_equal(fuv, faces):
            return vertices, normals, uvs, faces, None
        return vertices, normals, uvs, faces, fuv

    def _parse_obj(self, obj_path: str):
        """Parse OBJ file into numpy arrays."""
        vertices = []
        normals = []
        uvs = []
        faces = []

        with open(obj_path, "r") as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                if parts[0] == "v":
                    vertices.append([float(x) for x in parts[1:4]])
                elif parts[0] == "vn":
                    normals.append([float(x) for x in parts[1:4]])
                elif parts[0] == "vt":
                    uvs.append([float(x) for x in parts[1:3]])
                elif parts[0] == "f":
                    face = []
                    for p in parts[1:]:
                        indices = p.split("/")
                        face.append(int(indices[0]) - 1)  # OBJ is 1-indexed
                    faces.append(face)

        vertices = np.array(vertices, dtype=np.float32) if vertices else np.zeros((0, 3), dtype=np.float32)
        normals = np.array(normals, dtype=np.float32) if normals else np.zeros((0, 3), dtype=np.float32)
        uvs = np.array(uvs, dtype=np.float32) if uvs else np.zeros((0, 2), dtype=np.float32)
        faces = np.array(faces, dtype=np.uint32) if faces else np.zeros((0, 3), dtype=np.uint32)

        return vertices, normals, uvs, faces
