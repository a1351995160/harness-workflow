#!/usr/bin/env python3
"""Single-pass build runner for harness-workflow.

Runs lint, typecheck, and/or test commands detected for the project.
Used by build_verify.py internally, or standalone for quick checks.

Usage:
    python run.py run_build.py --check lint
    python run.py run_build.py --check all --json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from harness_shared import (
    detect_language,
    detect_build_commands,
    run_command,
    format_result,
    load_harness_config,
    get_build_commands_from_config,
)


def run_single_check(
    commands: Dict[str, str],
    check_type: str,
    project_dir: Path,
) -> Optional[Dict[str, Any]]:
    """Run a single check type if the command exists."""
    cmd = commands.get(check_type)
    if not cmd:
        return None

    print(f"  Running {check_type}: {cmd}")
    result = run_command(cmd, project_dir)

    status = "PASS" if result["success"] else "FAIL"
    suffix = "" if result["success"] else f" (exit code {result['returncode']})"
    print(f"    {status}{suffix}")

    if not result["success"] and result.get("stderr"):
        stderr_lines = result["stderr"].strip().splitlines()
        for line in stderr_lines[:5]:
            print(f"      {line}")
        if len(stderr_lines) > 5:
            print(f"      ... ({len(stderr_lines) - 5} more lines)")

    return result


def detect_and_run(
    project_dir: Path,
    check_type: str = "all",
) -> Dict[str, Any]:
    """Detect build commands and run selected checks.

    Args:
        project_dir: Project root directory
        check_type: 'lint', 'typecheck', 'test', or 'all'

    Returns:
        Dict mapping check names to their results
    """
    language = detect_language(project_dir)
    if not language:
        print("Warning: Could not detect project language")
        return {}

    print(f"Detected language: {language}")
    commands = detect_build_commands(project_dir, language)

    # Override with config commands if available
    config = load_harness_config(project_dir)
    config_commands = get_build_commands_from_config(config, language)
    if config_commands:
        print(f"  Config overrides: {list(config_commands.keys())}")
        commands.update(config_commands)

    if check_type == "all":
        results = {}
        for check in ("lint", "typecheck", "test"):
            result = run_single_check(commands, check, project_dir)
            if result is not None:
                results[check] = result
        return results
    else:
        result = run_single_check(commands, check_type, project_dir)
        return {check_type: result} if result else {}


def main():
    parser = argparse.ArgumentParser(description="Run build checks")
    parser.add_argument(
        "--check",
        choices=["lint", "typecheck", "test", "all"],
        default="all",
        help="Which check to run (default: all)",
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Project directory (default: current)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()

    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}")
        sys.exit(1)

    print(f"Build Check: {args.check}")
    print(f"Project: {project_dir}")
    print()

    results = detect_and_run(project_dir, args.check)

    if not results:
        print("No checks available for this project")
        sys.exit(0)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print()
        print("Summary:")
        all_passed = True
        for name, result in results.items():
            status = "PASS" if result["success"] else "FAIL"
            if not result["success"]:
                all_passed = False
            print(f"  {name}: {status}")

        if all_passed:
            print("\nAll checks passed")
            sys.exit(0)
        else:
            print("\nSome checks failed")
            sys.exit(1)


if __name__ == "__main__":
    main()
