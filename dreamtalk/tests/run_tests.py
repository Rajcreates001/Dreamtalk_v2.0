#!/usr/bin/env python3
"""
DreamTalk — Comprehensive Test Runner

Discovers and runs all test files in the project, reports results,
and provides a summary. Supports filtering by test category.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --category brain   # Run only brain tests
    python run_tests.py --category api     # Run only API tests
    python run_tests.py --category emotion # Run only emotion tests
    python run_tests.py --category pipeline # Run only pipeline tests
    python run_tests.py --list             # List discovered tests
"""

import subprocess
import sys
import time
import os
from pathlib import Path
import argparse
from typing import List, Tuple, Optional

# ── Constants ──────────────────────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

PROJECT_ROOT = Path(__file__).resolve().parent

TEST_CATEGORIES: dict[str, List[Tuple[str, str, Optional[str]]]] = {
    "all": [
        ("Pipeline Integration", "test_full_integration.py", None),
        ("Pipeline Full", "test_pipeline_full.py", None),
        ("API Endpoints", "test_api_endpoints.py", None),
        ("Brain Tests", "test_brain.py", None),
        ("Brain V2", "test_brain_v2.py", None),
        ("Emotion Brain", "test_emotion_brain.py", None),
        ("Brain Test 2", "test_brain2.py", None),
    ],
    "brain": [
        ("Brain Tests", "test_brain.py", None),
        ("Brain V2", "test_brain_v2.py", None),
        ("Emotion Brain", "test_emotion_brain.py", None),
        ("Brain Test 2", "test_brain2.py", None),
    ],
    "api": [
        ("API Endpoints", "test_api_endpoints.py", None),
        ("Pipeline Integration", "test_full_integration.py", None),
    ],
    "emotion": [
        ("Emotion Brain", "test_emotion_brain.py", None),
    ],
    "pipeline": [
        ("Pipeline Integration", "test_full_integration.py", None),
        ("Pipeline Full", "test_pipeline_full.py", None),
    ],
}


def print_banner():
    """Print the test runner banner."""
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{CYAN}{BOLD}  DreamTalk Test Runner{RESET}")
    print(f"{CYAN}{'='*60}{RESET}")
    print(f"  Project: {PROJECT_ROOT.name}")
    print(f"  Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{CYAN}{'-'*60}{RESET}\n")


def discover_test_files() -> List[Tuple[str, str]]:
    """Discover all test_*.py files in the project root."""
    test_files = sorted(PROJECT_ROOT.glob("test_*.py"))
    result = []
    for f in test_files:
        # Read first line for a description
        desc = f.stem.replace("test_", "").replace("_", " ").title()
        result.append((desc, f.name))
    return result


def run_test_file(name: str, filename: str, timeout: int = 120) -> Tuple[bool, float, str]:
    """Run a single test file and return (passed, duration, output)."""
    print(f"  {YELLOW}▶{RESET} Running {BOLD}{name}{RESET} ({filename})...", end=" ", flush=True)

    filepath = PROJECT_ROOT / filename
    if not filepath.exists():
        print(f"{RED}⚠ SKIPPED (file not found){RESET}")
        return (False, 0, "File not found")

    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(filepath)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
        )
        duration = time.time() - start
        passed = result.returncode == 0

        if passed:
            print(f"{GREEN}✓ PASSED{RESET} ({duration:.1f}s)")
        else:
            print(f"{RED}✗ FAILED{RESET} ({duration:.1f}s)")

        return (passed, duration, result.stdout + result.stderr)
    except subprocess.TimeoutExpired:
        duration = time.time() - start
        print(f"{RED}✗ TIMEOUT{RESET} ({duration:.1f}s)")
        return (False, duration, f"Timed out after {timeout}s")
    except Exception as e:
        duration = time.time() - start
        print(f"{RED}✗ ERROR{RESET} ({duration:.1f}s)")
        return (False, duration, str(e))


def print_summary(results: List[Tuple[str, bool, float]]):
    """Print a summary of all test results."""
    passed = sum(1 for _, p, _ in results if p)
    failed = sum(1 for _, p, _ in results if not p)
    total = len(results)
    total_time = sum(d for _, _, d in results)

    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}  Test Summary{RESET}")
    print(f"{CYAN}{'-'*60}{RESET}")
    print(f"  Total:  {total}")
    print(f"  Passed: {GREEN}{passed}{RESET}")
    print(f"  Failed: {RED}{failed}{RESET}")
    if total > 0:
        print(f"  Rate:   {GREEN if passed == total else RED}{(passed/total)*100:.0f}%{RESET}")
    print(f"  Time:   {total_time:.1f}s")
    print(f"{CYAN}{'='*60}{RESET}\n")

    if failed > 0:
        print(f"{YELLOW}Failed tests:{RESET}")
        for name, passed, duration in results:
            if not passed:
                print(f"  {RED}• {name}{RESET}")


def main():
    parser = argparse.ArgumentParser(description="DreamTalk Test Runner")
    parser.add_argument(
        "--category",
        "-c",
        choices=list(TEST_CATEGORIES.keys()),
        default="all",
        help="Test category to run",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List discovered test files without running",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=120,
        help="Timeout per test file in seconds (default: 120)",
    )
    args = parser.parse_args()

    if args.list:
        print(f"\n{CYAN}Discovered test files:{RESET}")
        for desc, filename in discover_test_files():
            print(f"  • {BOLD}{filename}{RESET} — {desc}")
        print()
        return

    print_banner()

    tests = TEST_CATEGORIES[args.category]
    results: List[Tuple[str, bool, float]] = []
    failed_outputs: List[Tuple[str, str]] = []

    for name, filename, _ in tests:
        passed, duration, output = run_test_file(name, filename, args.timeout)
        results.append((name, passed, duration))
        if not passed:
            failed_outputs.append((name, output.strip()[:2000]))  # Truncate long output

    print_summary(results)

    # Show failed outputs
    if failed_outputs:
        print(f"\n{YELLOW}{'='*60}{RESET}")
        print(f"{YELLOW}{BOLD}  Failure Details{RESET}")
        print(f"{YELLOW}{'='*60}{RESET}\n")
        for name, output in failed_outputs:
            if output:
                print(f"{BOLD}{name}:{RESET}")
                # Show last 30 lines of output
                lines = output.split("\n")
                last_lines = lines[-30:] if len(lines) > 30 else lines
                for line in last_lines:
                    print(f"  {line}")
                print()

    # Return exit code
    all_passed = all(p for _, p, _ in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
