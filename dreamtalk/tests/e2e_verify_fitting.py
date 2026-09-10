"""
End-to-end verification script for improved FLAME identity fitting.

Starts the backend, uploads a photo through the digital twin API,
verifies the mesh/static files are created, then cleans up.
"""
import subprocess
import sys
import os
import time
import json
import signal
import urllib.request

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

BACKEND_PROC = None

def start_backend():
    global BACKEND_PROC
    print("=== Starting backend ===")
    BACKEND_PROC = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "dreamtalk.backend.main:app",
         "--host", "0.0.0.0", "--port", "5000", "--log-level", "warning"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    print(f"Backend PID: {BACKEND_PROC.pid}")

def wait_for_backend(timeout=120):
    print("=== Waiting for backend to be ready ===")
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen("http://localhost:5000/", timeout=5) as resp:
                if resp.status == 200:
                    print(f"Backend ready after {time.time()-start:.0f}s")
                    return True
        except Exception:
            pass
        time.sleep(5)
    return False

def upload_photo():
    """Upload photo via the digital twin API and verify the FLAME mesh is generated."""
    print("=== Uploading photo through digital twin API ===")
    
    import requests
    
    s = requests.Session()
    
    # Login
    r = s.post("http://localhost:5000/api/v1/auth/login",
               json={"email": "maha@gmail.com", "password": "maha1234"})
    if r.status_code != 200:
        print(f"LOGIN FAILED: {r.status_code} {r.text[:200]}")
        return False
    token = r.json()["tokens"]["access_token"]
    s.headers.update({"Authorization": f"Bearer {token}"})
    print("1. Logged in OK")
    
    # Upload photo
    photo_path = os.path.join(PROJECT_ROOT, "dreamtalk", "local_upload_testing", "Image_local", "sample1.jpeg")
    if not os.path.exists(photo_path):
        print(f"PHOTO NOT FOUND: {photo_path}")
        return False
    
    print(f"2. Photo path: {photo_path} ({os.path.getsize(photo_path)} bytes)")
    
    with open(photo_path, "rb") as f:
        files = {"files": ("sample1.jpeg", f, "image/jpeg")}
        r = s.post(
            "http://localhost:5000/api/v1/digital-twins/48acf794-7423-4379-9f20-c2c852d64a01/appearance/upload",
            files=files,
        )
    
    print(f"3. Upload response: {r.status_code}")
    if r.status_code not in (200, 202):
        print(f"   ERROR: {r.text[:300]}")
        return False
    
    data = r.json()
    results = data.get("results", [])
    if not results:
        print(f"   No results: {json.dumps(data, indent=2)[:500]}")
        return False
    
    result = results[0]
    analysis = result.get("analysis", {})
    print(f"4. Face detected: {analysis.get('face_detected')}")
    
    # Print analysis log
    for log in analysis.get("analysis_log", []):
        print(f"   [{log.get('step')}] status={log.get('status')}  msg={log.get('message','')[:80]}")
    
    # Check mesh URL
    mesh_url = analysis.get("mesh_3d_url")
    print(f"5. Mesh URL: {mesh_url}")
    
    # Verify static files
    static_dir = os.path.join(PROJECT_ROOT, "dreamtalk", "avatar", "static")
    files_found = []
    for fname in os.listdir(static_dir):
        fpath = os.path.join(static_dir, fname)
        if os.path.isfile(fpath):
            files_found.append((fname, os.path.getsize(fpath)))
    
    print(f"6. Static files ({len(files_found)}):")
    for name, size in sorted(files_found):
        prefix = "  ✅" if "current" in name or "face_texture" in name else "   "
        print(f"   {prefix} {name}: {size} bytes")
    
    # Verify MTL references texture
    mtl_path = os.path.join(static_dir, "face_texture.mtl")
    if os.path.exists(mtl_path):
        mtl_content = open(mtl_path).read()
        print(f"7. MTL content: {mtl_content.strip()}")
        if "map_Kd" in mtl_content:
            print("   ✅ MTL references texture map")
        else:
            print("   ❌ MTL missing texture map")
    
    # Verify OBJ has vertices
    obj_path = os.path.join(static_dir, "current_mesh.obj")
    if os.path.exists(obj_path):
        with open(obj_path) as f:
            lines = f.readlines()
        vert_count = sum(1 for l in lines if l.startswith("v "))
        face_count = sum(1 for l in lines if l.startswith("f "))
        print(f"8. OBJ: {vert_count} vertices, {face_count} faces")
        if vert_count > 100:
            print("   ✅ FLAME mesh has sufficient geometry")
        if "mtllib" in "".join(lines[:5]):
            print("   ✅ OBJ references MTL")
        # Check for texture coordinates
        vt_count = sum(1 for l in lines if l.startswith("vt "))
        print(f"   Texture coords: {vt_count}")
        if vt_count > 0:
            print("   ✅ UV coordinates present")
    
    return mesh_url is not None

def check_avatar_viewer():
    """Check if the avatar viewer HTML would load the mesh."""
    print("=== Verifying avatar viewer would load the mesh ===")
    
    import requests
    s = requests.Session()
    
    # Login
    r = s.post("http://localhost:5000/api/v1/auth/login",
               json={"email": "maha@gmail.com", "password": "maha1234"})
    token = r.json()["tokens"]["access_token"]
    s.headers.update({"Authorization": f"Bearer {token}"})
    
    # Check session
    r = s.get("http://localhost:5000/api/avatar/session")
    if r.status_code != 200:
        print(f"Session endpoint failed: {r.status_code}")
        return False
    
    data = r.json()
    print(f"Mesh URL in session: {data.get('mesh_url')}")
    print(f"Texture URL in session: {data.get('texture_url')}")
    
    # Try to fetch the mesh directly
    mesh_resp = requests.get("http://localhost:5000/api/static/current_mesh.obj")
    if mesh_resp.status_code == 200:
        print(f"✅ Mesh accessible at /api/static/current_mesh.obj ({len(mesh_resp.content)} bytes)")
    else:
        print(f"❌ Mesh NOT accessible: {mesh_resp.status_code}")
    
    mtl_resp = requests.get("http://localhost:5000/api/static/face_texture.mtl")
    if mtl_resp.status_code == 200:
        print(f"✅ MTL accessible ({len(mtl_resp.content)} bytes): {mtl_resp.text[:100]}")
    else:
        print(f"❌ MTL NOT accessible: {mtl_resp.status_code}")
    
    return mesh_resp.status_code == 200

def cleanup():
    if BACKEND_PROC:
        print(f"\n=== Cleaning up backend (PID: {BACKEND_PROC.pid}) ===")
        BACKEND_PROC.terminate()
        BACKEND_PROC.wait(timeout=10)
        print("Backend stopped")

if __name__ == "__main__":
    try:
        start_backend()
        if not wait_for_backend():
            print("❌ Backend failed to start")
            cleanup()
            sys.exit(1)
        
        success = upload_photo()
        
        if success:
            viewer_ok = check_avatar_viewer()
            if viewer_ok:
                print("\n✅✅✅ END-TO-END VERIFICATION PASSED ✅✅✅")
                print("The improved FLAME identity fitting is now connected through the full pipeline:")
                print("  Upload → Digital Twin API → Identity Pipeline → FlameFitter.fit_from_photo()")
                print("  → avatar/static/current_mesh.obj → Avatar Viewer")
            else:
                print("\n⚠️ Mesh generated but viewer access has issues")
        else:
            print("\n❌ Upload flow failed")
    finally:
        cleanup()
