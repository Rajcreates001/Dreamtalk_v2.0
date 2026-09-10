"""Test that the backend can be imported from the dreamtalk/backend/ directory."""
import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(script_dir, "dreamtalk", "backend")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Test 1: Import from project root (should always work)
print("=== Test 1: Import from project root ===")
sys.path.insert(0, script_dir)
# Clear any PYTHONPATH
for key in list(os.environ.keys()):
    if "PYTHON" in key.upper():
        del os.environ[key]
# Remove any existing dreamtalk from sys.modules
for mod in list(sys.modules.keys()):
    if "dreamtalk" in mod:
        del sys.modules[mod]

try:
    from dreamtalk.backend.main import app
    print(f"  [OK] {len(app.routes)} routes")
except Exception as e:
    print(f"  [FAIL] {e}")

# Clean up
for mod in list(sys.modules.keys()):
    if "dreamtalk" in mod or "backend" in mod:
        del sys.modules[mod]

# Test 2: Simulate running from dreamtalk/backend/ directory
print("\n=== Test 2: Import from dreamtalk/backend/ ===")
original_cwd = os.getcwd()
os.chdir(backend_dir)
print(f"  CWD: {os.getcwd()}")

# Add current dir to path (simulating python -m backend)
sys.path.insert(0, backend_dir)

try:
    # This is what python -m backend does: finds backend/__main__.py
    import backend.__main__
    print("  [OK] backend.__main__ loaded successfully")
except Exception as e:
    print(f"  [FAIL] {e}")

os.chdir(original_cwd)
print("\nDone")
