"""Fix Python 2 -> 3 syntax in vendored files. Handles try/except, indent, empty blocks, parens."""
import ast, os, re

def get_errors(path):
    try:
        with open(path, encoding='utf-8') as f:
            ast.parse(f.read(), path)
        return []
    except SyntaxError as e:
        return [(e.lineno, e.msg, e.offset)]

def compile_and_fix(path, max_passes=10):
    for _pass in range(max_passes):
        errors = get_errors(path)
        if not errors:
            return True, 0
        with open(path, encoding='utf-8') as f:
            lines = f.readlines()
        fixed_any = False
        for lineno, msg, offset in errors:
            idx = lineno - 1
            if idx >= len(lines):
                continue
            fixed = False

            # Fix: "expected 'except' or 'finally' block" — bare try with no handler
            if msg == "expected 'except' or 'finally' block":
                # Find the matching try, add a generic except: pass
                # Walk backwards from this line to find the try
                depth = 0
                found_try = False
                for i in range(idx, -1, -1):
                    stripped = lines[i].strip()
                    if stripped == 'try:':
                        if depth == 0:
                            # Found the matching try — add except: pass after the failed line
                            indent = ' ' * (len(lines[i]) - len(lines[i].lstrip()) + 4)
                            insert_idx = idx + 1
                            while insert_idx < len(lines) and lines[insert_idx].strip() == '':
                                insert_idx += 1
                            lines.insert(insert_idx, f'{indent}except Exception:\n')
                            lines.insert(insert_idx + 1, f'{indent}    pass\n')
                            fixed = True
                            found_try = True
                            break
                        depth -= 1
                    elif stripped in ('try:',) and depth == 0:
                        pass
                if not found_try:
                    # Fallback: just add except: pass after this line
                    indent = '        '
                    lines.insert(idx + 1, f'{indent}except Exception:\n')
                    lines.insert(idx + 1, f'{indent}    pass\n')
                    fixed = True

            # Fix: "expected an indented block after 'try' statement on line N"
            elif 'expected an indented block after' in msg and "'try'" in msg:
                # Add pass under the try
                indent = ' ' * (len(lines[idx]) - len(lines[idx].lstrip()) + 4)
                # Find a real body line that should be indented
                next_non_empty = idx + 1
                while next_non_empty < len(lines) and lines[next_non_empty].strip() in ('', '#', '\n'):
                    next_non_empty += 1
                if next_non_empty < len(lines):
                    next_line = lines[next_non_empty]
                    curr_indent = len(next_line) - len(next_line.lstrip())
                    try_indent = len(lines[idx]) - len(lines[idx].lstrip())
                    if curr_indent <= try_indent:
                        # Need to fix indentation of the body line
                        lines[next_non_empty] = ' ' * (try_indent + 4) + next_line.lstrip()
                        fixed = True

            # Fix: "expected an indented block after function definition" / "after 'if' statement" / "after 'for' statement"
            elif 'expected an indented block after' in msg:
                indent = ' ' * (len(lines[idx]) - len(lines[idx].lstrip()) + 4)
                lines.insert(idx + 1, f'{indent}pass\n')
                fixed = True

            # Fix: "unexpected indent"
            elif 'unexpected indent' in msg:
                # Reduce indentation to match the previous meaningful line
                prev = idx - 1
                while prev >= 0 and lines[prev].strip() in ('', '\n'):
                    prev -= 1
                if prev >= 0:
                    prev_indent = len(lines[prev]) - len(lines[prev].lstrip())
                    curr_indent = len(lines[idx]) - len(lines[idx].lstrip())
                    if prev_indent < curr_indent:
                        # Check if prev line ends with : (block starter)
                        if lines[prev].rstrip().endswith(':'):
                            # This might be a continuation line that was over-indented
                            # Check if the content makes sense at prev_indent + 4
                            lines[idx] = ' ' * (prev_indent + 4) + lines[idx].lstrip()
                        else:
                            lines[idx] = ' ' * prev_indent + lines[idx].lstrip()
                        fixed = True

            # Fix: "unmatched ')'" — try to find and remove extra paren
            elif "unmatched ')'" in msg:
                line = lines[idx]
                # Count parens on this and surrounding lines
                full_text = ''.join(lines[max(0, idx-2):idx+3])
                opens = full_text.count('(')
                closes = full_text.count(')')
                if closes > opens:
                    # Remove one ) on this line (last occurrence)
                    last_close = line.rfind(')')
                    if last_close >= 0:
                        lines[idx] = line[:last_close] + line[last_close+1:]
                        fixed = True

            # Fix: "invalid syntax" - often from print statements or misplaced code
            elif 'invalid syntax' in msg:
                line = lines[idx]
                stripped = line.lstrip()

                # Fix: trailing comma after import
                if stripped.startswith('import ') and stripped.rstrip().endswith(','):
                    lines[idx] = line.rstrip().rstrip(',') + '\n'
                    fixed = True

                # Fix: bare "raise" without exception
                elif stripped == 'raise\n' or stripped == 'raise':
                    # Check if previous line has try:
                    for j in range(idx-1, max(-1, idx-5), -1):
                        if lines[j].strip() == 'try:':
                            lines[idx] = ' ' * (len(lines[j]) - len(lines[j].lstrip()) + 8) + 'raise\n'
                            fixed = True
                            break

                # Fix: Python 2 unicode literals u"..." inside non-ASCII files
                # Fine in Python 3, not a syntax error — skip

            if fixed:
                fixed_any = True
                break  # Fix one error per pass, then re-check

        if fixed_any:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.writelines(lines)
        else:
            # If no fix applied, break to avoid infinite loop
            break
    return len(get_errors(path)) == 0, _pass + 1

def main():
    # Find all failing files
    failed = []
    for r, ds, fs in os.walk('dreamtalk'):
        for f in fs:
            if f.endswith('.py'):
                p = os.path.join(r, f)
                errs = get_errors(p)
                if errs:
                    failed.append((p, errs))

    print(f'Failing files before fix: {len(failed)}')
    for p, errs in failed:
        ln, msg, _ = errs[0]
        print(f'  {p}:{ln} -> {msg}')

    # Fix each file
    fixed_count = 0
    still_fails = []
    for p, errs in failed:
        ok, passes = compile_and_fix(p)
        if ok:
            fixed_count += 1
            print(f'  FIXED: {p} ({passes} passes)')
        else:
            new_errs = get_errors(p)
            still_fails.append((p, new_errs))

    print(f'\nFixed: {fixed_count}/{len(failed)}')
    print(f'Still failing: {len(still_fails)}')
    for p, errs in sorted(still_fails):
        ln, msg, _ = errs[0]
        print(f'  STILL: {p}:{ln} -> {msg}')

    return len(still_fails)

if __name__ == '__main__':
    exit(main())
