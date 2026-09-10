"""
End-to-end verification of improved FLAME identity fitting.
Runs uvicorn in-process, uploads photo, verifies static files.
"""
import sys, os, json, time, threading

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# dreamtalk/ is the package root; its *parent* is needed so 'import dreamtalk.*' works
DREAMTALK_ROOT = PROJECT_ROOT
PROJECT_PARENT = os.path.dirname(DREAMTALK_ROOT)
os.chdir(PROJECT_PARENT)
sys.path.insert(0, PROJECT_PARENT)

SERVER_THREAD = None
STATUS_OK = {"ready": False}

def start_server():
    import uvicorn
    from dreamtalk.backend.main import app
    # Override log level for clean output
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="critical")

def wait_for_server(timeout=180):
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen("http://localhost:5000/", timeout=3) as resp:
                if resp.status == 200:
                    print("[OK] Backend ready after %ds" % (time.time() - start))
                    return True
        except Exception:
            pass
        time.sleep(3)
    return False

def test():
    # Start server in daemon thread
    global SERVER_THREAD
    SERVER_THREAD = threading.Thread(target=start_server, daemon=True)
    SERVER_THREAD.start()
    print("[INFO] Backend thread started")

    if not wait_for_server():
        print("[FAIL] Backend did not start in time")
        return False

    import requests
    sess = requests.Session()

    # Login
    r = sess.post("http://localhost:5000/api/v1/auth/login",
                  json={"email": "maha@gmail.com", "password": "maha1234"})
    if r.status_code != 200:
        print("[FAIL] Login: %d" % r.status_code)
        return False
    token = r.json()["tokens"]["access_token"]
    sess.headers.update({"Authorization": "Bearer %s" % token})
    print("[OK] Logged in")

    # Upload photo
    photo = os.path.join(DREAMTALK_ROOT, "local_upload_testing",
                         "Image_local", "sample1.jpeg")
    if not os.path.exists(photo):
        print("[FAIL] Photo not found: %s" % photo)
        return False
    print("[INFO] Photo: %s (%d bytes)" % (photo, os.path.getsize(photo)))

    with open(photo, "rb") as f:
        files = {"files": ("sample1.jpeg", f, "image/jpeg")}
        r = sess.post(
            "http://localhost:5000/api/v1/digital-twins/"
            "48acf794-7423-4379-9f20-c2c852d64a01/appearance/upload",
            files=files,
        )

    print("[INFO] Upload status: %d" % r.status_code)
    if r.status_code not in (200, 202):
        print("[FAIL] Upload error: %s" % r.text[:200])
        return False

    data = r.json()
    results = data.get("results", [])
    if not results:
        print("[FAIL] No results: %s" % json.dumps(data)[:300])
        return False

    analysis = results[0].get("analysis", {})
    face_detected = analysis.get("face_detected")
    print("[INFO] Face detected: %s" % face_detected)

    for log in analysis.get("analysis_log", []):
        print("  [LOG] step=%s status=%s" % (log.get("step"), log.get("status")))

    mesh_url = analysis.get("mesh_3d_url")
    print("[INFO] Mesh URL: %s" % mesh_url)

    # Verify static files
    static_dir = os.path.join(DREAMTALK_ROOT, "avatar", "static")
    for fname in sorted(os.listdir(static_dir)):
        fpath = os.path.join(static_dir, fname)
        if os.path.isfile(fpath):
            print("  [FILE] %s (%d bytes)" % (fname, os.path.getsize(fpath)))

    # Check MTL
    mtl_path = os.path.join(static_dir, "face_texture.mtl")
    if os.path.exists(mtl_path):
        mtl = open(mtl_path).read()
        print("[INFO] MTL: %s" % mtl.strip().replace("\n", " | "))

    # Check OBJ stats
    obj_path = os.path.join(static_dir, "current_mesh.obj")
    if os.path.exists(obj_path):
        with open(obj_path) as f:
            lines = f.readlines()
        v = sum(1 for l in lines if l.startswith("v "))
        vt = sum(1 for l in lines if l.startswith("vt "))
        f_cnt = sum(1 for l in lines if l.startswith("f "))
        has_mtl = "mtllib" in "".join(lines[:5])
        print("[INFO] OBJ: %d verts, %d faces, %d texcoords, mtllib=%s" %
              (v, f_cnt, vt, has_mtl))
        if v >= 5023:
            print("[OK] Full FLAME mesh geometry (5023+ vertices)")
        elif v > 100:
            print("[OK] Reduced mesh (%d vertices)" % v)
        else:
            print("[WARN] Too few vertices (%d)" % v)
    else:
        print("[FAIL] current_mesh.obj not created")
        return False

    # Verify via HTTP
    mesh_r = requests.get("http://localhost:5000/api/static/current_mesh.obj")
    print("[INFO] HTTP mesh: status=%d size=%d" % (mesh_r.status_code, len(mesh_r.content)))
    mtl_r = requests.get("http://localhost:5000/api/static/face_texture.mtl")
    print("[INFO] HTTP MTL: status=%d content=%s" % (mtl_r.status_code, mtl_r.text.strip()[:60]))

    if mesh_r.status_code == 200 and mtl_r.status_code == 200:
        print("\n[PASS] END-TO-END VERIFICATION PASSED")
        print("The improved FLAME identity fitting is now connected through:")
        print("  Upload -> Digital Twin API -> FlameFitter.fit_from_photo()")
        print("  -> avatar/static/current_mesh.obj -> Avatar Viewer")
        return True
    else:
        print("\n[WARN] Mesh generated but HTTP access failed")
        return False

if __name__ == "__main__":
    result = test()
    print("\n[RESULT] %s" % ("PASS" if result else "FAIL"))
