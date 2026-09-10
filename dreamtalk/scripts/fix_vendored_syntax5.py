"""Fix vendored Python 2->3: over-indented def/class/if blocks."""
import ast, os

def validate(path):
    try:
        with open(path, encoding='utf-8') as f:
            ast.parse(f.read(), path)
        return True, None
    except SyntaxError as e:
        return False, (e.lineno, e.msg)

BLOCK_KEYWORDS = ('def ', 'class ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'finally:', 'with ', 'async ')

def fix_overindented_blocks(path):
    """Fix def/class/if at indent N where body is at indent <= N (should be at indent N-4)."""
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    
    changed = False
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped:
            continue
        
        # Find block starters
        is_block = False
        for kw in BLOCK_KEYWORDS:
            if stripped.startswith(kw) or stripped == kw.rstrip(':'):
                is_block = True
                break
        if not is_block:
            continue
        if stripped.startswith('#'):
            continue
        
        block_indent = len(line) - len(line.lstrip())
        
        # Find the next meaningful line
        next_idx = i + 1
        while next_idx < len(lines):
            n_stripped = lines[next_idx].strip()
            if n_stripped and not n_stripped.startswith('#') and not n_stripped.startswith(('"""', "'''")):
                break
            if n_stripped and n_stripped.startswith(('"""', "'''")):
                # Docstring — look past it
                quote = n_stripped[:3]
                end_idx = next_idx
                while end_idx < len(lines):
                    if quote in lines[end_idx].strip():
                        break
                    end_idx += 1
                next_idx = end_idx + 1
                continue
            next_idx += 1
        
        if next_idx >= len(lines):
            continue
        
        next_line = lines[next_idx]
        next_indent = len(next_line) - len(next_line.lstrip())
        
        # If body indent <= block indent, the block is over-indented
        if next_indent <= block_indent and block_indent >= 4:
            # Dedent the block line by 4
            lines[i] = ' ' * (block_indent - 4) + stripped
            changed = True
    
    if changed:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(lines)
    return changed


def fix_misplaced_imports_v2(path):
    """Fix imports at column 0 when surrounded by indented code."""
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    
    changed = False
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        indent = len(line) - len(line.lstrip())
        
        if indent > 0:
            continue
        if not stripped or stripped.startswith(('#', '@', '\n')):
            continue
        
        # Check if this is a statement that should be inside a block
        # Look backward for indented code
        found_indented_before = False
        for j in range(i - 1, max(-1, i - 5), -1):
            p = lines[j].strip()
            if p and not p.startswith('#'):
                p_indent = len(lines[j]) - len(lines[j].lstrip())
                if p_indent > 0:
                    found_indented_before = True
                    break
                break
        
        found_indented_after = False
        target_indent = 0
        for j in range(i + 1, min(len(lines), i + 5)):
            n = lines[j].strip()
            if n and not n.startswith('#'):
                n_indent = len(lines[j]) - len(lines[j].lstrip())
                if n_indent > 0:
                    found_indented_after = True
                    target_indent = n_indent
                break
        
        if found_indented_before and found_indented_after and target_indent > 0:
            lines[i] = ' ' * target_indent + stripped
            changed = True
    
    if changed:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(lines)
    return changed


def fix_empty_blocks(path):
    """Add pass to empty function/class/if/for/try/except/finally blocks."""
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    
    changed = False
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue
        
        indent = len(lines[i]) - len(lines[i].lstrip())
        is_block = False
        for kw in BLOCK_KEYWORDS:
            if stripped.startswith(kw) or stripped == kw.rstrip(':'):
                is_block = True
                break
        if not is_block or stripped.startswith('#'):
            i += 1
            continue
        
        # Find body — skip docstrings
        j = i + 1
        docstring_skipped = False
        while j < len(lines):
            js = lines[j].strip()
            if not js:
                j += 1
                continue
            if js.startswith(('"""', "'''")):
                # Skip docstring
                docstring_skipped = True
                quote = js[:3]
                j += 1
                while j < len(lines):
                    if quote in lines[j].strip():
                        j += 1
                        break
                    j += 1
                continue
            break
        
        body_indent = len(lines[j]) - len(lines[j].lstrip()) if j < len(lines) else 0
        
        if j >= len(lines) or body_indent <= indent:
            # Empty block — add pass
            body_indent_target = indent + 4
            lines.insert(j, ' ' * body_indent_target + 'pass\n')
            changed = True
            i = j + 1
        else:
            i = j
    
    if changed:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(lines)
    return changed


def fix_file(path):
    # Iterative passes
    for _ in range(10):
        ok, err = validate(path)
        if ok:
            return True
        
        ln, msg = err
        
        # Apply fixers in order
        fix_overindented_blocks(path)
        ok, err = validate(path)
        if ok: return True
        
        fix_misplaced_imports_v2(path)
        ok, err = validate(path)
        if ok: return True
        
        fix_empty_blocks(path)
        ok, err = validate(path)
        if ok: return True
        
        # If we got here and nothing changed, break
        with open(path, encoding='utf-8') as f:
            before = f.read()
        
        fix_overindented_blocks(path)
        fix_misplaced_imports_v2(path)
        fix_empty_blocks(path)
        
        with open(path, encoding='utf-8') as f:
            after = f.read()
        
        if before == after:
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
    for p, _ in failing:
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
