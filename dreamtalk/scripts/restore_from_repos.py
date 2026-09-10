"""Restore vendored files from original repos, then re-fix any real Python 2->3 issues.

Usage:
    cd dreamtalk/ && python scripts/restore_from_repos.py
"""
import ast, os, shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent  # dreamtalk/
DREAMTALK = str(SCRIPT_DIR)
REPOS = str(SCRIPT_DIR / 'repos-used')

# Mapping of vendored path (relative to dreamtalk/) -> original repo-relative path
MAPPING = {
    # Hermes Agent
    'orchestration/agents/hermes_agent/agent/credential_pool.py':
        f'{REPOS}/hermes-agent/agent/credential_pool.py',
    'orchestration/agents/hermes_agent/hermes_cli/auth_commands.py':
        f'{REPOS}/hermes-agent/hermes_cli/auth_commands.py',

    # OpenAvatarChat (note: src/ prefix in repo)
    'orchestration/chat/openavatar_chat/handlers/client/ws_lam_client/ws_lam_client_handler.py':
        f'{REPOS}/OpenAvatarChat/src/handlers/client/ws_lam_client/ws_lam_client_handler.py',

    # Memanto
    'brain/memory/core/memanto_memory/cli/main.py':
        f'{REPOS}/memanto/memanto/cli/main.py',
}

def validate(path):
    try:
        with open(path, encoding='utf-8') as f:
            ast.parse(f.read(), path)
        return True, None
    except SyntaxError as e:
        return False, (e.lineno, e.msg)


def main():
    # Walk dreamtalk/ for all .py files
    all_py = []
    for r, ds, fs in os.walk(DREAMTALK):
        # Skip repos-used and hidden dirs
        ds[:] = [d for d in ds if not d.startswith('.') and d != 'repos-used']
        for f in fs:
            if f.endswith('.py'):
                all_py.append(os.path.join(r, f))

    failing_before = [(p, validate(p)[1]) for p in all_py if not validate(p)[0]]
    print(f'Before restore: {len(failing_before)} failing files')

    # Restore from originals
    restored = 0
    failed_restore = []
    for vendored_rel, original_abs in MAPPING.items():
        vendored_abs = os.path.join(DREAMTALK, vendored_rel)
        try:
            if os.path.exists(original_abs):
                shutil.copy2(original_abs, vendored_abs)
                restored += 1
                print(f'  RESTORED: {vendored_rel}')
            else:
                failed_restore.append((vendored_rel, f'Source not found: {original_abs}'))
                print(f'  SKIPPED: {vendored_rel} (source not found)')
        except Exception as e:
            failed_restore.append((vendored_rel, str(e)))
            print(f'  FAILED: {vendored_rel} -> {e}')

    print(f'\nRestored: {restored}/{len(MAPPING)}')
    if failed_restore:
        print(f'Failed/Skipped: {len(failed_restore)}')
        for p, e in failed_restore:
            print(f'  {p}: {e}')

    # Validate after restore
    failing_after = [(p, validate(p)[1]) for p in all_py if not validate(p)[0]]
    print(f'\nAfter restore: {len(failing_after)} failing files')
    for p, (ln, msg) in sorted(failing_after):
        print(f'  {p}:{ln} -> {msg}')
    
    total_ok = len(all_py) - len(failing_after)
    print(f'\nTotal passing: {total_ok}/{len(all_py)}')

if __name__ == '__main__':
    main()
