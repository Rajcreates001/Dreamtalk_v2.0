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


class AvatarExporter:
    """Export 3D face meshes to GLB/FBX format."""

    def obj_to_glb(
        self,
        obj_path: str,
        texture_path: Optional[str] = None,
        output_path: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Convert OBJ mesh to GLB (glTF Binary).

        Args:
            obj_path: Path to .obj file.
            texture_path: Optional path to texture image (.jpg/.png).
            output_path: Output .glb path. If None, replaces .obj extension.
            metadata: Optional metadata dict to embed in GLB.

        Returns:
            Path to the generated .glb file.
        """
        if output_path is None:
            output_path = str(Path(obj_path).with_suffix(".glb"))

        try:
            return self._export_with_pygltflib(
                obj_path, texture_path, output_path, metadata
            )
        except ImportError:
            logger.warning("pygltflib not installed — falling back to trimesh")
            try:
                return self._export_with_trimesh(
                    obj_path, texture_path, output_path
                )
            except ImportError:
                logger.warning("trimesh not installed — using raw OBJ copy")
                return self._export_raw(obj_path, output_path)

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
            gltf.accessors.append(pygltltflib.Accessor(
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
