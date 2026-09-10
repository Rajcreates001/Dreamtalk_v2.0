"""Test script to trace imports of dreamtalk.backend.main"""
import sys
import time

for m in list(sys.modules.keys()):
    if m.startswith('dreamtalk'):
        del sys.modules[m]

t0 = time.time()
sys.path.insert(0, '/app')

print(f'[{time.time()-t0:.1f}s] Starting import of main.py')

try:
    import dreamtalk.backend.main
    app = dreamtalk.backend.main.app
    print(f'[{time.time()-t0:.1f}s] IMPORT COMPLETE')
    trace = getattr(dreamtalk.backend.main, '_import_trace', [])
    for line in trace:
        print(f'  {line}')
except Exception as e:
    print(f'[{time.time()-t0:.1f}s] FAILED: {e}')
    import traceback
    traceback.print_exc()
