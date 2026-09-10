"""
Batch fix Python 2 -> 3 syntax issues in vendored code.
Handles: BOM (already done), bare try blocks, mixed indent, invalid syntax.
"""
import ast, os, re, sys

def fix_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    
    original = src
    
    # Fix 1: bare "try:" followed by same-indent or lower-indent line
    # In Python 2, try:\n    pass was required but many vendored files have
    # try:\nfrom ... import ... (the import at module level, not under try)
    lines = src.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # Check if this is a "try:" line with no body
        if stripped == 'try:' and i + 1 < len(lines):
            indent = len(line) - len(line.lstrip())
            next_line = lines[i + 1]
            next_stripped = next_line.strip()
            if next_stripped:
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent <= indent:
                    # The next line is not indented under try.
                    # Add proper indentation (indent + 4)
                    new_lines.append(line)
                    # Indent the next line
                    lines[i + 1] = ' ' * (indent + 4) + next_stripped
                    i += 1
                    continue
        new_lines.append(line)
        i += 1
    src = '\n'.join(new_lines)
    
    # Fix 2: "unexpected indent" - lines with too much indentation
    # Common pattern: a line is indented more than its parent allows
    lines = src.split('\n')
    new_lines = []
    for line in lines:
        stripped = line.rstrip()
        if stripped and line != stripped:
            # trailing whitespace - remove
            line = stripped
        new_lines.append(line)
    src = '\n'.join(new_lines)
    
    # Fix 3: fix specific invalid syntax patterns
    # Replace Python 2 print statements
    src = re.sub(r'(?<!\w)print (?!\()(.*)', r'print(\1)', src)
    
    # Fix 4: fix except X, Y: -> except X as Y:
    src = re.sub(r'except\s+(\w+(?:\s*\.\s*\w+)*)\s*,(\s*\w+)\s*:', r'except \1 as \2:', src)
    
    if src != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(src)
        return True
    return False

def verify(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            ast.parse(f.read(), path)
        return True, None
    except SyntaxError as e:
        return False, (e.lineno, e.msg)

def main():
    failed_before = []
    for r, ds, fs in os.walk('dreamtalk'):
        for f in fs:
            if f.endswith('.py'):
                p = os.path.join(r, f)
                ok, err = verify(p)
                if not ok:
                    failed_before.append((p, err))
    
    print(f'Files with errors before fixes: {len(failed_before)}')
    
    fixed = 0
    still_failed = []
    for p, err in failed_before:
        if fix_file(p):
            fixed += 1
        ok, new_err = verify(p)
        if not ok:
            still_failed.append((p, new_err))
    
    print(f'Fixed: {fixed}')
    print(f'Still failing: {len(still_failed)}')
    for p, (ln, msg) in still_failed[:20]:
        print(f'  {p}:{ln} -> {msg}')
    if len(still_failed) > 20:
        print(f'  ... and {len(still_failed)-20} more')
    
    return len(still_failed)

if __name__ == '__main__':
    sys.exit(main())
