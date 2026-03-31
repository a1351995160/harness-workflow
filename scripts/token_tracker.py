#!/usr/bin/env python3
"""Token consumption gradient tracking for doom loop detection.

Records token usage per iteration into .harness/error-history.json and
detects monotonically increasing token usage with no error-hash change
(spinning indicator).

Usage:
    from token_tracker import record_iteration, check_token_gradient

    record_iteration(project_dir, iteration=1, token_estimate=5000)
    is_spinning = check_token_gradient(history, threshold=0.1)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def record_iteration(
    project_dir: Path,
    iteration: int,
    token_estimate: int,
) -> None:
    """Record token consumption for one build-verify iteration.

    Appends to the ``token_gradient`` key in error-history.json.
    """
    history_path = project_dir / ".harness" / "error-history.json"
    history: Dict[str, Any] = {}
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    gradient = history.setdefault("token_gradient", [])
    gradient.append({
        "iteration": iteration,
        "token_estimate": token_estimate,
    })

    # Keep last 20 entries
    if len(gradient) > 20:
        history["token_gradient"] = gradient[-20:]

    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")


def check_token_gradient(
    history: Dict[str, Any],
    threshold: float = 0.1,
    min_entries: int = 3,
) -> bool:
    """Detect monotonically increasing token usage with same error hash.

    Returns True when:
    - At least *min_entries* gradient records exist
    - Token usage is monotonically increasing
    - The error hash has not changed across those entries

    This indicates the agent is spending more tokens without making progress.
    """
    gradient: List[Dict[str, Any]] = history.get("token_gradient", [])
    if len(gradient) < min_entries:
        return False

    recent = gradient[-min_entries:]
    tokens = [entry["token_estimate"] for entry in recent]

    # Check monotonic increase
    is_increasing = all(tokens[i] < tokens[i + 1] for i in range(len(tokens) - 1))
    if not is_increasing:
        return False

    # Check that error hash stayed the same (no progress)
    hashes = history.get("hashes", [])
    if len(hashes) >= min_entries:
        recent_hashes = hashes[-min_entries:]
        if len(set(recent_hashes)) == 1 and recent_hashes[0] != "":
            return True

    # If no hash data, just check token gradient exceeds threshold
    if len(tokens) >= 2:
        increase_ratio = (tokens[-1] - tokens[0]) / max(tokens[0], 1)
        if increase_ratio > threshold:
            return True

    return False


def check_execution_loop(
    history: Dict[str, Any],
    threshold: int = 5,
) -> bool:
    """Detect repeated tool-call patterns from error history.

    Returns True when the same error hash appears *threshold*+ times
    across the entire run history (not just consecutive).
    """
    runs: List[Dict[str, Any]] = history.get("runs", [])
    if len(runs) < threshold:
        return False

    recent_runs = runs[-threshold:]
    hashes = [run.get("hash", "") for run in recent_runs]
    non_empty = [h for h in hashes if h]

    if len(non_empty) < threshold:
        return False

    # All same hash = execution loop
    return len(set(non_empty)) == 1


def get_gradient_summary(history: Dict[str, Any]) -> Dict[str, Any]:
    """Return a summary of token gradient status."""
    gradient: List[Dict[str, Any]] = history.get("token_gradient", [])
    return {
        "entries": len(gradient),
        "is_spinning": check_token_gradient(history),
        "is_execution_loop": check_execution_loop(history),
        "last_iteration": gradient[-1]["iteration"] if gradient else None,
        "last_token_estimate": gradient[-1]["token_estimate"] if gradient else None,
    }
