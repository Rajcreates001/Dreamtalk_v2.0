"""Fix vendored Python 2->3 syntax. Handles misplaced imports,
try/except/empty blocks, and invalid syntax in Aura/hermes vendored code."""
import ast, os, re

def validate(path):
    try:
        with open(path, encoding='utf-8') as f:
            ast.parse(f.read(), path)
        return True, None
    except SyntaxError as e:
        return False, (e.lineno, e.msg)

# ── Direct fixes for files with known patterns ──

def fix_misplaced_imports(path):
    """Fix imports at column 0 inside functions (the 'server.py' pattern)."""
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    
    # Build function/class/if/try scope map: for each line, what indent level are we in?
    # A line at column 0 that is between indented blocks is "orphaned"
    
    changed = False
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped or stripped.startswith('#'):
            continue
        indent = len(line) - len(line.lstrip())
        
        # Check if this line is at column 0 but looks like a statement
        # that should be inside a block
        if indent == 0 and not stripped.startswith(('#', '"""', "'''", '@', '\n')):
            # Look backwards for the nearest indented line
            prev_indent = None
            prev_is_block = False
            for j in range(i - 1, -1, -1):
                p_stripped = lines[j].strip()
                if not p_stripped:
                    continue
                p_indent = len(lines[j]) - len(lines[j].lstrip())
                if p_indent > 0:
                    prev_indent = p_indent
                    prev_is_block = p_stripped.rstrip().endswith(':')
                    break
                elif p_indent == 0 and p_stripped.rstrip().endswith(':'):
                    # This line is at column 0 and the previous is a def/class/if at 0
                    # So this IS at module level — skip
                    prev_indent = None
                    break
                else:
                    break
            
            # Look forward for the next non-empty line
            next_indent = None
            for j in range(i + 1, min(i + 10, len(lines))):
                n_stripped = lines[j].strip()
                if not n_stripped:
                    continue
                n_indent = len(lines[j]) - len(lines[j].lstrip())
                next_indent = n_indent
                break
            
            if prev_indent and prev_indent > 0 and next_indent and next_indent > 0:
                # Both surrounding lines are indented — this line is orphaned
                target_indent = prev_indent
                lines[i] = ' ' * target_indent + stripped
                changed = True
    
    if changed:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(lines)
    return changed


def fix_bare_try(path):
    """Fix 'try:' blocks with no except/finally."""
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    
    changed = False
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        indent = len(lines[i]) - len(lines[i].lstrip())
        
        if stripped == 'try:':
            # Look ahead for except/finally/else within same indent
            found_handler = False
            for j in range(i + 1, min(i + 100, len(lines))):
                j_stripped = lines[j].strip()
                if not j_stripped:
                    continue
                j_indent = len(lines[j]) - len(lines[j].lstrip())
                if j_indent == indent and j_stripped in ('except:', 'finally:', 'else:'):
                    found_handler = True
                    break
                if j_stripped.startswith(('except ', 'except\n', 'finally:', 'else:')):
                    # Check indent
                    if j_indent == indent:
                        found_handler = True
                        break
                if j_indent < indent and j_stripped and not j_stripped.startswith('#'):
                    break  # Left the try block without finding handler
            
            if not found_handler:
                # Add except: pass after the try block's body
                # Find the last line inside the try (dedented to indent level)
                body_end = i + 1
                while body_end < len(lines):
                    b_indent = len(lines[body_end]) - len(lines[body_end].lstrip())
                    b_stripped = lines[body_end].strip()
                    if not b_stripped or b_stripped.startswith('#'):
                        body_end += 1
                        continue
                    if b_indent <= indent:
                        break
                    body_end += 1
                
                lines.insert(body_end, ' ' * (indent + 4) + 'except Exception:\n')
                lines.insert(body_end + 1, ' ' * (indent + 8) + 'pass\n')
                changed = True
                i = body_end + 2
                continue
        
        i += 1
    
    if changed:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(lines)
    return changed


def fix_unexpected_indent(path):
    """Fix 'unexpected indent' by adjusting to match context."""
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    
    changed = False
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip())
        
        # Look at previous meaningful lines to determine expected indent
        prev_indents = []
        prev_endswith_colon = False
        for j in range(i - 1, max(-1, i - 20), -1):
            p_s = lines[j].strip()
            if not p_s or p_s.startswith('#'):
                continue
            p_i = len(lines[j]) - len(lines[j].lstrip())
            prev_indents.append(p_i)
            prev_endswith_colon = p_s.rstrip().endswith(':')
            break
        
        if not prev_indents:
            continue
        
        expected = prev_indents[0]
        if prev_endswith_colon:
            expected += 4
        
        if indent > expected + 4:
            # This line is over-indented
            lines[i] = ' ' * expected + stripped
            changed = True
    
    if changed:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(lines)
    return changed


def fix_unmatched_paren(path):
    """Fix unmatched parentheses."""
    with open(path, encoding='utf-8') as f:
        src = f.read()
    
    # Very targeted fix: remove extra ) on the error line
    changed = False
    # Just check the specific file
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        opens = line.count('(')
        closes = line.count(')')
        if closes > opens + 2:  # More than 2 extra closes
            # Remove the extras
            diff = closes - opens
            for _ in range(diff):
                last = line.rfind(')')
                if last >= 0:
                    line = line[:last] + line[last+1:]
            lines[i] = line
            changed = True
    
    if changed:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(lines)
    return changed


def fix_hermes_invalid_syntax(path):
    """Fix hermes_agent specific invalid syntax (trailing comma imports)."""
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    
    changed = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Fix: import statements with trailing comma
        if stripped.startswith('import ') and stripped.rstrip().endswith(','):
            lines[i] = line.rstrip().rstrip(',') + '\n'
            changed = True
        # Fix: from X import Y,  (trailing comma)
        if stripped.startswith('from ') and ' import ' in stripped and stripped.rstrip().endswith(','):
            lines[i] = line.rstrip().rstrip(',') + '\n'
            changed = True
    
    if changed:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(lines)
    return changed


def fix_file(path):
    # Determine the error category and apply targeted fixes
    ok, err = validate(path)
    if ok:
        return True
    
    ln, msg = err
    
    # Try each fixer
    fixers = [
        ('misplaced_imports', fix_misplaced_imports),
        ('unexpected_indent', fix_unexpected_indent),
        ('bare_try', fix_bare_try),
        ('unmatched_paren', fix_unmatched_paren),
        ('hermes_syntax', fix_hermes_invalid_syntax),
    ]
    
    for name, fixer in fixers:
        fixer(path)
        ok, err = validate(path)
        if ok:
            return True
    
    return False


def main():
    all_files = []
    for r, ds, fs in os.walk('dreamtalk'):
        for f in fs:
            if f.endswith('.py'):
                all_files.append(os.path.join(r, f))

    failing = [(p, validate(p)[1]) for p in all_files if not validate(p)[0]]
    print(f'Before: {len(failing)} failing files')
    
    fixed = 0
    for p, _ in failing:
        if fix_file(p):
            fixed += 1
    
    still_failing = [(p, validate(p)[1]) for p in all_files if not validate(p)[0]]
    print(f'Fixed: {fixed}/{len(failing)}')
    print(f'Still failing: {len(still_failing)}')
    
    clean = sum(1 for p in all_files if validate(p)[0])
    print(f'Total passing: {clean}/{len(all_files)}')
    
    for p, (ln, msg) in sorted(still_failing):
        print(f'  {p}:{ln} -> {msg}')
    
    return len(still_failing)

if __name__ == '__main__':
    exit(main())
