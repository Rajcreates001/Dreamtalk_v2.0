"""Debug the overindented blocks pattern."""
import ast

path = r'dreamtalk/cognition/core/consciousness/aura/interface/auth.py'
with open(path, encoding='utf-8') as f:
    lines = f.readlines()

BLOCK_KWS = ('def ', 'class ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'finally:', 'with ')

for i, line in enumerate(lines):
    stripped = line.lstrip()
    if not stripped:
        continue
    indent = len(line) - len(line.lstrip())
    
    is_block = False
    for kw in BLOCK_KWS:
        if stripped.startswith(kw):
            is_block = True
            break
        if stripped == kw.rstrip(':'):
            is_block = True
            break
        # for 'except' kw, also match 'except ValueError:' etc
        if kw == 'except' and stripped.startswith('except'):
            is_block = True
            break
    
    if not is_block:
        continue
    if stripped.startswith('#'):
        continue
    
    # find next meaningful line (skip blanks, comments, single-line docstrings)
    j = i + 1
    while j < len(lines):
        s = lines[j].strip()
        if not s:
            j += 1
            continue
        if s.startswith('#'):
            j += 1
            continue
        # skip single-line docstrings
        if s.startswith('"""') and s.count('"""') >= 2:
            j += 1
            continue
        break
    
    if j >= len(lines):
        continue
    
    n_indent = len(lines[j]) - len(lines[j].lstrip())
    
    if n_indent <= indent:
        print(f'L{i+1:3d} ({indent}): {stripped[:60]}')
        print(f'     next L{j+1:3d} ({n_indent}): {lines[j].strip()[:60]}')
        print()
