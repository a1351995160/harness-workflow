#!/usr/bin/env python3
"""Build-Verify Loop - the core engine of harness-workflow.

Runs lint -> typecheck -> test in an iterative loop. Detects doom loops
(when the same error repeats 3+ times) and exits with appropriate codes.

Usage:
    python run.py build_verify.py --loop tight
    python run.py build_verify.py --loop loose --max-iterations 5 --json

Exit codes:
    0: All checks passed
    1: Checks failed (agent should fix and re-run)
    2: Doom loop detected (human intervention needed)
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from harness_shared import (
    detect_language,
    detect_build_commands,
    load_state,
    save_state,
    run_command,
    load_harness_config,
    get_build_commands_from_config,
)

import doom_loop
import token_tracker

DEFAULT_MAX_ITERATIONS = 3


def run_build_loop(
    commands: Dict[str, str],
    project_dir: Path,
    loop_type: str = "tight",
) -> Dict[str, Any]:
    """Execute build pipeline: lint -> typecheck -> test.

    Args:
        commands: Dict of check names to command strings
        project_dir: Project root directory
        loop_type: 'tight' (lint + typecheck + unit) or 'loose' (+ e2e)

    Returns:
        Dict mapping check names to results
    """
    results: Dict[str, Any] = {}

    # Step 1: Lint
    if "lint" in commands:
        print(f"  [1/4] Lint: {commands['lint']}")
        results["lint"] = run_command(commands["lint"], project_dir)
        _print_check_result("lint", results["lint"])

    # Step 2: Typecheck (skip if lint failed in tight mode)
    if "typecheck" in commands:
        lint_ok = results.get("lint", {}).get("success", True)
        if loop_type == "loose" or lint_ok:
            print(f"  [2/4] Typecheck: {commands['typecheck']}")
            results["typecheck"] = run_command(commands["typecheck"], project_dir)
            _print_check_result("typecheck", results["typecheck"])
        else:
            print("  [2/4] Typecheck: SKIPPED (lint failed)")

    # Step 3: Tests
    test_cmd = commands.get("test_unit" if loop_type == "tight" else "test")
    if not test_cmd:
        test_cmd = commands.get("test")
    if test_cmd:
        label = "Unit tests" if loop_type == "tight" else "Tests"
        print(f"  [3/4] {label}: {test_cmd}")
        results["test"] = run_command(test_cmd, project_dir)
        _print_check_result("test", results["test"])

    # Step 4: E2E (loose loop only)
    if loop_type == "loose" and "test_e2e" in commands:
        print(f"  [4/4] E2E: {commands['test_e2e']}")
        results["e2e"] = run_command(commands["test_e2e"], project_dir)
        _print_check_result("e2e", results["e2e"])
    elif loop_type == "loose":
        print("  [4/4] E2E: SKIPPED (no e2e command configured)")

    return results


def _print_check_result(name: str, result: Dict[str, Any]) -> None:
    """Print a single check result."""
    if result["success"]:
        print("    PASS")
    else:
        print(f"    FAIL (exit code {result['returncode']})")
        stderr = result.get("stderr", "").strip()
        stdout = result.get("stdout", "").strip()
        output = stderr or stdout
        if output:
            lines = output.splitlines()
            for line in lines[:5]:
                print(f"      {line}")
            if len(lines) > 5:
                print(f"      ... ({len(lines) - 5} more lines)")


def print_error_report(results: Dict[str, Any]) -> None:
    """Print detailed error report for failed checks."""
    for name, result in results.items():
        if not result.get("success", True):
            print(f"\n  === {name.upper()} ERRORS ===")
            stderr = result.get("stderr", "").strip()
            stdout = result.get("stdout", "").strip()
            output = stderr or stdout
            if output:
                for line in output.splitlines()[:20]:
                    print(f"    {line}")


def output_json(results: Dict[str, Any], iteration: int, status: str) -> None:
    """Output structured JSON result."""
    output = {
        "status": status,
        "iteration": iteration,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {},
    }
    for name, result in results.items():
        output["checks"][name] = {
            "success": result.get("success", False),
            "returncode": result.get("returncode", -1),
        }
    print(json.dumps(output, indent=2))


def update_state_stage(project_dir: Path, stage: str, status: str) -> None:
    """Update a stage status in .harness/state.json."""
    state = load_state(project_dir)
    if state and "stages" in state:
        state["stages"][stage] = status
        save_state(project_dir, state)


def main():
    parser = argparse.ArgumentParser(
        description="Build-Verify Loop: run lint -> typecheck -> test iteratively",
    )
    parser.add_argument(
        "--loop",
        choices=["tight", "loose"],
        default="tight",
        help="Loop type: tight (lint+typecheck+unit) or loose (+e2e)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=DEFAULT_MAX_ITERATIONS,
        help=f"Maximum iterations (default: {DEFAULT_MAX_ITERATIONS})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Project directory (default: current)",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()

    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}")
        sys.exit(1)

    language = detect_language(project_dir)
    if not language:
        print("Error: Could not detect project language")
        sys.exit(1)

    commands = detect_build_commands(project_dir, language)

    # Override with config commands if available
    config = load_harness_config(project_dir)
    config_commands = get_build_commands_from_config(config, language)
    if config_commands:
        print(f"  Config overrides: {list(config_commands.keys())}")
        commands.update(config_commands)

    print(f"Build-Verify Loop ({args.loop})")
    print(f"Project: {project_dir}")
    print(f"Language: {language}")
    print(f"Max iterations: {args.max_iterations}")
    print()

    error_history = doom_loop.load_error_history(project_dir)

    for iteration in range(1, args.max_iterations + 1):
        print(f"--- Iteration {iteration}/{args.max_iterations} ---")

        results = run_build_loop(commands, project_dir, args.loop)

        # Doom loop check (error hash)
        if doom_loop.check_doom_loop(error_history, results):
            print()
            print("DOOM LOOP DETECTED: same errors repeating")
            print("   Recommend human intervention or alternative approach")
            doom_loop.record_errors(error_history, results, iteration)
            doom_loop.save_error_history(project_dir, error_history)
            update_state_stage(project_dir, "execute", "blocked")
            if args.json:
                output_json(results, iteration, "doom_loop")
            sys.exit(2)

        doom_loop.record_errors(error_history, results, iteration)

        # Token gradient tracking (rough estimate based on output size)
        output_size = sum(
            len(r.get("stdout", "") + r.get("stderr", ""))
            for r in results.values()
        )
        token_estimate = max(output_size // 4, 500)  # ~4 chars per token
        token_tracker.record_iteration(project_dir, iteration, token_estimate)

        # Token gradient doom loop check
        if token_tracker.check_token_gradient(error_history):
            print()
            print("TOKEN GRADIENT DOOM LOOP: token consumption increasing without progress")
            doom_loop.save_error_history(project_dir, error_history)
            update_state_stage(project_dir, "execute", "blocked")
            if args.json:
                output_json(results, iteration, "doom_loop")
            sys.exit(2)

        # Execution loop check
        if token_tracker.check_execution_loop(error_history):
            print()
            print("EXECUTION LOOP: same error pattern across all recent iterations")
            doom_loop.save_error_history(project_dir, error_history)
            update_state_stage(project_dir, "execute", "blocked")
            if args.json:
                output_json(results, iteration, "doom_loop")
            sys.exit(2)

        # File edit doom loop check
        changed_files = doom_loop.get_changed_files(project_dir)
        doom_loop.record_file_edits(error_history, changed_files, iteration)
        is_file_doom, flagged_files = doom_loop.check_file_doom_loop(error_history)
        if is_file_doom:
            print()
            print("FILE DOOM LOOP DETECTED: same files edited too many times")
            for item in flagged_files:
                print(f"  - {item['file']}: {item['edit_count']} edits")
                print(f"    Nudge: {item['nudge']}")
            doom_loop.save_error_history(project_dir, error_history)
            update_state_stage(project_dir, "execute", "blocked")
            if args.json:
                output_json(results, iteration, "doom_loop")
            sys.exit(2)

        all_passed = all(r.get("success", True) for r in results.values())

        if all_passed:
            print()
            print(f"Build-verify loop PASSED (iteration {iteration})")
            update_state_stage(project_dir, "execute", "complete")
            doom_loop.save_error_history(project_dir, error_history)
            if args.json:
                output_json(results, iteration, "passed")
            sys.exit(0)

        print()
        print(f"Build-verify FAILED (iteration {iteration}/{args.max_iterations})")
        print_error_report(results)
        print()

        if args.json:
            output_json(results, iteration, "failed")

    # Max iterations reached
    doom_loop.save_error_history(project_dir, error_history)
    print(f"Max iterations ({args.max_iterations}) reached without passing")
    update_state_stage(project_dir, "execute", "blocked")
    sys.exit(1)


if __name__ == "__main__":
    main()
