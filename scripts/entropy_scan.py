#!/usr/bin/env python3
"""Entropy scanner for harness-workflow.

Detects AI-generated code quality issues: dead code, style drift,
stale documentation, and TODO/FIXME decay.

Usage:
    python run.py entropy_scan.py
    python run.py entropy_scan.py --json
    python run.py entropy_scan.py --fix

Exit codes:
    0: Low entropy (<= 20 issues)
    1: High entropy (> 20 issues)
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from harness_shared import (
    detect_language,
    load_harness_config,
    run_command,
)

HIGH_ENTROPY_THRESHOLD = 20

TODO_PATTERN = re.compile(
    r"^\s*(?://|#|<!--)\s*(TODO|FIXME|HACK|XXX)\b",
    re.IGNORECASE,
)


def _should_skip(path: Path) -> bool:
    """Check if a path should be skipped during scanning."""
    parts = str(path)
    return any(
        skip in parts
        for skip in (".git", "node_modules", "dist", "__pycache__", ".omc", "venv")
    )


def scan_dead_code(project_dir: Path, language: str) -> Dict[str, Any]:
    """Find unused exports, imports, and variables."""
    issues: List[str] = []

    if language in ("typescript", "javascript"):
        # Try knip first (most comprehensive)
        result = run_command("npx knip --no-progress", project_dir, timeout=60)
        if result["success"] and result["stdout"]:
            for line in result["stdout"].splitlines():
                stripped = line.strip()
                if stripped and ("unused" in stripped.lower() or "export" in stripped.lower()):
                    issues.append(stripped)
        else:
            # Fallback: ts-prune
            result = run_command("npx ts-prune", project_dir, timeout=60)
            if result["stdout"]:
                for line in result["stdout"].splitlines():
                    stripped = line.strip()
                    if stripped:
                        issues.append(stripped)

    elif language == "python":
        result = run_command("ruff check --select F401,F811 .", project_dir, timeout=60)
        if result["stdout"]:
            for line in result["stdout"].splitlines():
                stripped = line.strip()
                if stripped:
                    issues.append(stripped)

    elif language == "csharp":
        # Detect outdated NuGet packages
        result = run_command(
            "dotnet list package --outdated", project_dir, timeout=60
        )
        if result["stdout"]:
            for line in result["stdout"].splitlines():
                stripped = line.strip()
                if stripped and (">" in stripped or "outdated" in stripped.lower()):
                    issues.append(stripped)

    if not issues:
        # Generic: find exported symbols not imported elsewhere
        if language in ("typescript", "javascript"):
            export_pattern = re.compile(
                r"export\s+(?:const|function|class|interface|type)\s+(\w+)"
            )
            import_pattern = re.compile(r"import\s+.*?{([^}]+)}")

            exports: Dict[str, str] = {}
            imports = set()

            for f in project_dir.rglob("*.ts"):
                if _should_skip(f):
                    continue
                try:
                    content = f.read_text(encoding="utf-8")
                    for m in export_pattern.finditer(content):
                        exports[m.group(1)] = str(f.relative_to(project_dir))
                    for m in import_pattern.finditer(content):
                        for name in m.group(1).split(","):
                            imports.add(name.strip().split(" as ")[0].strip())
                except OSError:
                    pass

            for name, path in exports.items():
                if name not in imports:
                    issues.append(f"Unused export: {name} in {path}")

    return {
        "category": "dead_code",
        "count": len(issues),
        "issues": issues[:20],
    }


def scan_style_drift(project_dir: Path, language: str) -> Dict[str, Any]:
    """Check for inconsistent coding patterns."""
    issues: List[str] = []

    extensions = {
        "typescript": [".ts", ".tsx"],
        "javascript": [".js", ".jsx"],
        "python": [".py"],
        "go": [".go"],
        "java": [".java"],
        "csharp": [".cs"],
    }.get(language, [])

    if not extensions:
        return {"category": "style_drift", "count": 0, "issues": []}

    for ext in extensions:
        for f in project_dir.rglob(f"*{ext}"):
            if _should_skip(f):
                continue
            try:
                content = f.read_text(encoding="utf-8")
            except OSError:
                continue

            rel_path = str(f.relative_to(project_dir))

            # Mixed quote styles
            single_quotes = len(re.findall(r"(?<!\\)'[^']*'", content))
            double_quotes = len(re.findall(r'(?<!\\)"[^"]*"', content))
            if single_quotes > 0 and double_quotes > 0:
                ratio = min(single_quotes, double_quotes) / max(
                    single_quotes, double_quotes
                )
                if ratio > 0.3:
                    issues.append(
                        f"Mixed quotes in {rel_path} "
                        f"(single: {single_quotes}, double: {double_quotes})"
                    )

            # Mixed naming conventions
            if language in ("typescript", "javascript"):
                snake_vars = re.findall(r"\b[a-z]+_[a-z_]+\b", content)
                camel_vars = re.findall(r"\b[a-z]+[A-Z][a-zA-Z]*\b", content)
                if len(snake_vars) > 3 and len(camel_vars) > 3:
                    issues.append(
                        f"Mixed naming in {rel_path} "
                        f"(snake_case: {len(snake_vars)}, camelCase: {len(camel_vars)})"
                    )

    return {
        "category": "style_drift",
        "count": len(issues),
        "issues": issues[:20],
    }


def scan_stale_docs(project_dir: Path) -> Dict[str, Any]:
    """Find docs referencing non-existent files or code."""
    issues: List[str] = []

    for md_file in project_dir.rglob("*.md"):
        if _should_skip(md_file):
            continue
        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError:
            continue

        rel_path = str(md_file.relative_to(project_dir))

        # File path references
        path_refs = re.findall(
            r"(?:src|lib|pkg|cmd|internal|test|tests|scripts)/[\w/\-\.]+\.\w+",
            content,
        )
        for ref in set(path_refs):
            clean_ref = ref.rstrip(")")
            if not (project_dir / clean_ref).exists():
                issues.append(
                    f"Stale reference in {rel_path}: {clean_ref} does not exist"
                )

        # Class/function references in backticks
        code_refs = re.findall(
            r"`([A-Z][a-zA-Z]+(?:Manager|Handler|Service|Factory|Builder|Controller|Provider))`",
            content,
        )
        for ref in set(code_refs):
            found = False
            for ext in (".ts", ".tsx", ".py", ".go", ".java", ".cs"):
                for f in project_dir.rglob(f"*{ext}"):
                    if _should_skip(f):
                        continue
                    try:
                        if ref in f.read_text(encoding="utf-8"):
                            found = True
                            break
                    except OSError:
                        pass
                    if found:
                        break
                if found:
                    break
            if not found:
                issues.append(
                    f"Stale reference in {rel_path}: `{ref}` not found in source"
                )

    return {
        "category": "stale_docs",
        "count": len(issues),
        "issues": issues[:20],
    }


def scan_todos(project_dir: Path) -> Dict[str, Any]:
    """Find TODO/FIXME/HACK comments, flag those older than 30 days."""
    todos: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for f in project_dir.rglob("*"):
        if _should_skip(f) or f.is_dir():
            continue
        if f.suffix not in (
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".py",
            ".go",
            ".java",
            ".cs",
            ".rs",
            ".rb",
            ".md",
        ):
            continue

        try:
            content = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        rel_path = str(f.relative_to(project_dir))

        for i, line in enumerate(content.splitlines(), 1):
            if TODO_PATTERN.match(line):
                tag_match = re.search(r"(TODO|FIXME|HACK|XXX)", line, re.IGNORECASE)
                tag = tag_match.group(1).upper() if tag_match else "TODO"
                todos.append(
                    {
                        "file": rel_path,
                        "line": i,
                        "tag": tag,
                        "text": line.strip(),
                    }
                )

    # Check age via git
    aged = []
    for todo in todos:
        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "-1",
                    "--format=%aI",
                    "-L",
                    f"{todo['line']},{todo['line']}:{todo['file']}",
                ],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                commit_date = datetime.fromisoformat(result.stdout.strip())
                days_old = (now - commit_date).days
                todo["days_old"] = days_old
                if days_old > 30:
                    aged.append(todo)
        except (subprocess.TimeoutExpired, ValueError, OSError):
            pass

    return {
        "category": "todo_decay",
        "count": len(todos),
        "aged_count": len(aged),
        "issues": [
            f"[{t['tag']}] {t['file']}:{t['line']} {t['text'][:60]}"
            for t in aged[:10]
        ],
        "tags": {
            "TODO": sum(1 for t in todos if t["tag"] == "TODO"),
            "FIXME": sum(1 for t in todos if t["tag"] == "FIXME"),
            "HACK": sum(1 for t in todos if t["tag"] == "HACK"),
            "XXX": sum(1 for t in todos if t["tag"] == "XXX"),
        },
    }


def auto_fix(project_dir: Path, language: str) -> int:
    """Auto-fix safely fixable issues. Returns count of fixes applied."""
    fixes = 0

    if language == "python":
        result = run_command("ruff check --select F401 --fix .", project_dir)
        if result["success"]:
            stdout = result.get("stdout", "")
            if "Removed" in stdout or "Fixed" in stdout:
                fixes += 1

    return fixes


def main():
    parser = argparse.ArgumentParser(
        description="Scan for entropy: dead code, style drift, stale docs, TODO decay",
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
        "--fix",
        action="store_true",
        help="Auto-fix safely fixable issues",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()

    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}")
        sys.exit(1)

    language = detect_language(project_dir) or "unknown"

    print(f"Entropy Scan: {project_dir}")
    print(f"Language: {language}")
    print()

    # Load config overrides
    config = load_harness_config(project_dir)
    entropy_config = (config or {}).get("entropy_management", {})

    # Config-driven threshold
    threshold = HIGH_ENTROPY_THRESHOLD
    if isinstance(entropy_config.get("threshold"), int):
        threshold = entropy_config["threshold"]

    # Config-driven scanner selection
    scan_targets = entropy_config.get("scan_targets", [])
    target_to_scanner = {
        "dead_code": "dead_code",
        "unused_imports": "dead_code",
        "style_inconsistencies": "style_drift",
        "outdated_documentation": "stale_docs",
    }
    enabled_scanners = None
    if scan_targets:
        enabled_scanners = set()
        for target in scan_targets:
            scanner = target_to_scanner.get(target)
            if scanner:
                enabled_scanners.add(scanner)

    if config:
        print(f"  Config: threshold={threshold}, scanners={enabled_scanners or 'all'}")
        print()

    # Run scanners
    all_scanners = {
        "dead_code": lambda: scan_dead_code(project_dir, language),
        "style_drift": lambda: scan_style_drift(project_dir, language),
        "stale_docs": lambda: scan_stale_docs(project_dir),
        "todo_decay": lambda: scan_todos(project_dir),
    }

    results = {}
    for name, func in all_scanners.items():
        if enabled_scanners is None or name in enabled_scanners:
            results[name] = func()

    total_issues = sum(r["count"] for r in results.values())

    # Auto-fix if requested
    if args.fix:
        fixes = auto_fix(project_dir, language)
        if fixes > 0:
            print(f"Applied {fixes} auto-fixes")
            print()

    # Output
    if args.json:
        output = {
            "project_dir": str(project_dir),
            "language": language,
            "total_issues": total_issues,
            "entropy_level": (
                "HIGH" if total_issues > threshold else "LOW"
            ),
            "scanners": results,
        }
        print(json.dumps(output, indent=2))
    else:
        print("Entropy Report:")
        for name, result in results.items():
            count = result["count"]
            line = f"  {name}: {count} issue{'s' if count != 1 else ''} found"
            if name == "todo_decay" and "tags" in result:
                tags = result["tags"]
                tag_str = ", ".join(
                    f"{k}: {v}" for k, v in tags.items() if v > 0
                )
                if tag_str:
                    line += f" ({tag_str})"
            print(line)
            for issue in result.get("issues", [])[:5]:
                print(f"    - {issue}")

        level = "HIGH" if total_issues > threshold else "LOW"
        print(f"  OVERALL: {level} entropy ({total_issues} issues)")

    sys.exit(1 if total_issues > threshold else 0)


if __name__ == "__main__":
    main()
