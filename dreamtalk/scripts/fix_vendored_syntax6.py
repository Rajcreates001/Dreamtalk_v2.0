"""Fix vendored Python 2→3 indentation errors.
Targets the specific pattern: over-indented def/class + fixer4-inserted pass lines.
"""
import ast
import os
import re

BLOCK_KWS = ['def ', 'class ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'finally:', 'with ', 'async def ']

def is_block(line):
    s = line.lstrip()
    for kw in BLOCK_KWS:
        if s.startswith(kw) or s == kw.rstrip(':'):
            return True
        if kw == 'except' and s.startswith('except'):
            return True
    return False

def validate(path):
    try:
        with open(path, encoding='utf-8') as f:
            ast.parse(f.read(), path)
        return True, None
    except SyntaxError as e:
        return False, (e.lineno, e.msg)

def fix_file(path):
    for iteration in range(20):
        ok, _ = validate(path)
        if ok:
            return True

        with open(path, encoding='utf-8') as f:
            lines = f.readlines()

        modified = False
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()
            indent = len(line) - len(line.lstrip())

            if not stripped or not is_block(line):
                i += 1
                continue

            # Find the body start (skip blank/comments)
            body_start = None
            for j in range(i+1, len(lines)):
                s = lines[j].strip()
                if not s:
                    continue
                if s.startswith('#'):
                    continue
                # Skip single-line docstrings like """...""
                if s.startswith('"""') and s.count('"""') >= 2:
                    continue
                # Skip multi-line docstring start
                if s.startswith('"""') or s.startswith("'''"):
                    k = j + 1
                    while k < len(lines):
                        if lines[k].strip().endswith('"""') or lines[k].strip().endswith("'''"):
                            body_start = k + 1
                            break
                        k += 1
                    if body_start:
                        break
                    # malformed docstring, skip
                    i = j + 1
                    break
                body_start = j
                break

            if body_start is None or body_start >= len(lines):
                i += 1
                continue

            body_indent = len(lines[body_start]) - len(lines[body_start].lstrip())

            # Case 1: body is at SAME indent as block header → over-indented
            if body_indent <= indent and indent >= 4:
                # Dedent this block line by 4
                lines[i] = ' ' * (indent - 4) + stripped
                modified = True
                # Re-process from same index
                continue

            # Case 2: body starts with 'pass' and next meaningful line is at indent <= block_indent
            # This means fixer4 erroneously inserted 'pass'
            body_line = lines[body_start].strip()
            if body_line == 'pass' and body_indent > indent:
                # Find next meaningful line after pass
                next_body = None
                for j in range(body_start + 1, len(lines)):
                    s = lines[j].strip()
                    if not s or s.startswith('#'):
                        continue
                    if s.startswith('"""') and s.count('"""') >= 2:
                        continue
                    next_body = j
                    break

                if next_body:
                    next_indent = len(lines[next_body]) - len(lines[next_body].lstrip())
                    if next_indent <= indent and indent >= 4:
                        # The pass was erroneously inserted, dedent the def and remove the pass
                        lines[i] = ' ' * (indent - 4) + stripped
                        del lines[body_start]  # remove the pass line
                        modified = True
                        continue

            # Case 3: body starts with a single-line docstring AND the docstring is
            # at the same indent as the block (meaning indentation corruption)
            if body_line.startswith('"""') and body_line.count('"""') >= 2 and body_indent <= indent and indent >= 4:
                lines[i] = ' ' * (indent - 4) + stripped
                modified = True
                continue

            i += 1

        if modified:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.writelines(lines)
        else:
            # No progress, break the loop
            break

    return validate(path)[0]


def main():
    all_files = []
    for r, ds, fs in os.walk('dreamtalk'):
        for f in fs:
            if f.endswith('.py'):
                all_files.append(os.path.join(r, f))

    failing = [(p, validate(p)[1]) for p in all_files if not validate(p)[0]]
    print(f'Before: {len(failing)} failing files')

    fixed_count = 0
    for p, _ in sorted(failing):
        if fix_file(p):
            fixed_count += 1
            print(f'  FIXED: {p}')

    still_failing = [(p, validate(p)[1]) for p in all_files if not validate(p)[0]]
    print(f'\nFixed: {fixed_count}/{len(failing)}')
    print(f'Still failing: {len(still_failing)}')

    clean = sum(1 for p in all_files if validate(p)[0])
    print(f'Total passing: {clean}/{len(all_files)}')

    for p, (ln, msg) in sorted(still_failing):
        print(f'  {p}:{ln} -> {msg}')

if __name__ == '__main__':
    main()
