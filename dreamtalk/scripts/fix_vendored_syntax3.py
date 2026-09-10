"""Fix vendored Python 2->3 syntax: misplaced imports, try/except, empty blocks."""
import ast, os

def validate(path):
    try:
        with open(path, encoding='utf-8') as f:
            ast.parse(f.read(), path)
        return True, None
    except SyntaxError as e:
        return False, (e.lineno, e.msg)

def fix_file(path):
    """Multi-pass fix for common vendored syntax errors."""
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()

    changed = False
    max_passes = 20

    for _pass in range(max_passes):
        ok, err = validate(path)
        if ok:
            return True

        ln, msg = err
        idx = ln - 1
        if idx >= len(lines):
            break

        fixed = False

        # Fix: misplaced "from ... import ..." or "import ..." at col 0 inside a block
        if msg in ('invalid syntax', "unexpected indent", "unindent does not match any outer indentation level"):
            line = lines[idx]
            stripped = line.lstrip()
            # Check if this is an import statement at wrong indent
            if stripped.startswith(('import ', 'from ')):
                # Find the indent of the surrounding block by looking at previous lines
                prev_indent = None
                for j in range(idx - 1, -1, -1):
                    p = lines[j].strip()
                    if p and not p.startswith('#') and not p.startswith('"""') and not p.startswith("'''"):
                        pi = len(lines[j]) - len(lines[j].lstrip())
                        # Check if the previous line ends with : (block starter)
                        if p.rstrip().endswith(':') or p.rstrip().endswith('\\'):
                            continue
                        # Lines inside a block
                        if pi > 0:
                            prev_indent = pi
                            break
                        elif pi == 0 and lines[idx].strip().startswith(('import ', 'from ')):
                            # This import is at col 0 inside a function - need module-level context
                            # Check if the line before last non-blank was at higher indent
                            for k in range(idx - 1, -1, -1):
                                pk = lines[k].strip()
                                if pk and not pk.startswith('#') and not pk.startswith('"""') and not pk.startswith("'''"):
                                    pki = len(lines[k]) - len(lines[k].lstrip())
                                    if pki > 0:
                                        prev_indent = pki
                                        break
                                    break
                            break
                
                if prev_indent is not None and prev_indent > 0:
                    # The import is inside a block - indent it
                    lines[idx] = ' ' * prev_indent + stripped
                    changed = True
                    fixed = True

        # Fix: expected 'except' or 'finally' block
        if not fixed and msg == "expected 'except' or 'finally' block":
            # Find the matching try and add except: pass
            for j in range(idx, -1, -1):
                if lines[j].strip() == 'try:':
                    try_indent = len(lines[j]) - len(lines[j].lstrip())
                    lines.insert(idx + 1, ' ' * (try_indent + 4) + 'except Exception:\n')
                    lines.insert(idx + 2, ' ' * (try_indent + 8) + 'pass\n')
                    changed = True
                    fixed = True
                    break

        # Fix: "expected an indented block after 'if' statement"
        if not fixed and msg.startswith("expected an indented block after"):
            # Find the parent block and add pass
            indent = len(lines[idx]) - len(lines[idx].lstrip())
            lines.insert(idx + 1, ' ' * (indent + 4) + 'pass\n')
            changed = True
            fixed = True

        # Fix: "unmatched ')'"
        if not fixed and "unmatched ')'" in msg:
            # Remove the extra closing paren
            line = lines[idx]
            opens = line.count('(')
            closes = line.count(')')
            if closes > opens:
                last = line.rfind(')')
                lines[idx] = line[:last] + line[last+1:]
                changed = True
                fixed = True

        if fixed:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.writelines(lines)
        else:
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

    fixed = 0
    for p, _ in failing:
        if fix_file(p):
            fixed += 1
    
    final_failing = [(p, validate(p)[1]) for p in all_files if not validate(p)[0]]
    print(f'Fixed: {fixed}/{len(failing)}')
    print(f'Still failing: {len(final_failing)}')
    
    clean = sum(1 for p in all_files if validate(p)[0])
    print(f'Total passing: {clean}/{len(all_files)}')

    with open('fix_vendored_failures.log', 'w') as f:
        for p, (ln, msg) in sorted(final_failing):
            f.write(f'{p}:{ln} -> {msg}\n')
            with open(p, encoding='utf-8') as fh:
                context = fh.readlines()[max(0,ln-3):ln+2]
            for i, cl in enumerate(context):
                f.write(f'  {ln-2+i}: {cl.rstrip()}\n')
            f.write('\n')

    return len(final_failing)

if __name__ == '__main__':
    exit(main())
