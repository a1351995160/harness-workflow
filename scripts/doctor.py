#!/usr/bin/env python3
"""Environment health check for harness-workflow.

Validates that all required and optional tools are available,
checks state file integrity, and produces a color-coded report.

Usage:
    python run.py doctor.py
    python run.py doctor.py --json
"""

import argparse
import json
import platform
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from harness_shared import detect_language, detect_openspec_cli, load_state


# ANSI color codes (disabled on Windows if no VT support)
_COLORS = {
    "OK": "\033[92m",      # green
    "WARN": "\033[93m",    # yellow
    "FAIL": "\033[91m",    # red
    "BOLD": "\033[1m",
    "RESET": "\033[0m",
}


def _supports_color() -> bool:
    """Check if terminal supports ANSI colors."""
    if platform.system() == "Windows":
        return sys.stdout.isatty()
    return True


def _colorize(status: str, text: str) -> str:
    """Wrap text in ANSI color codes based on status."""
    if not _supports_color():
        return text
    color = _COLORS.get(status, "")
    return f"{color}{text}{_COLORS['RESET']}"


def check_python_version() -> Dict[str, Any]:
    """Check Python version is 3.8+."""
    major, minor = sys.version_info[:2]
    ok = (major, minor) >= (3, 8)
    return {
        "name": "Python 3.8+",
        "status": "OK" if ok else "FAIL",
        "detail": f"{major}.{minor}.{sys.version_info.micro}",
    }


def check_git() -> Dict[str, Any]:
    """Check git is available."""
    path = shutil.which("git")
    return {
        "name": "Git",
        "status": "OK" if path else "FAIL",
        "detail": path or "not found",
    }


def check_openspec() -> Dict[str, Any]:
    """Check OpenSpec CLI availability."""
    available = detect_openspec_cli()
    return {
        "name": "OpenSpec CLI",
        "status": "OK" if available else "WARN",
        "detail": "installed" if available else "not installed (npm install -g @fission-ai/openspec)",
    }


def check_tool(name: str, required: bool = False) -> Dict[str, Any]:
    """Check if a CLI tool is on PATH."""
    path = shutil.which(name)
    status = "OK" if path else ("FAIL" if required else "WARN")
    return {
        "name": name,
        "status": status,
        "detail": path or "not found",
    }


def check_state_integrity(project_dir: Path) -> Dict[str, Any]:
    """Validate .harness/state.json structure."""
    state_path = project_dir / ".harness" / "state.json"
    if not state_path.exists():
        return {
            "name": ".harness/state.json",
            "status": "WARN",
            "detail": "not found (run /harness-workflow:init)",
        }

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {
            "name": ".harness/state.json",
            "status": "FAIL",
            "detail": f"corrupt: {e}",
        }

    required_keys = {"current_stage", "project_name"}
    missing = required_keys - set(state.keys())
    if missing:
        return {
            "name": ".harness/state.json",
            "status": "WARN",
            "detail": f"missing keys: {', '.join(sorted(missing))}",
        }

    return {
        "name": ".harness/state.json",
        "status": "OK",
        "detail": f"stage={state.get('current_stage', '?')}",
    }


def check_harness_dir(project_dir: Path) -> Dict[str, Any]:
    """Check .harness/ directory exists."""
    harness_dir = project_dir / ".harness"
    exists = harness_dir.is_dir()
    return {
        "name": ".harness/ directory",
        "status": "OK" if exists else "WARN",
        "detail": "exists" if exists else "not found (run /harness-workflow:init)",
    }


def check_mcp_config(project_dir: Path) -> Dict[str, Any]:
    """Check if optional MCP server reference config exists."""
    mcp_ref = Path(__file__).parent.parent / "config" / "mcp-servers.json"
    if mcp_ref.exists():
        try:
            servers = json.loads(mcp_ref.read_text(encoding="utf-8"))
            server_names = [k for k in servers if not k.startswith("_")]
            return {
                "name": "MCP server config",
                "status": "OK",
                "detail": f"reference config available ({len(server_names)} servers: {', '.join(server_names)})",
            }
        except (json.JSONDecodeError, OSError):
            return {
                "name": "MCP server config",
                "status": "WARN",
                "detail": "config/mcp-servers.json exists but is invalid JSON",
            }
    return {
        "name": "MCP server config",
        "status": "WARN",
        "detail": "no reference config found (optional)",
    }


def run_doctor(project_dir: Path) -> List[Dict[str, Any]]:
    """Run all diagnostic checks and return results."""
    results: List[Dict[str, Any]] = []

    # Core tools
    results.append(check_python_version())
    results.append(check_git())
    results.append(check_openspec())

    # Formatters & linters (optional)
    for tool in ("prettier", "black", "ruff", "eslint", "mypy"):
        results.append(check_tool(tool))

    # AST tools
    results.append(check_tool("ast-grep"))

    # Git hooks
    results.append(check_tool("lefthook"))

    # Project state
    results.append(check_harness_dir(project_dir))
    results.append(check_state_integrity(project_dir))

    # MCP server config reference
    results.append(check_mcp_config(project_dir))

    return results


def print_report(results: List[Dict[str, Any]], project_dir: Path) -> None:
    """Print color-coded doctor report."""
    print(_colorize("BOLD", f"harness-workflow doctor — {project_dir}"))
    print()

    ok_count = sum(1 for r in results if r["status"] == "OK")
    warn_count = sum(1 for r in results if r["status"] == "WARN")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")

    for r in results:
        status_str = _colorize(r["status"], f"  [{r['status']:4s}]")
        print(f"{status_str}  {r['name']}: {r['detail']}")

    print()
    summary = f"  {ok_count} OK, {warn_count} WARN, {fail_count} FAIL"
    print(_colorize("BOLD", summary))

    if fail_count > 0:
        print()
        print("  Fix FAIL items before proceeding.")
    elif warn_count > 0:
        print()
        print("  WARN items are optional but recommended.")


def main() -> None:
    parser = argparse.ArgumentParser(description="harness-workflow environment health check")
    parser.add_argument("--project-dir", default=".", help="Project directory (default: current)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    results = run_doctor(project_dir)

    if args.json:
        output = {
            "project_dir": str(project_dir),
            "checks": results,
            "summary": {
                "ok": sum(1 for r in results if r["status"] == "OK"),
                "warn": sum(1 for r in results if r["status"] == "WARN"),
                "fail": sum(1 for r in results if r["status"] == "FAIL"),
            },
        }
        print(json.dumps(output, indent=2))
    else:
        print_report(results, project_dir)

    # Exit 1 if any FAIL
    has_fail = any(r["status"] == "FAIL" for r in results)
    sys.exit(1 if has_fail else 0)


if __name__ == "__main__":
    main()
