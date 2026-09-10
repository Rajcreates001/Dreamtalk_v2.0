"""Fix Python 2 -> 3 syntax: convert tabs->spaces, then fix structural issues."""
import ast, os

def has_tabs(path):
    with open(path, 'rb') as f:
        return b'\t' in f.read()

def detab(path):
    with open(path, encoding='utf-8') as f:
        src = f.read()
    # Replace tabs with 4 spaces
    new_src = src.replace('\t', '    ')
    if new_src != src:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(new_src)
        return True
    return False

def normalize_indents(path):
    """Detect and fix mixed tab/space indentation by full retab."""
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    new_lines = []
    changed = False
    for line in lines:
        # Count leading whitespace
        stripped = line.lstrip('\t ')
        leading = line[:len(line) - len(stripped)]
        # Replace any tabs in leading whitespace with 4 spaces
        new_leading = leading.replace('\t', '    ')
        # Also normalize spaces to 4-space multiples
        # Count spaces and round to nearest 4
        if new_leading:
            space_count = len(new_leading)
            # Round to nearest 4
            rounded = (space_count // 4) * 4
            if rounded != space_count:
                new_leading = ' ' * rounded
                changed = True
        new_line = new_leading + stripped
        if new_line != line:
            changed = True
        new_lines.append(new_line)
    if changed:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(new_lines)
    return changed

def add_missing_bodies(path):
    """Add 'pass' for empty function/if/for/while/try/except/finally blocks."""
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    
    changed = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Check if line ends with ':' and could start a block
        if stripped.endswith(':') and not stripped.startswith('#'):
            indent = len(line) - len(line.lstrip())
            # Look for the next non-empty, non-comment line
            j = i + 1
            while j < len(lines) and lines[j].strip() in ('', '#', '\n'):
                j += 1
            if j < len(lines):
                next_line = lines[j]
                next_indent = len(next_line) - len(next_line.lstrip())
                next_stripped = next_line.strip()
                if next_indent <= indent or next_stripped.startswith('#'):
                    # The block is empty or the next meaningful line is at same/lower indent
                    # Add 'pass' under this block
                    block_keywords = ('if ', 'else:', 'elif ', 'for ', 'while ', 'def ', 
                                      'class ', 'try:', 'except', 'finally:', 'with ', 'async ')
                    if any(stripped.startswith(k) for k in block_keywords):
                        # Add one more meaningful line: pass
                        lines.insert(j, ' ' * (indent + 4) + 'pass\n')
                        changed = True
                        i = j + 1
                        continue
        i += 1
    if changed:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(lines)
    return changed

def validate(path):
    try:
        with open(path, encoding='utf-8') as f:
            ast.parse(f.read(), path)
        return True, None
    except SyntaxError as e:
        return False, (e.lineno, e.msg)

def main():
    # Find all .py files
    all_files = []
    for r, ds, fs in os.walk('dreamtalk'):
        for f in fs:
            if f.endswith('.py'):
                all_files.append(os.path.join(r, f))
    
    # Phase 1: detab ALL files
    tab_count = sum(1 for p in all_files if has_tabs(p))
    detab_count = sum(1 for p in all_files if detab(p))
    print(f'Phase 1: {detab_count}/{tab_count} tab files detabbed')
    
    # Phase 2: normalize indentation in failing files
    failing = [p for p in all_files if not validate(p)[0]]
    print(f'Phase 2: {len(failing)} files still failing after detab')
    
    for p in failing:
        normalize_indents(p)
    
    # Phase 3: add missing bodies
    failing = [p for p in all_files if not validate(p)[0]]
    print(f'Phase 3: {len(failing)} files still failing after indent normalize')
    
    for p in failing:
        add_missing_bodies(p)
    
    # Phase 4: fix remaining try/except issues
    failing = [p for p in all_files if not validate(p)[0]]
    print(f'Phase 4: {len(failing)} files still failing after bodies')
    
    # For remaining issues, try a more aggressive approach:
    # Analyze each file and fix remaining syntax errors
    still_failing = []
    for p in failing:
        ok, err = validate(p)
        if not ok:
            ln, msg = err
            # Read the file again
            with open(p, encoding='utf-8') as f:
                lines = f.readlines()
            
            changed = False
            
            # Common remaining patterns:
            # 1. try with no except/finally -> add except: pass
            # 2. unexpected indent -> find context and fix
            # 3. unmatched ')' -> balance parens
            
            if msg == "expected 'except' or 'finally' block":
                # Find the try and add except
                idx = ln - 1
                for j in range(idx, -1, -1):
                    if lines[j].strip() == 'try:':
                        try_indent = len(lines[j]) - len(lines[j].lstrip())
                        lines.insert(idx + 1, ' ' * (try_indent + 4) + 'except Exception:\n')
                        lines.insert(idx + 2, ' ' * (try_indent + 8) + 'pass\n')
                        changed = True
                        break
            
            elif 'unexpected indent' in msg or "unindent does not match" in msg:
                idx = ln - 1
                # Look at the previous meaningful line
                prev = idx - 1
                while prev >= 0 and lines[prev].strip() in ('', '\n'):
                    prev -= 1
                if prev >= 0:
                    prev_indent = len(lines[prev]) - len(lines[prev].lstrip())
                    curr_indent = len(lines[idx]) - len(lines[idx].lstrip())
                    # Check if this should be a continuation or a new block level
                    if prev_indent < curr_indent:
                        # Fix by aligning with previous
                        lines[idx] = ' ' * prev_indent + lines[idx].lstrip()
                        changed = True
            
            elif "unmatched ')'" in msg:
                idx = ln - 1
                line = lines[idx]
                opens = line.count('(')
                closes = line.count(')')
                if closes > opens:
                    last = line.rfind(')')
                    lines[idx] = line[:last] + line[last+1:]
                    changed = True
            
            if changed:
                with open(p, 'w', encoding='utf-8', newline='') as f:
                    f.writelines(lines)
    
    # Final count
    total = 0
    clean = 0
    final_failing = []
    for p in all_files:
        ok, err = validate(p)
        total += 1
        if ok:
            clean += 1
        else:
            final_failing.append((p, err))
    
    print(f'\nFinal: {clean}/{total} .py files pass syntax check')
    print(f'Still failing: {len(final_failing)}')
    for p, (ln, msg) in sorted(final_failing):
        print(f'  {p}:{ln} -> {msg}')
    
    return len(final_failing)

if __name__ == '__main__':
    exit(main())
