"""
Add procedural hair + eyes geometry to a FLAME base mesh.

This script takes an existing FLAME OBJ (from flame_fitter.py or
generate_mean_mesh) and enhances it with:
  1. Two spherical eyes with irises/pupils (as textured quads)
  2. Procedural hair using layered hair strips with volume
  3. Eyebrow geometry
  4. Combined output as a single OBJ/MTL set

Usage:
    python scripts/add_hair_eyes_mesh.py [--input path/to/head.obj] [--output path/to/output.obj]
"""

import os
import sys
import math
import argparse
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATIC_DIR = os.path.join(PROJECT_ROOT, "avatar", "static")
DEFAULT_INPUT = os.path.join(STATIC_DIR, "generated_head.obj")
DEFAULT_OUTPUT = os.path.join(STATIC_DIR, "dreamtalk_head_full.obj")
DEFAULT_MTL = os.path.join(STATIC_DIR, "dreamtalk_head_full.mtl")


def parse_obj(path: str):
    """Parse OBJ file, handling v/vt/vn/normals."""
    vertices = []
    texcoords = []
    normals = []
    faces = []  # list of dicts: {v: [i,j,k], vt: [i,j,k]|None, vn: [i,j,k]|None}

    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if not parts:
                continue

            if parts[0] == "v":
                vertices.append(tuple(map(float, parts[1:4])))
            elif parts[0] == "vt":
                texcoords.append(tuple(map(float, parts[1:3])))
            elif parts[0] == "vn":
                normals.append(tuple(map(float, parts[1:4])))
            elif parts[0] == "f":
                face_v = []
                face_vt = []
                face_vn = []
                for p in parts[1:]:
                    idxs = p.split("/")
                    face_v.append(int(idxs[0]))
                    face_vt.append(int(idxs[1]) if len(idxs) > 1 and idxs[1] else None)
                    face_vn.append(int(idxs[2]) if len(idxs) > 2 and idxs[2] else None)
                if len(set(face_v)) >= 3:
                    faces.append({"v": face_v, "vt": face_vt, "vn": face_vn})

    return vertices, texcoords, normals, faces


def compute_normals(vertices):
    """Compute radial normals pointing outward from center."""
    verts = np.array(vertices)
    center = verts.mean(axis=0)
    normals = verts - center
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.divide(normals, lengths, out=np.zeros_like(normals), where=lengths > 0)
    return normals.tolist()


def generate_eye_geometry(eye_center_x, eye_center_y, eye_center_z,
                          eye_radius=0.035, segments=16, is_left=True):
    """Generate an eye as a sphere with iris highlight.

    Returns (vertices, texcoords, normals, faces)
    """
    verts = []
    tcoords = []
    norms = []
    faces_list = []

    cx, cy, cz = eye_center_x, eye_center_y, eye_center_z
    r = eye_radius

    # Generate sphere vertices via UV sphere
    for lat in range(segments + 1):
        theta = lat * math.pi / segments  # 0 to pi
        for lon in range(segments * 2 + 1):
            phi = lon * 2 * math.pi / (segments * 2)  # 0 to 2pi

            x = cx + r * math.sin(theta) * math.cos(phi)
            y = cy + r * math.cos(theta)
            z = cz + r * math.sin(theta) * math.sin(phi)

            verts.append((x, y, z))

            # UV: u = phi/(2pi), v = theta/pi
            u = lon / (segments * 2)
            v = lat / segments
            tcoords.append((u, v))

            # Normal is radial from sphere center
            nx = math.sin(theta) * math.cos(phi)
            ny = math.cos(theta)
            nz = math.sin(theta) * math.sin(phi)
            norms.append((nx, ny, nz))

    # Generate faces (triangles)
    for lat in range(segments):
        for lon in range(segments * 2):
            i0 = lat * (segments * 2 + 1) + lon
            i1 = i0 + 1
            i2 = (lat + 1) * (segments * 2 + 1) + lon
            i3 = i2 + 1

            if lat == 0:
                # Top cap: triangles from top
                faces_list.append({"v": [i2, i0, i3], "vt": [i2, i0, i3], "vn": [i2, i0, i3]})
            elif lat == segments - 1:
                # Bottom cap
                faces_list.append({"v": [i0, i2, i1], "vt": [i0, i2, i1], "vn": [i0, i2, i1]})
            else:
                faces_list.append({"v": [i0, i2, i1], "vt": [i0, i2, i1], "vn": [i0, i2, i1]})
                faces_list.append({"v": [i1, i2, i3], "vt": [i1, i2, i3], "vn": [i1, i2, i3]})

    return verts, tcoords, norms, faces_list


def generate_eyebrow_geometry(eye_center_x, eye_center_y, eye_center_z,
                              arch_height=0.008, width=0.025, depth=0.008, is_left=True):
    """Generate eyebrow geometry as an arched strip above the eye.

    Returns (vertices, texcoords, normals, faces)
    """
    verts = []
    tcoords = []
    norms = []
    faces_list = []

    cx, cy, cz = eye_center_x, eye_center_y, eye_center_z
    sign = -1 if is_left else 1

    # Eyebrow arch with 5 control points extending outward from center
    arch_points = 12
    segments = 3  # thickness layers

    for s in range(segments + 1):
        depth_offset = -s * depth / segments  # going inward (toward head)
        for p in range(arch_points + 1):
            t = p / arch_points
            # Arch shape: starts near inner eye, arches up, ends near outer eye
            angle = t * math.pi - math.pi * 0.25  # from -45deg to +135deg
            arch_scale = math.sin(t * math.pi) * arch_height * 2.5

            x = cx + sign * (width * 0.8 * math.cos(angle) * 0.8)
            y = cy + 0.04 + arch_scale + width * 0.15 * math.sin(angle) * 0.5
            z = cz + depth_offset + width * 0.25 * math.sin(angle) * 0.3

            # Slightly thicker at middle
            spread = 1.0 - 0.3 * abs(math.sin(t * math.pi))
            x += sign * spread * width * 0.1

            verts.append((x, y, z))
            tcoords.append((t, s / segments))
            norms.append((0.0, 0.7, -0.7))

    for s in range(segments):
        for p in range(arch_points):
            i0 = s * (arch_points + 1) + p
            i1 = i0 + 1
            i2 = (s + 1) * (arch_points + 1) + p
            i3 = i2 + 1

            faces_list.append({"v": [i0, i2, i1], "vt": [i0, i2, i1], "vn": [i0, i2, i1]})
            faces_list.append({"v": [i1, i2, i3], "vt": [i1, i2, i3], "vn": [i1, i2, i3]})

    return verts, tcoords, norms, faces_list


def generate_hair_geometry(head_vertices, head_center=None):
    """Generate procedural hair geometry over the top of the head.

    Strategy:
      1. Find the top region of the head (y > center_y + threshold)
      2. Generate hair strands as layered strips with both horizontal
         and vertical connections for a solid mesh
      3. Add volume with multiple concentric layers
      4. Add a solid hair cap at the top

    Returns (vertices, texcoords, normals, faces)
    """
    verts = []
    tcoords = []
    norms = []
    faces_list = []

    verts_arr = np.array(head_vertices)
    if head_center is None:
        head_center = verts_arr.mean(axis=0)

    cx, cy, cz = head_center

    # Find top head vertices to determine hair cap extent
    top_verts = verts_arr[verts_arr[:, 1] > cy + 0.15]
    if len(top_verts) == 0:
        top_verts = verts_arr
    top_center = top_verts.mean(axis=0)
    top_y = top_center[1]
    radius = max(0.18, np.max(np.linalg.norm(top_verts[:, [0, 2]] - top_center[[0, 2]], axis=1)))

    # Hair parameters
    hair_layers = 8
    hair_radius = radius * 1.3
    hair_height = 0.25
    strands = 24
    segs_per_strand = 5  # segments along each strand

    base_offset = 0.0

    for layer in range(hair_layers):
        layer_ratio = layer / (hair_layers - 1)
        layer_radius = hair_radius * (0.7 + 0.3 * layer_ratio)
        layer_height = hair_height * (0.3 + 0.7 * (1 - layer_ratio))

        for s in range(strands):
            theta = 2 * math.pi * s / strands + layer * 0.3
            theta += (layer * 0.1 + s * 0.03)

            bx = top_center[0] + layer_radius * math.cos(theta)
            bz = top_center[2] + layer_radius * math.sin(theta)
            by = top_y - 0.05 + base_offset

            for seg in range(segs_per_strand):
                seg_ratio = seg / (segs_per_strand - 1)
                height_factor = 1.0 - seg_ratio * 0.15
                spread = 1.0 + seg_ratio * 0.25
                sway = math.sin(seg_ratio * math.pi * 2 + theta) * 0.01

                x = bx + spread * (layer_radius * 0.2) * math.cos(theta) + sway
                z = bz + spread * (layer_radius * 0.2) * math.sin(theta)
                y = by + layer_height * height_factor - seg_ratio * 0.02

                verts.append((x, y, z))
                tcoords.append((seg / (segs_per_strand - 1), layer_ratio))
                norms.append((0.0, 1.0, 0.0))

    def _vi(layer, strand, seg):
        """Compute vertex index for a given hair coordinate."""
        return layer * (strands * segs_per_strand) + strand * segs_per_strand + seg

    # Generate hair faces with BOTH horizontal and vertical connections
    # Vertical quads: connect same (strand, seg) across adjacent layers
    # Horizontal quads: connect same (layer, seg) across adjacent strands
    for layer in range(hair_layers - 1):
        for s in range(strands):
            s_next = (s + 1) % strands
            for seg in range(segs_per_strand - 1):
                # Vertical quad (between layers, same strand+seg)
                i0 = _vi(layer, s, seg)
                i1 = _vi(layer, s, seg + 1)
                i2 = _vi(layer + 1, s, seg)
                i3 = _vi(layer + 1, s, seg + 1)
                faces_list.append({"v": [i0, i2, i1], "vt": [i0, i2, i1], "vn": [i0, i2, i1]})
                faces_list.append({"v": [i1, i2, i3], "vt": [i1, i2, i3], "vn": [i1, i2, i3]})

                # Horizontal quad (between strands, same layer+seg)
                i0 = _vi(layer, s, seg)
                i1 = _vi(layer, s, seg + 1)
                i2 = _vi(layer, s_next, seg)
                i3 = _vi(layer, s_next, seg + 1)
                faces_list.append({"v": [i0, i1, i2], "vt": [i0, i1, i2], "vn": [i0, i1, i2]})
                faces_list.append({"v": [i1, i3, i2], "vt": [i1, i3, i2], "vn": [i1, i3, i2]})

                # Cross-layer horizontal quad (between strands across layers)
                i0 = _vi(layer, s, seg)
                i1 = _vi(layer, s_next, seg)
                i2 = _vi(layer + 1, s, seg)
                i3 = _vi(layer + 1, s_next, seg)
                faces_list.append({"v": [i0, i2, i1], "vt": [i0, i2, i1], "vn": [i0, i2, i1]})
                faces_list.append({"v": [i1, i2, i3], "vt": [i1, i2, i3], "vn": [i1, i2, i3]})

    # Add a solid hair cap at the top
    cap_verts = []
    cap_radius = hair_radius * 1.1
    cap_points = 24

    for p in range(cap_points):
        theta_cap = 2 * math.pi * p / cap_points
        x = top_center[0] + cap_radius * math.cos(theta_cap)
        z = top_center[2] + cap_radius * math.sin(theta_cap)
        y = top_y + hair_height * 0.8
        cap_verts.append((x, y, z))

    # Center top vertex (apex of cap dome)
    cap_center_idx = len(verts)  # index where center will be placed
    verts.append((top_center[0], top_y + hair_height * 0.95, top_center[2]))
    tcoords.append((0.5, 0.5))
    norms.append((0.0, 1.0, 0.0))

    cap_offset = len(verts)  # first cap perimeter vertex goes right after center
    for v in cap_verts:
        verts.append(v)
        tcoords.append((0.5, 0.5))
        norms.append((0.0, 1.0, 0.0))

    # Cap triangles from center to each cap edge pair
    for p in range(cap_points):
        i0 = cap_center_idx
        i1 = cap_offset + p
        i2 = cap_offset + (p + 1) % cap_points
        faces_list.append({"v": [i0, i1, i2], "vt": [i0, i1, i2], "vn": [i0, i1, i2]})

    return verts, tcoords, norms, faces_list


def write_obj(path, all_vertices, all_texcoords, all_normals, all_faces,
              groups=None, mtl_name="dreamtalk_head_full.mtl"):
    """Write combined OBJ file with material groups."""
    with open(path, "w") as f:
        f.write(f"# DreamTalk Complete Head Mesh - FLAME + Hair + Eyes\n")
        f.write(f"# {len(all_vertices)} vertices, {len(all_faces)} faces\n")
        f.write(f"mtllib {mtl_name}\n\n")

        # Vertices
        for v in all_vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

        f.write("\n")

        # Texture coords
        for vt in all_texcoords:
            f.write(f"vt {vt[0]:.6f} {vt[1]:.6f}\n")

        f.write("\n")

        # Normals
        for vn in all_normals:
            f.write(f"vn {vn[0]:.6f} {vn[1]:.6f} {vn[2]:.6f}\n")

        f.write("\n")

        def _format_face(face):
            """Format a face as an OBJ face line. Handles cases where
            vt/vn may be None (whole list) or contain None entries."""
            parts = []
            has_vt = isinstance(face.get('vt'), list) and len(face['vt']) >= 3
            has_vn = isinstance(face.get('vn'), list) and len(face['vn']) >= 3
            for j in range(3):
                vi = face['v'][j] + 1
                if has_vt and has_vn and face['vt'][j] is not None and face['vn'][j] is not None:
                    parts.append(f"{vi}/{face['vt'][j]+1}/{face['vn'][j]+1}")
                elif has_vn and face['vn'][j] is not None:
                    parts.append(f"{vi}//{face['vn'][j]+1}")
                elif has_vt and face['vt'][j] is not None:
                    parts.append(f"{vi}/{face['vt'][j]+1}")
                else:
                    parts.append(str(vi))
            return " ".join(parts)

        # Faces by group
        if groups:
            for group_name, face_range in groups:
                f.write(f"g {group_name}\n")
                f.write(f"usemtl {group_name}\n")
                for i in range(*face_range):
                    f.write(f"f {_format_face(all_faces[i])}\n")
                f.write("\n")
        else:
            for face in all_faces:
                f.write(f"f {_format_face(face)}\n")


def write_mtl(path):
    """Write MTL file with materials for skin, eyes, and hair."""
    mtl = """# DreamTalk Complete Head Mesh Materials

newmtl skin
Ka 0.85 0.75 0.65
Kd 0.92 0.82 0.72
Ks 0.30 0.25 0.20
Ns 40.0
d 1.0
illum 2

newmtl eyes
Ka 1.0 1.0 1.0
Kd 0.95 0.95 1.0
Ks 0.50 0.50 0.50
Ns 80.0
d 1.0
illum 3

newmtl pupils
Ka 0.05 0.05 0.05
Kd 0.05 0.05 0.05
Ks 0.10 0.10 0.10
Ns 10.0
d 1.0
illum 1

newmtl iris
Ka 0.2 0.3 0.5
Kd 0.3 0.4 0.6
Ks 0.2 0.3 0.4
Ns 30.0
d 1.0
illum 2

newmtl eyebrows
Ka 0.1 0.08 0.06
Kd 0.15 0.12 0.10
Ks 0.20 0.15 0.10
Ns 15.0
d 1.0
illum 2

newmtl hair
Ka 0.08 0.06 0.05
Kd 0.12 0.10 0.08
Ks 0.30 0.25 0.20
Ns 60.0
d 1.0
illum 2
"""
    with open(path, "w") as f:
        f.write(mtl)


def main():
    parser = argparse.ArgumentParser(
        description="Add procedural hair + eyes to FLAME base mesh"
    )
    parser.add_argument("--input", default=DEFAULT_INPUT,
                        help=f"Input OBJ path (default: {DEFAULT_INPUT})")
    parser.add_argument("--output", default=DEFAULT_OUTPUT,
                        help=f"Output OBJ path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--hair-density", type=int, default=24,
                        help="Number of hair strands (default: 24)")
    parser.add_argument("--eye-size", type=float, default=1.0,
                        help="Eye size multiplier (default: 1.0)")
    args = parser.parse_args()

    print(f"Reading FLAME mesh from: {args.input}")

    if not os.path.exists(args.input):
        # Check if input is default but not found - try generating mean mesh first
        print(f"Warning: Input OBJ not found. Generating from FLAME model...")
        try:
            sys.path.insert(0, PROJECT_ROOT)
            from pipeline.flame_fitter import FlameFitter
            fitter = FlameFitter()
            result = fitter.generate_mean_mesh(output_dir=STATIC_DIR)
            args.input = result["obj_path"]
            print(f"Generated mean mesh at: {args.input}")
        except Exception as e:
            print(f"ERROR: Could not generate FLAME mesh: {e}")
            print(f"Generating standalone head instead...")
            args.input = None

    all_vertices = []
    all_texcoords = []
    all_normals = []
    all_faces = []
    group_ranges = []

    base_vertex_offset = 0

    if args.input and os.path.exists(args.input):
        # Parse FLAME mesh
        flame_verts, flame_tc, flame_n, flame_faces = parse_obj(args.input)

        # Compute normals if none in OBJ
        if len(flame_n) == 0:
            flame_n = compute_normals(flame_verts)

        base_vertex_offset = len(all_vertices)
        all_vertices.extend(flame_verts)
        all_texcoords.extend(flame_tc if flame_tc else [(0.0, 0.0)] * len(flame_verts))
        all_normals.extend(flame_n if flame_n else [(0.0, 1.0, 0.0)] * len(flame_verts))

        # Re-index faces
        for face in flame_faces:
            new_face = {
                "v": [base_vertex_offset + i - 1 for i in face["v"]],
                "vt": [base_vertex_offset + (i if i else 1) - 1 for i in face["vt"]] if face["vt"] and face["vt"][0] else None,
                "vn": [base_vertex_offset + (i if i else 1) - 1 for i in face["vn"]] if face["vn"] and face["vn"][0] else None,
            }
            all_faces.append(new_face)

        group_ranges.append(("skin", (0, len(all_faces))))

        # Compute head center and vertex array from flame mesh
        verts_arr = np.array(flame_verts)
        head_center = verts_arr.mean(axis=0)
        print(f"FLAME mesh: {len(flame_verts)} verts, {len(flame_faces)} faces")
        print(f"Head center: {head_center}")
    else:
        # Standalone: use procedural head shape
        print("Generating standalone head shape...")
        verts_arr = np.array([
            [0.0, 0.0, 0.0],
            [0.2, 0.2, 0.2],
        ])
        head_center = np.array([0.0, 0.0, 0.0])

    # Eye positions derived from actual mesh vertex data
    head_width = np.max(np.abs(verts_arr[:, 0]))
    head_height = verts_arr[:, 1].max() - verts_arr[:, 1].min()
    head_depth = verts_arr[:, 2].max() - verts_arr[:, 2].min()

    print(f"Head bounds: width={head_width:.3f}, height={head_height:.3f}, depth={head_depth:.3f}")

    # Eye parameters
    eye_radius = 0.035 * args.eye_size

    # Estimate eye Z from mesh depth
    face_front_z = verts_arr[:, 2].max()  # Z+ is forward in FLAME
    face_mid_y = verts_arr[:, 1].min() + head_height * 0.38

    # Estimate from mesh - use actual vertex bounds for eye placement
    left_eye_pos = (-head_width * 0.28, face_mid_y, face_front_z * 0.55)
    right_eye_pos = (head_width * 0.28, face_mid_y, face_front_z * 0.55)

    # Generate left eye
    print("Generating left eye geometry...")
    le_verts, le_tc, le_n, le_faces = generate_eye_geometry(
        left_eye_pos[0], left_eye_pos[1], left_eye_pos[2],
        eye_radius=eye_radius, is_left=True,
    )
    le_offset = len(all_vertices)
    all_vertices.extend(le_verts)
    all_texcoords.extend(le_tc)
    all_normals.extend(le_n)
    for face in le_faces:
        all_faces.append({
            "v": [le_offset + i for i in face["v"]],
            "vt": [le_offset + i for i in face["vt"]],
            "vn": [le_offset + i for i in face["vn"]],
        })
    group_ranges.append(("eyes", (len(all_faces) - len(le_faces), len(all_faces))))

    # Generate right eye
    print("Generating right eye geometry...")
    re_verts, re_tc, re_n, re_faces = generate_eye_geometry(
        right_eye_pos[0], right_eye_pos[1], right_eye_pos[2],
        eye_radius=eye_radius, is_left=False,
    )
    re_offset = len(all_vertices)
    all_vertices.extend(re_verts)
    all_texcoords.extend(re_tc)
    all_normals.extend(re_n)
    for face in re_faces:
        all_faces.append({
            "v": [re_offset + i for i in face["v"]],
            "vt": [re_offset + i for i in face["vt"]],
            "vn": [re_offset + i for i in face["vn"]],
        })
    # Update eyes group to cover left + right eyes together
    total_eye_faces = len(le_faces) + len(re_faces)
    group_ranges[-1] = ("eyes", (len(all_faces) - total_eye_faces, len(all_faces)))

    # Generate eyebrows
    print("Generating eyebrow geometry...")
    for is_left, pos in [(True, left_eye_pos), (False, right_eye_pos)]:
        eb_verts, eb_tc, eb_n, eb_faces = generate_eyebrow_geometry(
            pos[0], pos[1], pos[2],
            arch_height=0.008, width=0.025, depth=0.008,
            is_left=is_left,
        )
        eb_offset = len(all_vertices)
        all_vertices.extend(eb_verts)
        all_texcoords.extend(eb_tc)
        all_normals.extend(eb_n)
        for face in eb_faces:
            all_faces.append({
                "v": [eb_offset + i for i in face["v"]],
                "vt": [eb_offset + i for i in face["vt"]],
                "vn": [eb_offset + i for i in face["vn"]],
            })

    group_ranges.append(("eyebrows", (len(all_faces) - 2 * len(eb_faces), len(all_faces))))

    # Generate hair
    print("Generating hair geometry...")
    hair_verts, hair_tc, hair_n, hair_faces = generate_hair_geometry(
        all_vertices[:base_vertex_offset] if base_vertex_offset > 0 else all_vertices,
        head_center=None,
    )
    hair_offset = len(all_vertices)
    all_vertices.extend(hair_verts)
    all_texcoords.extend(hair_tc)
    all_normals.extend(hair_n)
    for face in hair_faces:
        all_faces.append({
            "v": [hair_offset + i for i in face["v"]],
            "vt": [hair_offset + i for i in face["vt"]],
            "vn": [hair_offset + i for i in face["vn"]],
        })
    group_ranges.append(("hair", (len(all_faces) - len(hair_faces), len(all_faces))))

    # Write output
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    print(f"\nWriting combined mesh to: {args.output}")
    write_obj(args.output, all_vertices, all_texcoords, all_normals, all_faces,
              groups=group_ranges)

    mtl_path = os.path.join(os.path.dirname(args.output) or ".", os.path.basename(args.output).replace(".obj", ".mtl"))
    if args.output.endswith(".obj"):
        mtl_path = args.output.replace(".obj", ".mtl")
    print(f"Writing materials to: {mtl_path}")
    write_mtl(mtl_path)

    print(f"\n{'='*50}")
    print(f"Complete Head Mesh Summary:")
    print(f"  Total vertices: {len(all_vertices)}")
    print(f"  Total faces:    {len(all_faces)}")
    print(f"  Groups:")
    for name, (start, end) in group_ranges:
        print(f"    {name}: {end - start} faces")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
