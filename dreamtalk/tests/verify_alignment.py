"""
Phase 13: Full repo-to-Dreamtalk alignment verification.
Checks every extracted file for import hygiene, license preservation,
and structural completeness.
"""

import os
import re
import sys

DREAMTALK_ROOT = r"D:\Black folder\DreamTalk_Startup\Dreamtalk-Integrated\dreamtalk"
EXCLUDED_DIRS = {".git", "__pycache__", "node_modules", ".next", "weights", "frontend"}

total_files = 0
py_files = 0
tsx_files = 0
import_issues = []
license_issues = []
branding_issues = []
ok_imports = 0
ok_licenses = 0

BRANDED_NAMES = [
    "GPT-SoVITS",
    "RVC",
    "MuseTalk",
    "LivePortrait",
    "SadTalker",
    "IDOL",
    "MHR",
    "FLAME-Avatar",
    "Brain-Cog",
    "OpenAvatarChat",
    "hermes-agent",
    "handcrafted-persona",
    "Utsuwa",
    "mem0",
    "Letta",
    "Zep",
    "MemoryOS",
    "Memanto",
    "OpenHuman",
    "Neurologique",
]

LICENSE_KEYWORDS = [
    "MIT License",
    "Apache License",
    "Apache 2.0",
    "Copyright (c)",
    "Copyright",
    "License",
    "SPDX",
]

ORIGINAL_IMPORT_PATTERNS = [
    r"from\s+(?:libs?\.|src\.|app\.|modules?\.|core\.|utils\.|tools\.|providers?\.)",
    r"import\s+(?:libs?\.|src\.|app\.|modules?\.)",
]

DREAMTALK_PREFIX = "dreamtalk."


def walk_dir(root):
    global total_files, py_files, tsx_files
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith(".")]
        for f in filenames:
            total_files += 1
            if f.endswith(".py"):
                py_files += 1
            elif f.endswith((".tsx", ".ts", ".jsx", ".js")):
                tsx_files += 1
            yield os.path.join(dirpath, f)


def check_file(filepath):
    global import_issues, license_issues, branding_issues, ok_imports, ok_licenses

    rel = os.path.relpath(filepath, DREAMTALK_ROOT)
    ext = os.path.splitext(filepath)[1]

    if ext not in (".py", ".tsx", ".ts", ".jsx", ".js"):
        return

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return

    lines = content.split("\n")

    # Check 1: License header presence
    has_license = any(kw.lower() in content.lower() for kw in LICENSE_KEYWORDS)
    if has_license:
        ok_licenses += 1
    else:
        license_issues.append(f"{rel} (no license header)")

    # Check 2: Original imports (should be rewritten to dreamtalk.*)
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            # Skip standard lib / third-party
            if any(stripped.startswith(f"import {x}") or stripped.startswith(f"from {x}") for x in
                   ["os", "sys", "typing", "json", "pathlib", "abc", "io", "re", "math",
                    "fastapi", "uvicorn", "pydantic", "httpx", "torch", "numpy", "torchmetrics",
                    "transformers", "PIL", "flask", "django", "cv2", "audio",
                    "collections", "functools", "itertools", "concurrent", "multiprocessing",
                    "dataclasses", "enum", "hashlib", "datetime", "time", "random",
                    "uuid", "copy", "inspect", "warnings", "logging", "socket",
                    "http", "urllib", "email", "xml", "pickle", "tempfile",
                    "shutil", "glob", "fnmatch", "statistics", "decimal", "fractions",
                    "unittest", "pytest", "hypothesis", "pdb", "traceback", "pprint",
                    "textwrap", "string", "struct", "binascii", "base64", "zlib",
                    "gzip", "bz2", "lzma", "zipfile", "tarfile", "configparser",
                    "argparse", "getopt", "optparse", "atexit", "signal", "platform",
                    "ctypes", "curses", "getpass", "locale", "calendar", "email",
                    "html", "numbers", "secrets", "shelve", "sqlite3", "socketserver",
                    "subprocess", "sympy", "pkgutil", "importlib", "ast",
                    "next", "react", "react-dom", "motion", "clsx", "lucide-react",
                    "@radix-ui", "sonner", "tailwind-merge", "class-variance-authority",
                    "geist", "next/", "@/"]):
                continue

            if DREAMTALK_PREFIX not in stripped:
                # This is a non-dreamtalk import - check if it's pointing to original module structure
                for pat in ORIGINAL_IMPORT_PATTERNS:
                    if re.match(pat, stripped):
                        import_issues.append(f"{rel}:{i}: {stripped}")
                        break
                else:
                    # Could be a local import (from .xxx import yyy) - that's fine
                    if not stripped.startswith("from .") and not stripped.startswith("import ."):
                        ok_imports += 1

    # Check 3: Branded repo names in content
    for brand in BRANDED_NAMES:
        if brand.lower() in content.lower():
            # Only flag if it's not in a comment about extraction origin
            for line in lines:
                if brand.lower() in line.lower():
                    # Check if it's an attribution comment
                    if "extracted from" in line.lower() or "license" in line.lower():
                        continue
                    branding_issues.append(f"{rel}: {brand} found")
                    break


def main():
    print("=" * 60)
    print("Phase 13: Repo-to-Dreamtalk Alignment Verification")
    print("=" * 60)
    print()

    for fp in walk_dir(DREAMTALK_ROOT):
        check_file(fp)

    print(f"Total files scanned: {total_files}")
    print(f"  Python files: {py_files}")
    print(f"  TSX/TS/JS files: {tsx_files}")
    print(f"  Other files: {total_files - py_files - tsx_files}")
    print()

    print(f"License headers found: {ok_licenses}/{py_files + tsx_files} files")
    if license_issues:
        print(f"  Files missing license headers ({len(license_issues)}):")
        for issue in license_issues[:10]:
            print(f"    - {issue}")
        if len(license_issues) > 10:
            print(f"    ... and {len(license_issues) - 10} more")
    else:
        print("  All files have license headers!")
    print()

    print(f"Import check: {ok_imports} non-dreamtalk imports are local/correct")
    if import_issues:
        print(f"  Potential original-import issues ({len(import_issues)}):")
        for issue in import_issues[:10]:
            print(f"    - {issue}")
        if len(import_issues) > 10:
            print(f"    ... and {len(import_issues) - 10} more")
    else:
        print("  No original-import issues found!")
    print()

    if branding_issues:
        print(f"Branding issues ({len(branding_issues)}):")
        for issue in branding_issues[:10]:
            print(f"    - {issue}")
        if len(branding_issues) > 10:
            print(f"    ... and {len(branding_issues) - 10} more")
    else:
        print("No branding issues found!")
    print()

    print("=" * 60)
    score = 0
    if ok_licenses > 0:
        score += 30
    if not import_issues:
        score += 35
    if not branding_issues:
        score += 35
    print(f"Alignment Score: {score}/100")
    if score >= 90:
        print("Status: EXCELLENT - repo alignment is clean")
    elif score >= 70:
        print("Status: GOOD - minor issues remain")
    else:
        print("Status: NEEDS WORK - significant alignment issues found")
    print("=" * 60)


if __name__ == "__main__":
    main()
