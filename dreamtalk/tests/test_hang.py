import sys
import time
import traceback
import threading

results = {}

def target():
    try:
        import asyncio
        from dreamtalk.backend.api.v1.endpoints.avatar import load_all_models
        t_import = time.time()
        results['imported'] = t_import
        asyncio.run(load_all_models())
        t_done = time.time()
        results['done'] = t_done
    except Exception as e:
        results['error'] = str(e)
        results['tb'] = traceback.format_exc()

t = threading.Thread(target=target)
t.start()
t.join(timeout=60)

if 'done' in results:
    t_import = results['imported']
    t_done = results['done']
    print(f'Completed in {t_done - t_import:.1f}s')
elif 'error' in results:
    print(f'Error: {results["error"]}')
else:
    print('TIMEOUT - dumping stacks:')
    for th_id, frame in sys._current_frames().items():
        print(f'\n--- Thread {th_id} ---')
        traceback.print_stack(frame)
