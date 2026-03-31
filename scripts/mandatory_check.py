#!/usr/bin/env python3
"""Mandatory security checks — deterministic, no AI dependency.

Scans source files for known vulnerability patterns using regex.
Exit codes:
    0: All checks passed (or no files to scan)
    1: Violations found

Usage:
    python run.py mandatory_check.py --files src/app.ts src/utils.py
    python run.py mandatory_check.py --directory src/
    python run.py mandatory_check.py --staged
    python run.py mandatory_check.py --json
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))


@dataclass
class Violation:
    """A single mandatory check violation."""

    file: str
    line: int
    rule: str
    severity: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MandatoryChecker:
    """Deterministic security pattern scanner — no AI dependency."""

    # SQL injection patterns
    SQL_INJECTION: List[Tuple[str, str]] = [
        (r'(?:query|execute)\s*\(\s*[`"\'].*\$\{', "SQL injection: string interpolation in query"),
        (r'(?:query|execute)\s*\(\s*[`"\'].*\+', "SQL injection: string concatenation in query"),
        (r'cursor\.execute\s*\(\s*[fF]?["\'].*%', "SQL injection: format string in query"),
        (r'\.execute\s*\(\s*[^,]+\+', "SQL injection: concatenation in query"),
        (r'String\s+\w+\s*=\s*".*(?:SELECT|INSERT|UPDATE|DELETE).*"\s*\+', "SQL injection: string building"),
    ]

    # Hardcoded secret patterns
    HARDCODED_SECRETS: List[Tuple[str, str]] = [
        (r'(?:api[_-]?key|apikey)\s*=\s*["\'][^"\']{16,}["\']', "Hardcoded API key"),
        (r'(?:password|passwd|pwd)\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
        (r'(?:secret|token|auth)\s*=\s*["\'][^"\']{20,}["\']', "Hardcoded secret/token"),
        (r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----", "Hardcoded private key"),
        (r'aws_access_key_id\s*=\s*["\']AKIA', "Hardcoded AWS key"),
    ]

    # Dangerous function patterns by extension
    DANGEROUS_FUNCTIONS: Dict[str, List[Tuple[str, str]]] = {
        ".ts": [
            (r"\beval\s*\(", "Dangerous: eval() allows code injection"),
            (r"\bFunction\s*\(", "Dangerous: Function() allows code injection"),
            (r'setTimeout\s*\(\s*["\']', "Dangerous: setTimeout with string argument"),
        ],
        ".tsx": [
            (r"\beval\s*\(", "Dangerous: eval() allows code injection"),
            (r"dangerouslySetInnerHTML", "Dangerous: React dangerouslySetInnerHTML"),
        ],
        ".js": [
            (r"\beval\s*\(", "Dangerous: eval() allows code injection"),
            (r"\bFunction\s*\(", "Dangerous: Function() allows code injection"),
        ],
        ".jsx": [
            (r"\beval\s*\(", "Dangerous: eval() allows code injection"),
            (r"dangerouslySetInnerHTML", "Dangerous: React dangerouslySetInnerHTML"),
        ],
        ".py": [
            (r"\beval\s*\(", "Dangerous: eval() allows code injection"),
            (r"\bexec\s*\(", "Dangerous: exec() allows code injection"),
            (r"__import__\s*\(", "Dangerous: dynamic import"),
        ],
        ".java": [
            (r"Runtime\.getRuntime\(\)\.exec\s*\(", "Dangerous: Runtime.exec()"),
        ],
    }

    # XSS patterns
    XSS_PATTERNS: List[Tuple[str, str]] = [
        (r'innerHTML\s*=\s*[^$]', "XSS: direct innerHTML assignment"),
        (r"document\.write\s*\(", "XSS: document.write usage"),
    ]

    # Extensions to scan
    SCAN_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".py", ".java"}

    # Directories to skip
    SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next"}

    def __init__(self) -> None:
        self.violations: List[Violation] = []

    def check_file(self, file_path: Path) -> List[Violation]:
        """Scan a single file for all violation patterns."""
        violations: List[Violation] = []

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")
        except (OSError, UnicodeDecodeError):
            return violations

        ext = file_path.suffix.lower()

        for line_num, line in enumerate(lines, 1):
            # SQL injection
            for pattern, message in self.SQL_INJECTION:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(Violation(
                        file=str(file_path), line=line_num,
                        rule="SQL_INJECTION", severity="CRITICAL", message=message,
                    ))

            # Hardcoded secrets
            for pattern, message in self.HARDCODED_SECRETS:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(Violation(
                        file=str(file_path), line=line_num,
                        rule="HARDCODED_SECRET", severity="CRITICAL", message=message,
                    ))

            # Dangerous functions (extension-specific)
            if ext in self.DANGEROUS_FUNCTIONS:
                for pattern, message in self.DANGEROUS_FUNCTIONS[ext]:
                    if re.search(pattern, line):
                        violations.append(Violation(
                            file=str(file_path), line=line_num,
                            rule="DANGEROUS_FUNCTION", severity="CRITICAL", message=message,
                        ))

            # XSS (JS/TS only)
            if ext in (".ts", ".tsx", ".js", ".jsx"):
                for pattern, message in self.XSS_PATTERNS:
                    if re.search(pattern, line):
                        violations.append(Violation(
                            file=str(file_path), line=line_num,
                            rule="XSS", severity="HIGH", message=message,
                        ))

        return violations

    def check_directory(self, directory: Path) -> List[Violation]:
        """Scan an entire directory tree."""
        all_violations: List[Violation] = []
        for ext in self.SCAN_EXTENSIONS:
            for file_path in directory.rglob(f"*{ext}"):
                if any(part in self.SKIP_DIRS for part in file_path.parts):
                    continue
                all_violations.extend(self.check_file(file_path))
        return all_violations

    def check_staged(self, project_dir: Path) -> List[Violation]:
        """Scan only git-staged files."""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=10,
            )
            if not result.returncode == 0 or not result.stdout.strip():
                return []
            staged_files = [
                project_dir / f.strip()
                for f in result.stdout.strip().splitlines()
                if f.strip()
            ]
        except (subprocess.TimeoutExpired, OSError):
            return []

        violations: List[Violation] = []
        for file_path in staged_files:
            if file_path.suffix.lower() in self.SCAN_EXTENSIONS and file_path.exists():
                violations.extend(self.check_file(file_path))
        return violations


def _print_report(violations: List[Violation]) -> None:
    """Print human-readable violation report."""
    if not violations:
        print("All mandatory checks passed")
        return

    print()
    print("=" * 60)
    print("MANDATORY CHECK FAILED")
    print("=" * 60)
    print()

    for v in violations:
        print(f"  [{v.severity}] {v.rule}")
        print(f"    File: {v.file}:{v.line}")
        print(f"    Issue: {v.message}")
        print()

    print("=" * 60)
    print(f"Total violations: {len(violations)}")
    print("These issues MUST be fixed before merge.")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Mandatory security checks")
    parser.add_argument("--files", nargs="+", help="Specific files to check")
    parser.add_argument("--directory", default=None, help="Directory to scan")
    parser.add_argument("--staged", action="store_true", help="Check git-staged files only")
    parser.add_argument("--project-dir", default=".", help="Project root (default: current)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    checker = MandatoryChecker()
    violations: List[Violation] = []

    if args.files:
        for file_str in args.files:
            file_path = Path(file_str)
            if not file_path.is_absolute():
                file_path = project_dir / file_path
            if file_path.exists():
                violations.extend(checker.check_file(file_path))
    elif args.staged:
        violations = checker.check_staged(project_dir)
    elif args.directory:
        scan_dir = Path(args.directory)
        if not scan_dir.is_absolute():
            scan_dir = project_dir / scan_dir
        if scan_dir.exists():
            violations = checker.check_directory(scan_dir)
    else:
        # Default: scan project directory
        if project_dir.exists():
            violations = checker.check_directory(project_dir)

    if args.json:
        output = {
            "status": "fail" if violations else "pass",
            "violation_count": len(violations),
            "violations": [v.to_dict() for v in violations],
        }
        print(json.dumps(output, indent=2))
    else:
        _print_report(violations)

    sys.exit(1 if violations else 0)


if __name__ == "__main__":
    main()
