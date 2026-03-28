#!/usr/bin/env python3
"""Verify implementation against OpenSpec specs.

Validates spec structure, content depth, file references, cross-references,
and delta spec compliance. Delegates to OpenSpec CLI when available.

Usage:
    python run.py verify_specs.py
    python run.py verify_specs.py --strict --report
    python run.py verify_specs.py --json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from harness_shared import (
    detect_openspec_cli,
    run_command,
)

# Required/recommended sections by spec type
SPEC_SECTIONS = {
    "proposal": {
        "required": ["Problem", "Goals", "Success Criteria"],
        "recommended": ["Stakeholders", "Constraints", "Risks"],
    },
    "design": {
        "required": ["Architecture", "Components"],
        "recommended": ["Data Model", "API", "Security", "Performance"],
    },
    "tasks": {
        "required": ["Task Summary", "Phase"],
        "recommended": ["Dependency Graph", "Risk Register"],
    },
}

# File reference patterns
FILE_REF_PATTERNS = [
    r"`([^`]+\.(?:ts|tsx|js|jsx|py|go|java|rs|rb|php))`",
    r"(?:src|lib|pkg|cmd|internal)/[\w/\-]+\.\w+",
    r'(?:import|from)\s+[\'"]([^\'"]+)[\'"]',
]

SOURCE_EXTENSIONS = {".ts", ".tsx", ".py", ".go", ".java", ".rs", ".rb", ".php"}


def find_spec_files(project_dir: Path) -> Dict[str, List[Path]]:
    """Find all spec files recursively under openspec/."""
    specs: Dict[str, List[Path]] = {
        "proposal": [],
        "design": [],
        "tasks": [],
        "delta": [],
        "other": [],
    }

    search_dirs = [
        project_dir / "openspec" / "specs",
        project_dir / "openspec" / "changes",
    ]

    for base_dir in search_dirs:
        if not base_dir.is_dir():
            continue
        for md_file in base_dir.rglob("*.md"):
            name = md_file.stem.lower()
            if name == "proposal":
                specs["proposal"].append(md_file)
            elif name == "design":
                specs["design"].append(md_file)
            elif name == "tasks":
                specs["tasks"].append(md_file)
            elif "delta" in name or "spec" in name:
                specs["delta"].append(md_file)
            else:
                specs["other"].append(md_file)

    return specs


def validate_spec_structure(
    spec_path: Path,
    spec_type: str,
    strict: bool = False,
) -> Dict[str, Any]:
    """Validate spec file has required and recommended sections with depth."""
    if not spec_path.exists():
        return {"valid": False, "status": "FAIL", "issues": [f"File not found: {spec_path}"], "warnings": []}

    try:
        content = spec_path.read_text(encoding="utf-8")
    except OSError as e:
        return {"valid": False, "status": "FAIL", "issues": [f"Cannot read file: {e}"], "warnings": []}

    config = SPEC_SECTIONS.get(spec_type, {})
    required = config.get("required", [])
    recommended = config.get("recommended", [])

    issues = []
    warnings = []

    for section in required:
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
            min_chars = 100 if spec_type == "design" else 50
            if len(section_content) < min_chars:
                issues.append(
                    f"Section '{section}' has insufficient content "
                    f"({len(section_content)} chars, need {min_chars})"
                )

    for section in recommended:
        pattern = rf"^##\s+.*{re.escape(section)}"
        if not re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
            warnings.append(f"Missing recommended section: '{section}'")

    if spec_type == "tasks":
        if not re.search(r"-\s+\[[ x]\]", content):
            issues.append("No task items found (expected - [ ] or - [x] format)")

    if spec_type == "design" and not issues:
        ref_pattern = r"`[\w/\-\.]+\.\w+`"
        file_refs = re.findall(ref_pattern, content)
        if len(file_refs) < 2:
            warnings.append(
                "Design should reference at least 2 source files or components"
            )

    status = "PASS" if not issues else ("FAIL" if strict else "PARTIAL")

    return {
        "valid": len(issues) == 0,
        "status": status,
        "file": str(spec_path),
        "issues": issues,
        "warnings": warnings,
    }


def validate_file_references(
    spec_path: Path, project_dir: Path
) -> Dict[str, Any]:
    """Check that file references in specs exist on disk."""
    try:
        content = spec_path.read_text(encoding="utf-8")
    except OSError:
        return {"valid": True, "total": 0, "missing": []}

    references = []
    missing = []

    for pattern in FILE_REF_PATTERNS:
        for match in re.finditer(pattern, content):
            ref = match.group(1) if match.lastindex else match.group(0)
            ref = ref.strip().strip("'\"")
            if not ref or (ref.startswith(".") and len(ref) < 3):
                continue

            resolved = project_dir / ref
            if not resolved.exists():
                for prefix in ("src", "lib", "pkg"):
                    alt = project_dir / prefix / ref
                    if alt.exists():
                        ref = str(alt.relative_to(project_dir))
                        resolved = alt
                        break

            exists = resolved.exists()
            references.append({"path": ref, "exists": exists})
            if not exists:
                missing.append(ref)

    return {
        "valid": len(missing) == 0,
        "total": len(references),
        "missing": missing,
    }


def validate_delta_specs(spec_path: Path) -> Dict[str, Any]:
    """Validate delta spec compliance (ADDED/MODIFIED/REMOVED sections)."""
    try:
        content = spec_path.read_text(encoding="utf-8")
    except OSError:
        return {"valid": True, "delta_sections": [], "issues": []}

    delta_types = ["ADDED", "MODIFIED", "REMOVED"]
    deltas = []
    issues = []

    for dtype in delta_types:
        pattern = rf"^##\s+{dtype}"
        matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))
        for match in matches:
            start = match.end()
            end_match = re.search(r"\n##\s", content[start:])
            end = start + end_match.start() if end_match else len(content)
            section_content = content[start:end].strip()

            deltas.append({"type": dtype, "has_content": bool(section_content)})

            if dtype == "MODIFIED" and section_content:
                if not re.search(r"\(Previously:", section_content):
                    issues.append(
                        "MODIFIED section missing '(Previously: ...)' notation"
                    )

            if dtype == "REMOVED" and section_content:
                if len(section_content) < 20:
                    issues.append(
                        "REMOVED section should include a reason for removal"
                    )

    return {
        "valid": len(issues) == 0,
        "delta_sections": deltas,
        "issues": issues,
    }


def cross_reference_design(
    spec_path: Path, project_dir: Path
) -> Dict[str, Any]:
    """Check that design components have corresponding source files."""
    try:
        content = spec_path.read_text(encoding="utf-8")
    except OSError:
        return {"valid": True, "components": [], "total": 0, "found": 0}

    components = re.findall(r"###\s+(?:Component|component)[:\s]+(.+)", content)

    results = []
    found = 0

    for comp_name in components:
        comp_clean = comp_name.strip().lower().replace(" ", "-")
        matches = []
        for ext in SOURCE_EXTENSIONS:
            for f in project_dir.rglob(f"*{comp_clean}{ext}"):
                if ".git" not in str(f) and "node_modules" not in str(f):
                    matches.append(str(f.relative_to(project_dir)))

        if matches:
            found += 1
        results.append(
            {"name": comp_name.strip(), "files": matches, "found": len(matches) > 0}
        )

    return {
        "valid": found > 0 or len(components) == 0,
        "components": results,
        "total": len(components),
        "found": found,
    }


def generate_report(
    project_dir: Path,
    strict: bool = False,
    write_report: bool = False,
) -> Dict[str, Any]:
    """Run full verification and generate report."""
    # Try OpenSpec CLI first
    cli_result = None
    if detect_openspec_cli():
        print("OpenSpec CLI detected, running validation...")
        result = run_command(
            "openspec validate --all --json", project_dir, timeout=30
        )
        if result["success"]:
            try:
                cli_result = json.loads(result["stdout"])
                print("  OpenSpec CLI validation passed")
            except json.JSONDecodeError:
                print("  OpenSpec CLI output not parseable, falling back")
        else:
            print(f"  OpenSpec CLI failed: {result['stderr'].strip()}")
            print("  Falling back to manual validation")

    # Manual validation
    spec_files = find_spec_files(project_dir)

    report: Dict[str, Any] = {
        "project_dir": str(project_dir),
        "cli_validated": cli_result is not None,
        "specs": {},
        "summary": {"pass": 0, "partial": 0, "fail": 0, "total": 0},
    }

    for spec_type in ("proposal", "design", "tasks"):
        for spec_path in spec_files.get(spec_type, []):
            validation = validate_spec_structure(spec_path, spec_type, strict)
            refs = validate_file_references(spec_path, project_dir)
            xref = (
                cross_reference_design(spec_path, project_dir)
                if spec_type == "design"
                else {"valid": True, "components": []}
            )

            combined = {
                "structure": validation,
                "references": refs,
                "cross_reference": xref,
                "status": validation["status"],
            }

            key = f"{spec_type}:{spec_path.relative_to(project_dir)}"
            report["specs"][key] = combined
            status_key = validation["status"].lower()
            if status_key in report["summary"]:
                report["summary"][status_key] += 1
            report["summary"]["total"] += 1

    # Validate delta specs
    for delta_path in spec_files.get("delta", []):
        delta_validation = validate_delta_specs(delta_path)
        key = f"delta:{delta_path.relative_to(project_dir)}"
        report["specs"][key] = {"delta": delta_validation}
        status = "pass" if delta_validation["valid"] else "fail"
        report["summary"][status] += 1
        report["summary"]["total"] += 1

    # Write report files
    if write_report:
        harness_dir = project_dir / ".harness"
        harness_dir.mkdir(exist_ok=True)

        (harness_dir / "verification-report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )

        lines = ["# Verification Report", ""]
        for key, spec_report in report["specs"].items():
            lines.append(f"## {key}")
            struct = spec_report.get("structure", {})
            if struct:
                lines.append(f"  Status: {struct.get('status', 'N/A')}")
                for issue in struct.get("issues", []):
                    lines.append(f"  - {issue}")
                for warning in struct.get("warnings", []):
                    lines.append(f"  - {warning}")
            lines.append("")

        lines.append("## Summary")
        for k, v in report["summary"].items():
            lines.append(f"  {k.capitalize()}: {v}")

        (harness_dir / "verification-report.md").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
        print("Report written to .harness/verification-report.md")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Verify implementation against OpenSpec specs",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat any issue as FAIL (default: PARTIAL)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Write report to .harness/verification-report.md",
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
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()

    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}")
        sys.exit(1)

    print(f"Verifying specs in: {project_dir}")
    print()

    report = generate_report(
        project_dir, strict=args.strict, write_report=args.report
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for key, spec_report in report["specs"].items():
            struct = spec_report.get("structure", {})
            delta = spec_report.get("delta", {})
            if struct:
                status = struct.get("status", "N/A")
                print(f"  [{status}] {key}")
                for issue in struct.get("issues", []):
                    print(f"    ! {issue}")
                for warning in struct.get("warnings", []):
                    print(f"    ~ {warning}")
            elif delta:
                status = "PASS" if delta.get("valid") else "FAIL"
                print(f"  [{status}] {key}")
                for issue in delta.get("issues", []):
                    print(f"    ! {issue}")

        print()
        s = report["summary"]
        print(
            f"Summary: {s['pass']} pass, {s['partial']} partial, {s['fail']} fail"
        )

    if report["summary"]["fail"] > 0:
        sys.exit(1)
    if args.strict and report["summary"]["partial"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
