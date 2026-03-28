#!/usr/bin/env python3
"""Check harness-workflow status with content validation and stage gating.

Reports workflow stage progress, validates artifact content (not just
existence), and enforces stage transitions via --gate flag.

Usage:
    python run.py check_status.py
    python run.py check_status.py --gate spec
    python run.py check_status.py --json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from harness_shared import (
    detect_openspec_cli,
    load_harness_config,
    load_state,
    run_command,
)

# Required sections per artifact (header text -> minimum content chars)
ARTIFACT_VALIDATION = {
    "intent.md": {
        "required_sections": ["Problem", "Success Criteria"],
        "min_content_chars": 50,
    },
    "proposal.md": {
        "required_sections": ["Goals", "Constraints"],
        "min_content_chars": 50,
    },
    "design.md": {
        "required_sections": ["Architecture", "Components"],
        "min_content_chars": 100,
    },
    "tasks.md": {
        "required_sections": ["Phase"],
        "requires_task_items": True,
        "min_content_chars": 50,
    },
}

STAGE_ORDER = ["intent", "spec", "plan", "harness", "execute"]


def _get_openspec_dir(project_dir: Path) -> Path:
    """Get OpenSpec directory from config or default."""
    config = load_harness_config(project_dir)
    if config:
        custom_dir = (config.get("openspec") or {}).get("directory")
        if custom_dir:
            return project_dir / custom_dir
    return project_dir / "openspec"


def find_change_dirs(project_dir: Path) -> List[Path]:
    """Find all change directories under openspec/changes/."""
    changes_dir = _get_openspec_dir(project_dir) / "changes"
    if not changes_dir.is_dir():
        return []
    return sorted(
        d for d in changes_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
    )


def validate_artifact_content(
    file_path: Path,
    required_sections: List[str],
    min_content_chars: int = 50,
    requires_task_items: bool = False,
) -> Tuple[bool, List[str]]:
    """Validate that an artifact has required sections with substantive content.

    Returns (is_valid, list_of_issues)
    """
    if not file_path.exists():
        return False, [f"File not found: {file_path.name}"]

    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as e:
        return False, [f"Cannot read {file_path.name}: {e}"]

    if not content.strip():
        return False, [f"{file_path.name} is empty"]

    issues = []

    for section in required_sections:
        pattern = rf"^##\s+.*{re.escape(section)}"
        if not re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
            issues.append(f"Missing required section: '{section}'")
            continue

        section_pattern = rf"^##\s+.*{re.escape(section)}.*\n(.*?)(?=\n##\s|\Z)"
        match = re.search(
            section_pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        if match:
            section_content = match.group(1).strip()
            if len(section_content) < min_content_chars:
                issues.append(
                    f"Section '{section}' has insufficient content "
                    f"({len(section_content)} chars, need {min_content_chars})"
                )

    if requires_task_items:
        if not re.search(r"-\s+\[[ x]\]", content):
            issues.append("No task items found (expected - [ ] or - [x] format)")

    return len(issues) == 0, issues


def check_intent_stage(project_dir: Path) -> Dict[str, Any]:
    """Check intent stage: validate intent.md content."""
    intent_path = project_dir / "intent.md"
    config = ARTIFACT_VALIDATION["intent.md"]
    valid, issues = validate_artifact_content(
        intent_path,
        config["required_sections"],
        config["min_content_chars"],
    )
    return {
        "stage": "intent",
        "complete": valid,
        "artifacts": {
            "intent.md": {
                "exists": intent_path.exists(),
                "valid": valid,
                "issues": issues,
            }
        },
    }


def check_spec_stage(project_dir: Path) -> Dict[str, Any]:
    """Check spec stage: validate OpenSpec artifacts."""
    change_dirs = find_change_dirs(project_dir)

    if not change_dirs:
        changes_dir = _get_openspec_dir(project_dir) / "changes"
        artifacts = {
            "proposal.md": changes_dir / "proposal.md",
            "design.md": changes_dir / "design.md",
            "tasks.md": changes_dir / "tasks.md",
        }
    else:
        change_dir = change_dirs[0]
        artifacts = {
            "proposal.md": change_dir / "proposal.md",
            "design.md": change_dir / "design.md",
            "tasks.md": change_dir / "tasks.md",
        }

    all_valid = True
    artifact_results = {}

    for name, path in artifacts.items():
        config = ARTIFACT_VALIDATION.get(name, {})
        valid, issues = validate_artifact_content(
            path,
            config.get("required_sections", []),
            config.get("min_content_chars", 50),
            config.get("requires_task_items", False),
        )
        artifact_results[name] = {
            "exists": path.exists(),
            "valid": valid,
            "issues": issues,
            "path": str(path),
        }
        if not valid:
            all_valid = False

    return {
        "stage": "spec",
        "complete": all_valid,
        "artifacts": artifact_results,
    }


def check_stage_gate(project_dir: Path, stage: str) -> Tuple[bool, List[str]]:
    """Check if a stage gate can be passed.

    Returns (can_advance, blockers)
    """
    if stage == "intent":
        result = check_intent_stage(project_dir)
        blockers = []
        for info in result["artifacts"].values():
            if not info["valid"]:
                blockers.extend(info.get("issues", ["Artifact not valid"]))
        return result["complete"], blockers

    elif stage == "spec":
        result = check_spec_stage(project_dir)
        blockers = []
        for name, info in result["artifacts"].items():
            if not info.get("exists", False):
                blockers.append(f"{name} not found")
            elif not info.get("valid", False):
                blockers.extend(info.get("issues", [f"{name} not valid"]))
        return result["complete"], blockers

    elif stage in ("plan", "harness", "execute"):
        state = load_state(project_dir)
        if not state:
            return False, [".harness/state.json not found"]
        stage_status = state.get("stages", {}).get(stage, "pending")
        if stage_status == "complete":
            return True, []
        return False, [f"Stage '{stage}' is {stage_status}"]

    return False, [f"Unknown stage: {stage}"]


def format_text_report(
    project_dir: Path, state: Optional[Dict[str, Any]]
) -> str:
    """Format human-readable status report."""
    lines = []
    lines.append("=" * 60)
    lines.append("Harness Workflow Status")
    lines.append("=" * 60)
    lines.append(f"Project: {project_dir}")

    if state:
        language = state.get("language", "unknown")
        framework = state.get("framework")
        current = state.get("current_stage", "unknown")
        lines.append(f"Language: {language}")
        if framework:
            lines.append(f"Framework: {framework}")
        lines.append(f"Current stage: {current}")

    lines.append("")
    lines.append("Stages:")

    for stage in STAGE_ORDER:
        if stage in ("intent", "spec"):
            check = (
                check_intent_stage(project_dir)
                if stage == "intent"
                else check_spec_stage(project_dir)
            )
            status = "COMPLETE" if check["complete"] else "INCOMPLETE"
            lines.append(f"  {stage}: {status}")
            for name, info in check["artifacts"].items():
                icon = "+" if info.get("valid") else "-"
                exists = "exists" if info.get("exists") else "missing"
                lines.append(f"    [{icon}] {name}: {exists}")
                for issue in info.get("issues", []):
                    lines.append(f"        {issue}")
        elif state:
            stage_status = state.get("stages", {}).get(stage, "pending")
            lines.append(f"  {stage}: {stage_status.upper()}")

    return "\n".join(lines)


def get_next_action(
    project_dir: Path, state: Optional[Dict[str, Any]]
) -> str:
    """Recommend the next action based on current status."""
    if not state:
        return "Run: python scripts/run.py init_harness.py . --feature <name>"

    for stage in STAGE_ORDER:
        stage_status = state.get("stages", {}).get(stage, "pending")
        if stage_status != "complete":
            actions = {
                "intent": "Edit intent.md with your project goals and success criteria",
                "spec": "Create OpenSpec documents (proposal, design, tasks)",
                "plan": "Break down tasks and assign agents",
                "harness": "Configure agent pool and quality gates",
                "execute": "Run: python scripts/run.py build_verify.py --loop tight",
            }
            return actions.get(stage, f"Complete {stage} stage")

    return "All stages complete! Run verification: python scripts/run.py verify_specs.py"


def main():
    parser = argparse.ArgumentParser(
        description="Check harness-workflow status with content validation",
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Project directory (default: current)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--gate",
        choices=STAGE_ORDER,
        help="Check if a specific stage gate can be passed (exit 0/1)",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()

    # Gate check mode
    if args.gate:
        can_advance, blockers = check_stage_gate(project_dir, args.gate)
        if can_advance:
            print(f"Stage gate '{args.gate}': PASSED")
            sys.exit(0)
        else:
            print(f"Stage gate '{args.gate}': BLOCKED")
            for blocker in blockers:
                print(f"  - {blocker}")
            sys.exit(1)

    # OpenSpec CLI delegation
    if detect_openspec_cli():
        result = run_command("openspec status --json", project_dir, timeout=10)
        if result["success"]:
            print("OpenSpec CLI status:")
            try:
                cli_status = json.loads(result["stdout"])
                print(json.dumps(cli_status, indent=2))
            except json.JSONDecodeError:
                print(result["stdout"])
            print()

    # Standard status check
    state = load_state(project_dir)

    if args.json:
        report = {
            "project_dir": str(project_dir),
            "state": state,
            "intent": check_intent_stage(project_dir),
            "spec": check_spec_stage(project_dir),
            "next_action": get_next_action(project_dir, state),
        }
        print(json.dumps(report, indent=2))
    else:
        print(format_text_report(project_dir, state))
        print()
        print(f"Next: {get_next_action(project_dir, state)}")


if __name__ == "__main__":
    main()
