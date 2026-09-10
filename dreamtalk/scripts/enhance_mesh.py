"""
Enhance the generated 3D head mesh:
  1. Compute smooth vertex normals (area-weighted face normal averaging)
  2. Create an MTL material file with skin-like shading properties
  3. Write a new OBJ that references the MTL and includes vertex normals
"""

import os
import sys
import math

# Paths
# Script is at ./scripts/, OBJ is at ./avatar/static/
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(SCRIPTS_DIR)  # dreamtalk/
OBJ_IN = os.path.join(APP_DIR, "avatar", "static", "generated_head.obj")
OBJ_OUT = os.path.join(APP_DIR, "avatar", "static", "generated_head.obj")
MTL_PATH = os.path.join(APP_DIR, "avatar", "static", "generated_head.mtl")


def parse_obj(path: str):
    """Parse a simple OBJ file (no normals, no mtllib yet)."""
    vertices = []  # list of (x, y, z)
    faces = []     # list of lists of vertex indices (1-based)

    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "v":
                x, y, z = map(float, parts[1:4])
                vertices.append((x, y, z))
            elif parts[0] == "f":
                # supports "f v1 v2 v3" or "f v1/t1 v2/t2 v3/t3"
                idxs = []
                for p in parts[1:]:
                    idx = p.split("/")[0]
                    idxs.append(int(idx))
                # Skip degenerate faces (duplicate vertices = zero area)
                if len(set(idxs)) >= 3:
                    faces.append(idxs)

    return vertices, faces


def face_normal(v0, v1, v2):
    """Compute the unit normal of a triangle defined by three vertices."""
    ax, ay, az = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
    bx, by, bz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
    nx = ay * bz - az * by
    ny = az * bx - ax * bz
    nz = ax * by - ay * bx
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length == 0:
        return (0.0, 1.0, 0.0)
    return (nx / length, ny / length, nz / length)


def compute_vertex_normals(vertices, faces):
    """Compute smooth vertex normals by area-weighted averaging of face normals."""
    normals = [(0.0, 0.0, 0.0) for _ in vertices]
    weights = [0.0 for _ in vertices]

    for face in faces:
        if len(face) < 3:
            continue
        # Compute face normal from first three vertices
        i0, i1, i2 = face[0] - 1, face[1] - 1, face[2] - 1
        v0, v1, v2 = vertices[i0], vertices[i1], vertices[i2]
        fn = face_normal(v0, v1, v2)

        # Accumulate weighted by angle at each vertex
        for tri_idx in range(len(face)):
            i_prev = face[(tri_idx - 1) % len(face)] - 1
            i_cur = face[tri_idx] - 1
            i_next = face[(tri_idx + 1) % len(face)] - 1

            v_prev = vertices[i_prev]
            v_cur = vertices[i_cur]
            v_next = vertices[i_next]

            # Angle at i_cur between edges (prev->cur) and (cur->next)
            e1 = (v_prev[0] - v_cur[0], v_prev[1] - v_cur[1], v_prev[2] - v_cur[2])
            e2 = (v_next[0] - v_cur[0], v_next[1] - v_cur[1], v_next[2] - v_cur[2])

            len1 = math.sqrt(e1[0]**2 + e1[1]**2 + e1[2]**2)
            len2 = math.sqrt(e2[0]**2 + e2[1]**2 + e2[2]**2)

            if len1 == 0 or len2 == 0:
                continue

            dot = (e1[0] * e2[0] + e1[1] * e2[1] + e1[2] * e2[2]) / (len1 * len2)
            dot = max(-1.0, min(1.0, dot))
            angle = math.acos(dot)

            nx, ny, nz = normals[i_cur]
            nx += fn[0] * angle
            ny += fn[1] * angle
            nz += fn[2] * angle
            normals[i_cur] = (nx, ny, nz)
            weights[i_cur] += angle

    # Normalize
    result = []
    for i, (nx, ny, nz) in enumerate(normals):
        w = weights[i]
        if w == 0:
            # Radial fallback: point outward from center using vertex position
            vx, vy, vz = vertices[i]
            length = math.sqrt(vx*vx + vy*vy + vz*vz)
            if length > 0:
                result.append((vx/length, vy/length, vz/length))
            else:
                result.append((0.0, 1.0, 0.0))
        else:
            length = math.sqrt(nx * nx + ny * ny + nz * nz)
            if length == 0:
                result.append((0.0, 1.0, 0.0))
            else:
                result.append((nx / length, ny / length, nz / length))

    return result


def write_mtl(path: str):
    """Write a high-quality skin material MTL file for Three.js."""
    mtl = """# DreamTalk Face Mesh Material
newmtl skin_material
Ka 0.85 0.75 0.65
Kd 0.92 0.82 0.72
Ks 0.30 0.25 0.20
Ns 40.0
d 1.0
illum 2
"""
    with open(path, "w") as f:
        f.write(mtl)
    print(f"  Wrote MTL: {path}")


def write_obj(path: str, vertices, normals, faces, mtl_name="generated_head.mtl"):
    """Write the OBJ with mtllib, usemtl, and vertex normals."""
    with open(path, "w") as f:
        f.write("# DreamTalk 3D Face Mesh - Enhanced\n")
        f.write(f"# {len(vertices)} vertices, {len(faces)} faces\n")
        f.write(f"mtllib {mtl_name}\n")
        f.write(f"usemtl skin_material\n")
        f.write("\n")

        # Vertices
        for v in vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

        f.write("\n")

        # Normals
        for n in normals:
            f.write(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n")

        f.write("\n")

        # Faces with normals (v//vn format)
        for face in faces:
            idxs = " ".join(f"{i}//{i}" for i in face)
            f.write(f"f {idxs}\n")

    print(f"  Wrote OBJ: {path}")


def main():
    print("Enhancing 3D face mesh with normals and MTL...\n")

    if not os.path.exists(OBJ_IN):
        print(f"ERROR: Input OBJ not found: {OBJ_IN}")
        sys.exit(1)

    print(f"  Reading: {OBJ_IN}")
    vertices, faces = parse_obj(OBJ_IN)
    print(f"  Vertices: {len(vertices)}, Faces: {len(faces)}")

    print("  Computing smooth vertex normals (angle-weighted)...")
    normals = compute_vertex_normals(vertices, faces)
    print(f"  Normals computed: {len(normals)}")

    # Count degenerate normals
    bad = sum(1 for n in normals if n == (0.0, 1.0, 0.0))
    if bad:
        print(f"  Warning: {bad} vertices got fallback normals")

    print("\n  Creating MTL material file...")
    write_mtl(MTL_PATH)

    print("\n  Writing enhanced OBJ...")
    write_obj(OBJ_OUT, vertices, normals, faces)

    print("\nDone! Enhanced mesh written:")
    print(f"   OBJ: {OBJ_OUT}")
    print(f"   MTL: {MTL_PATH}")

    # Verify
    with open(OBJ_OUT, "r") as f:
        content = f.read()
    vn_count = content.count("\nvn ")
    print(f"\n   Verification: {vn_count} vertex normals in output OBJ")


if __name__ == "__main__":
    main()
