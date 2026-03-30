#!/usr/bin/env python3
"""Doom loop detection for harness-workflow.

Tracks error patterns across build-verify iterations. When the same error
hash appears 3+ consecutive times, a doom loop is detected and human
intervention is recommended.

Exit codes:
    0: Normal (status check / reset)
    Usage via import: check_doom_loop() returns bool
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from harness_shared import run_command

MAX_HISTORY = 20
DOOM_THRESHOLD = 3
FILE_EDIT_THRESHOLD = 5
ERROR_HISTORY_FILE = "error-history.json"

NUDGE_MESSAGES = [
    "Consider taking a completely different approach to this problem.",
    "The repeated edits suggest the current strategy isn't working. Try a simpler solution.",
    "You may be stuck in a local optimum. Step back and reconsider the architecture.",
    "Try reverting the last change and approaching from a different angle.",
]


def _history_path(project_dir: Path) -> Path:
    return project_dir / ".harness" / ERROR_HISTORY_FILE


def load_error_history(project_dir: Path) -> Dict[str, Any]:
    """Load .harness/error-history.json."""
    path = _history_path(project_dir)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"runs": [], "hashes": []}


def save_error_history(project_dir: Path, history: Dict[str, Any]) -> None:
    """Save error history, keeping last MAX_HISTORY entries."""
    path = _history_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    if len(history.get("runs", [])) > MAX_HISTORY:
        history["runs"] = history["runs"][-MAX_HISTORY:]
    if len(history.get("hashes", [])) > MAX_HISTORY:
        history["hashes"] = history["hashes"][-MAX_HISTORY:]
    path.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")


def compute_error_hash(errors: List[str]) -> str:
    """Hash sorted error output to detect repetition."""
    if not errors:
        return ""
    content = "\n".join(sorted(errors))
    return hashlib.md5(content.encode()).hexdigest()[:12]


def extract_errors(results: Dict[str, Any]) -> List[str]:
    """Extract error lines from build results dict."""
    errors = []
    for check_name, result in results.items():
        if isinstance(result, dict) and not result.get("success", True):
            stderr = result.get("stderr", "").strip()
            stdout = result.get("stdout", "").strip()
            if stderr:
                errors.extend(stderr.splitlines())
            elif stdout:
                for line in stdout.splitlines():
                    lower = line.lower()
                    if any(m in lower for m in ("error", "fail", "warning")):
                        errors.append(f"[{check_name}] {line}")
    return errors


def check_doom_loop(history: Dict[str, Any], current_results: Dict[str, Any]) -> bool:
    """Returns True if same error hash appears DOOM_THRESHOLD+ consecutive times."""
    current_hash = compute_error_hash(extract_errors(current_results))
    hashes = history.get("hashes", [])
    hashes.append(current_hash)
    hashes = hashes[-10:]
    history["hashes"] = hashes

    if len(hashes) >= DOOM_THRESHOLD:
        last_n = hashes[-DOOM_THRESHOLD:]
        if len(set(last_n)) == 1 and last_n[0] != "":
            return True
    return False


def record_errors(
    history: Dict[str, Any], results: Dict[str, Any], iteration: int
) -> None:
    """Record a run's errors into history."""
    errors = extract_errors(results)
    history.setdefault("runs", []).append(
        {
            "iteration": iteration,
            "hash": compute_error_hash(errors),
            "error_count": len(errors),
            "errors": errors[:50],
        }
    )


def reset_history(project_dir: Path) -> None:
    """Clear error history."""
    path = _history_path(project_dir)
    if path.exists():
        path.unlink()
        print(f"Error history cleared for {project_dir}")
    else:
        print(f"No error history found for {project_dir}")


# -- Per-File Edit Tracking --


def get_changed_files(project_dir: Path) -> List[str]:
    """Get list of files changed since last commit via git diff."""
    result = run_command(
        "git diff --name-only HEAD", project_dir, timeout=10
    )
    if result["success"] and result["stdout"].strip():
        return [
            f.strip()
            for f in result["stdout"].strip().splitlines()
            if f.strip()
        ]
    return []


def record_file_edits(
    history: Dict[str, Any],
    changed_files: List[str],
    iteration: int,
) -> None:
    """Record which files were edited in this iteration.

    Tracks per-file edit count across iterations to detect doom loops
    where the agent keeps editing the same file without making progress.
    """
    file_edits = history.setdefault("file_edits", {})
    file_edits.setdefault("_iterations", [])

    for f in changed_files:
        if f not in file_edits:
            file_edits[f] = []
        file_edits[f].append(iteration)

    file_edits["_iterations"].append(iteration)

    # Keep only last MAX_HISTORY iterations of tracking
    all_iters = file_edits["_iterations"]
    if len(all_iters) > MAX_HISTORY:
        cutoff = all_iters[-MAX_HISTORY]
        for key in list(file_edits.keys()):
            if key == "_iterations":
                continue
            file_edits[key] = [i for i in file_edits[key] if i >= cutoff]
        file_edits["_iterations"] = all_iters[-MAX_HISTORY:]


def check_file_doom_loop(
    history: Dict[str, Any],
    threshold: int = FILE_EDIT_THRESHOLD,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Check if any single file has been edited too many times.

    Returns (is_doom_loop, list of flagged files with edit counts and nudges).
    """
    file_edits = history.get("file_edits", {})
    flagged = []

    for f, iterations in file_edits.items():
        if f.startswith("_"):
            continue
        if len(iterations) >= threshold:
            nudge_idx = len(iterations) % len(NUDGE_MESSAGES)
            flagged.append({
                "file": f,
                "edit_count": len(iterations),
                "iterations": iterations[-5:],
                "nudge": NUDGE_MESSAGES[nudge_idx],
            })

    return len(flagged) > 0, flagged


def print_status(project_dir: Path) -> None:
    """Print current doom loop status (error-hash + file-edit tracking)."""
    history = load_error_history(project_dir)
    hashes = history.get("hashes", [])
    runs = history.get("runs", [])

    print(f"Doom Loop Status: {project_dir}")
    print(f"  Total runs tracked: {len(runs)}")
    print(f"  Recent error hashes: {hashes[-5:]}")

    if len(hashes) >= DOOM_THRESHOLD:
        last_n = hashes[-DOOM_THRESHOLD:]
        if len(set(last_n)) == 1 and last_n[0] != "":
            print(f"  WARNING: Error-hash doom loop! Same error {DOOM_THRESHOLD}x in a row")
        else:
            print("  No error-hash doom loop detected")
    else:
        print(f"  Insufficient data ({len(hashes)}/{DOOM_THRESHOLD} runs)")

    # File edit tracking
    is_file_doom, flagged = check_file_doom_loop(history)
    if flagged:
        print(f"  File edit doom loop: {len(flagged)} file(s) edited {FILE_EDIT_THRESHOLD}+ times")
        for item in flagged:
            print(f"    - {item['file']}: {item['edit_count']} edits")
            print(f"      Nudge: {item['nudge']}")
    else:
        file_edits = history.get("file_edits", {})
        tracked_files = len([k for k in file_edits if not k.startswith("_")])
        print(f"  File edit tracking: {tracked_files} files tracked, no doom loop")

    if runs:
        last_run = runs[-1]
        print(
            f"  Last run: iteration {last_run.get('iteration')}, "
            f"{last_run.get('error_count')} errors"
        )


def main():
    parser = argparse.ArgumentParser(description="Doom loop detection")
    parser.add_argument("--project-dir", default=".", help="Project directory")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--reset", action="store_true", help="Clear error history")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()

    if args.status:
        print_status(project_dir)
    elif args.reset:
        reset_history(project_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
