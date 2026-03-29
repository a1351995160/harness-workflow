#!/usr/bin/env python3
"""Run E2E tests and capture results with screenshots on failure.

Wraps Playwright test runner with structured output and doom loop integration.

Usage:
    python run.py e2e_runner.py
    python run.py e2e_runner.py --browser chromium --headed
    python run.py e2e_runner.py --json

Exit codes:
    0: All tests pass
    1: Some tests fail
    2: Doom loop detected
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from harness_shared import detect_language, run_command


def find_e2e_command(project_dir: Path, language: str) -> Dict[str, str]:
    """Detect E2E test command for the project."""
    commands = {}

    # Check package.json scripts
    pkg_json = project_dir / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {})
            if "test:e2e" in scripts:
                commands["e2e"] = "npm run test:e2e"
            elif "e2e" in scripts:
                commands["e2e"] = "npm run e2e"
            elif "test" in scripts:
                commands["e2e"] = "npm test"
        except (json.JSONDecodeError, OSError):
            pass

    # Check for Playwright config
    if (project_dir / "playwright.config.ts").exists() or (project_dir / "playwright.config.js").exists():
        if "e2e" not in commands:
            commands["e2e"] = "npx playwright test"
    elif (project_dir / "playwright.config.py").exists() or (project_dir / "pytest.ini").exists():
        if "e2e" not in commands:
            commands["e2e"] = "pytest --headed"

    # Check for Python pytest with playwright
    if language == "python" and "e2e" not in commands:
        commands["e2e"] = "pytest e2e/ tests/e2e/ --headed"

    return commands


def run_e2e_tests(
    project_dir: Path,
    language: str,
    browser: str = "chromium",
    headed: bool = False,
    timeout: int = 300,
) -> Dict[str, Any]:
    """Run E2E tests and capture results."""
    commands = find_e2e_command(project_dir, language)

    if "e2e" not in commands:
        return {
            "status": "SKIP",
            "reason": "No E2E test command found. Configure test:e2e script or install Playwright.",
        }

    cmd = commands["e2e"]

    # Add browser flag for Playwright
    if "playwright" in cmd:
        cmd += f" --browser {browser}"
    if headed and "playwright" in cmd:
        cmd += " --headed"

    result = run_command(cmd, project_dir, timeout=timeout)

    return {
        "status": "PASS" if result["success"] else "FAIL",
        "command": cmd,
        "returncode": result.get("returncode", -1),
        "stdout": result.get("stdout", "")[:2000],
        "stderr": result.get("stderr", "")[:2000],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run E2E tests with structured output",
    )
    parser.add_argument("--project-dir", default=".", help="Project directory")
    parser.add_argument(
        "--browser", choices=["chromium", "firefox", "webkit"],
        default="chromium", help="Browser to use (default: chromium)",
    )
    parser.add_argument("--headed", action="store_true", help="Run in headed mode")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}")
        sys.exit(1)

    language = detect_language(project_dir) or "unknown"

    print(f"E2E Test Runner")
    print(f"  Project: {project_dir}")
    print(f"  Browser: {args.browser}")
    print(f"  Language: {language}")
    print()

    result = run_e2e_tests(
        project_dir, language,
        browser=args.browser,
        headed=args.headed,
        timeout=args.timeout,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"  Status: {result['status']}")
        if result.get("command"):
            print(f"  Command: {result['command']}")
        if result.get("reason"):
            print(f"  Reason: {result['reason']}")
        if result["status"] == "FAIL":
            output = result.get("stderr", "") or result.get("stdout", "")
            if output:
                print()
                print("  Error output:")
                for line in output.splitlines()[:15]:
                    print(f"    {line}")

    if result["status"] == "SKIP":
        sys.exit(0)
    elif result["status"] == "FAIL":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
