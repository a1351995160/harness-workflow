#!/usr/bin/env python3
"""Semantic verification: intent-level spec vs code comparison.

Extracts assertions from spec files (proposal, design, tasks) and checks
source code for evidence. Unlike verify_specs.py which checks structure,
this checks whether the implementation actually fulfills the spec requirements.

Usage:
    python run.py semantic_verify.py
    python run.py semantic_verify.py --strict --report
    python run.py semantic_verify.py --json

Exit codes:
    0: All assertions pass
    1: Some assertions fail
    2: Critical gaps found (missing core features)
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from harness_shared import (
    detect_language,
    load_harness_config,
    run_command,
)

# Assertion extraction patterns
ASSERTION_PATTERNS = {
    "success_criteria": [
        re.compile(r"^[-*]\s*(.+)$", re.MULTILINE),  # bullet points under ## Success Criteria
    ],
    "api_endpoints": [
        re.compile(r"(?:GET|POST|PUT|PATCH|DELETE)\s+(`?(/[^\s`]+)`?)", re.IGNORECASE),
        re.compile(r"(?:endpoint|route|url|path)\s*[:=]\s*`?(/[^\s`]+)`?", re.IGNORECASE),
    ],
    "data_model_fields": [
        re.compile(r"[-*]\s+(\w+)\s*[:=]\s*(?:Column|field|property|attribute)", re.IGNORECASE),
        re.compile(r"`(\w+)`\s*:\s*\w+"),  # TypeScript style: `field`: type
    ],
    "constraints": [
        re.compile(r"(?:must|should|shall|needs? to|required)\s+(.+?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"(?:real-?time|<\s*\d+\s*(?:ms|sec|second|min)|within\s+\d+)", re.IGNORECASE),
        re.compile(r"(?:TTL|retention|expire|cleanup|prune).*?\d+\s*(?:day|hour|minute)", re.IGNORECASE),
    ],
    "channels_enums": [
        re.compile(r"(?:channel|type|mode|status)\s*[:=]?\s*(?:enum\s+)?\[([^\]]+)\]", re.IGNORECASE),
        re.compile(r"(?:email|sms|push|websocket|in[_-]?app|slack)", re.IGNORECASE),
    ],
}

# Evidence detection patterns in source code
EVIDENCE_PATTERNS = {
    "endpoint": [
        re.compile(r"@(?:router|app|bp|route)\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]", re.IGNORECASE),
        re.compile(r"(?:app|router)\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]", re.IGNORECASE),
        re.compile(r"(?:@Get|@Post|@Put|@Patch|@Delete|@RequestMapping)\s*\(\s*['\"]([^'\"]+)['\"]", re.IGNORECASE),
    ],
    "class_definition": [
        re.compile(r"class\s+(\w+)\s*(?:\(|:|{)", re.MULTILINE),
    ],
    "field_definition_python": [
        re.compile(r"(\w+)\s*[:=]\s*(?:Column|Field|field|mapped_column)", re.IGNORECASE),
    ],
    "field_definition_ts": [
        re.compile(r"(\w+)\s*:\s*(?:string|number|boolean|Date|Buffer|Array)<", re.IGNORECASE),
        re.compile(r"(\w+)\??\s*:\s*\w+"),  # TS property
    ],
    "websocket_sse": [
        re.compile(r"(?:WebSocket|SSE|EventSource|socket\.io|WebSocketConsumer|stream)", re.IGNORECASE),
    ],
    "realtime": [
        re.compile(r"(?:real[- ]?time|push|notify|broadcast|publish|subscribe|emit)", re.IGNORECASE),
    ],
    "cleanup_ttl": [
        re.compile(r"(?:TTL|retention|expire|cleanup|prune|purge|archive|gc|delete_old|remove_old|cron.*clean)", re.IGNORECASE),
        re.compile(r"\d+\s*(?:day|hour|minute)\s*(?:retention|expire|ttl|cleanup)", re.IGNORECASE),
    ],
    "auth_security": [
        re.compile(r"(?:auth|jwt|token|session|oauth|password|bcrypt|hash)", re.IGNORECASE),
    ],
    "enum_values": [
        re.compile(r"(?:enum|Enum|UNION_TYPE|const)\s+\w+\s*[{=]\s*([^}]+)", re.IGNORECASE),
        re.compile(r"(?:email|sms|push|in_app|slack|webhook)", re.IGNORECASE),
    ],
    "test_file": [
        re.compile(r"(?:test_|_test\.|\.test\.|\.spec\.)", re.IGNORECASE),
    ],
}

SOURCE_EXTENSIONS = {".ts", ".tsx", ".py", ".go", ".java", ".rs", ".rb", ".js", ".jsx"}


def _should_skip(path: Path) -> bool:
    """Check if a path should be skipped during scanning."""
    parts = str(path)
    return any(
        skip in parts
        for skip in (".git", "node_modules", "dist", "__pycache__", ".omc", "venv", ".harness", "openspec")
    )


# ─────────────────────────────────────────────────────────────
# Assertion Extraction
# ─────────────────────────────────────────────────────────────

def extract_section(content: str, heading: str) -> str:
    """Extract the content of a markdown section by heading."""
    pattern = rf"^##\s+.*{re.escape(heading)}.*\n(.*?)(?=\n##\s|\Z)"
    match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_assertions_from_proposal(content: str) -> List[Dict[str, Any]]:
    """Extract testable assertions from proposal.md."""
    assertions = []

    # Success Criteria
    section = extract_section(content, "Success Criteria")
    if section:
        for line in section.splitlines():
            line = line.strip()
            if line.startswith(("- ", "* ", "1. ", "2. ", "3. ")):
                text = re.sub(r"^[-*\d.]+\s*", "", line).strip()
                if len(text) > 5:
                    assertions.append({
                        "id": f"SC-{len(assertions) + 1}",
                        "source": "proposal:Success Criteria",
                        "text": text,
                        "category": "success_criteria",
                        "priority": "HIGH",
                    })

    # Constraints
    section = extract_section(content, "Constraint")
    if section:
        for line in section.splitlines():
            line = line.strip()
            if line.startswith(("- ", "* ")):
                text = re.sub(r"^[-*]\s*", "", line).strip()
                if len(text) > 5:
                    assertions.append({
                        "id": f"CON-{len(assertions) + 1}",
                        "source": "proposal:Constraints",
                        "text": text,
                        "category": "constraint",
                        "priority": "MEDIUM",
                    })

    return assertions


def extract_assertions_from_design(content: str) -> List[Dict[str, Any]]:
    """Extract testable assertions from design.md."""
    assertions = []

    # API Endpoints
    for pattern in ASSERTION_PATTERNS["api_endpoints"]:
        for match in pattern.finditer(content):
            endpoint = match.group(1).strip().strip("`")
            assertions.append({
                "id": f"API-{len(assertions) + 1}",
                "source": "design:API",
                "text": f"Endpoint {endpoint} must exist",
                "category": "api_endpoint",
                "priority": "HIGH",
                "endpoint": endpoint,
            })

    # Data Model fields
    section = extract_section(content, "Data Model")
    if section:
        fields = set()
        for pattern in ASSERTION_PATTERNS["data_model_fields"]:
            for match in pattern.finditer(section):
                field_name = match.group(1).strip()
                if field_name and field_name not in fields:
                    fields.add(field_name)
                    assertions.append({
                        "id": f"DM-{len(assertions) + 1}",
                        "source": "design:Data Model",
                        "text": f"Field '{field_name}' must exist in data model",
                        "category": "data_field",
                        "priority": "MEDIUM",
                        "field": field_name,
                    })

    # Real-time / WebSocket mentions
    for pattern in ASSERTION_PATTERNS["channels_enums"]:
        for match in pattern.finditer(content):
            text = match.group(0)
            assertions.append({
                "id": f"CH-{len(assertions) + 1}",
                "source": "design",
                "text": f"Channel/type '{text}' must be implemented",
                "category": "channel",
                "priority": "MEDIUM",
            })

    return assertions


def extract_assertions_from_tasks(content: str) -> List[Dict[str, Any]]:
    """Extract task completion assertions from tasks.md."""
    assertions = []
    for match in re.finditer(r"-\s+\[[ x]\]\s+(.+)$", content, re.MULTILINE):
        task_text = match.group(1).strip()
        is_done = match.group(0).strip().startswith("- [x]")
        assertions.append({
            "id": f"TASK-{len(assertions) + 1}",
            "source": "tasks",
            "text": task_text,
            "category": "task",
            "priority": "LOW",
            "completed": is_done,
        })
    return assertions


# ─────────────────────────────────────────────────────────────
# Evidence Gathering
# ─────────────────────────────────────────────────────────────

def gather_evidence(project_dir: Path, language: str) -> Dict[str, Any]:
    """Scan source code for evidence of implementation."""
    evidence: Dict[str, Any] = {
        "endpoints": set(),
        "classes": set(),
        "fields": set(),
        "realtime": set(),
        "cleanup": set(),
        "auth": set(),
        "enums": set(),
        "test_files": set(),
        "source_files": [],
    }

    for f in project_dir.rglob("*"):
        if _should_skip(f) or f.is_dir():
            continue
        if f.suffix not in SOURCE_EXTENSIONS:
            continue

        try:
            content = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        rel_path = str(f.relative_to(project_dir))
        evidence["source_files"].append(rel_path)

        # Detect endpoints
        for pattern in EVIDENCE_PATTERNS["endpoint"]:
            for match in pattern.finditer(content):
                method = match.group(1).upper() if len(match.groups()) > 1 else ""
                path = match.group(2) if len(match.groups()) > 1 else match.group(1)
                evidence["endpoints"].add(f"{method} {path}".strip())

        # Detect classes
        for pattern in EVIDENCE_PATTERNS["class_definition"]:
            for match in pattern.finditer(content):
                evidence["classes"].add(match.group(1))

        # Detect fields
        field_patterns = (
            EVIDENCE_PATTERNS["field_definition_python"]
            if language == "python"
            else EVIDENCE_PATTERNS["field_definition_ts"]
        )
        for pattern in field_patterns:
            for match in pattern.finditer(content):
                evidence["fields"].add(match.group(1))

        # Detect realtime
        for pattern in EVIDENCE_PATTERNS["websocket_sse"]:
            for match in pattern.finditer(content):
                evidence["realtime"].add(f"{rel_path}:{match.group(0)[:30]}")

        # Detect cleanup/TTL
        for pattern in EVIDENCE_PATTERNS["cleanup_ttl"]:
            for match in pattern.finditer(content):
                evidence["cleanup"].add(f"{rel_path}:{match.group(0)[:30]}")

        # Detect auth
        for pattern in EVIDENCE_PATTERNS["auth_security"]:
            for match in pattern.finditer(content):
                evidence["auth"].add(f"{rel_path}:{match.group(0)[:20]}")

        # Detect enums
        for pattern in EVIDENCE_PATTERNS["enum_values"]:
            for match in pattern.finditer(content):
                evidence["enums"].add(match.group(0)[:50])

        # Detect test files
        for pattern in EVIDENCE_PATTERNS["test_file"]:
            if pattern.search(rel_path):
                evidence["test_files"].add(rel_path)

    # Convert sets to sorted lists for JSON output
    return {k: sorted(v) if isinstance(v, set) else v for k, v in evidence.items()}


# ─────────────────────────────────────────────────────────────
# Assertion vs Evidence Matching
# ─────────────────────────────────────────────────────────────

def check_assertion(assertion: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Check a single assertion against gathered evidence."""
    category = assertion["category"]
    text = assertion["text"].lower()
    status = "SKIP"
    evidence_found: List[str] = []
    gap = ""

    if category == "api_endpoint":
        endpoint = assertion.get("endpoint", "").lower()
        for ep in evidence["endpoints"]:
            if endpoint in ep.lower() or ep.lower().startswith(endpoint.split("/")[-1]):
                status = "PASS"
                evidence_found.append(ep)
                break
        if status == "SKIP":
            gap = f"No endpoint matching '{assertion.get('endpoint')}' found"
            status = "FAIL"

    elif category == "data_field":
        field = assertion.get("field", "").lower()
        for f in evidence["fields"]:
            if f.lower() == field:
                status = "PASS"
                evidence_found.append(f)
                break
        if status == "SKIP":
            gap = f"Field '{assertion.get('field')}' not found in data models"
            status = "FAIL"

    elif category == "success_criteria":
        # Check for keywords from the assertion in code evidence
        keywords = _extract_keywords(text)
        matched = []
        for kw in keywords:
            kw_lower = kw.lower()
            for ep in evidence["endpoints"]:
                if kw_lower in ep.lower():
                    matched.append(ep)
            for cls in evidence["classes"]:
                if kw_lower in cls.lower():
                    matched.append(cls)
            for field in evidence["fields"]:
                if kw_lower == field.lower():
                    matched.append(field)
            if any(kw_lower in r.lower() for r in evidence["realtime"]):
                matched.append(f"realtime:{kw}")
            if any(kw_lower in c.lower() for c in evidence["cleanup"]):
                matched.append(f"cleanup:{kw}")
            if any(kw_lower in e.lower() for e in evidence["enums"]):
                matched.append(f"enum:{kw}")

        if len(matched) >= len(keywords) * 0.5:
            status = "PASS" if len(matched) >= len(keywords) else "PARTIAL"
            evidence_found = matched[:5]
        elif matched:
            status = "PARTIAL"
            evidence_found = matched[:5]
            gap = f"Only {len(matched)}/{len(keywords)} keywords matched"
        else:
            status = "FAIL"
            gap = f"No evidence found for: {', '.join(keywords[:5])}"

    elif category == "constraint":
        # Check specific constraint types
        if any(kw in text for kw in ("real-time", "realtime", "real time", "<", "within")):
            if evidence["realtime"]:
                status = "PASS"
                evidence_found = evidence["realtime"][:3]
            else:
                status = "FAIL"
                gap = "No real-time/WebSocket/SSE implementation found"
        elif any(kw in text for kw in ("ttl", "retention", "expire", "cleanup", "day")):
            if evidence["cleanup"]:
                status = "PASS"
                evidence_found = evidence["cleanup"][:3]
            else:
                status = "FAIL"
                gap = "No TTL/retention/cleanup logic found"
        elif any(kw in text for kw in ("auth", "security", "permission", "role")):
            if evidence["auth"]:
                status = "PASS"
                evidence_found = evidence["auth"][:3]
            else:
                status = "FAIL"
                gap = "No authentication/authorization implementation found"
        else:
            # Generic keyword match
            keywords = _extract_keywords(text)
            matched = []
            all_evidence = (
                evidence["endpoints"] + evidence["classes"]
                + evidence["fields"] + evidence["enums"]
            )
            for kw in keywords:
                if any(kw.lower() in e.lower() for e in all_evidence):
                    matched.append(kw)
            if len(matched) >= len(keywords) * 0.5:
                status = "PASS"
                evidence_found = matched[:5]
            else:
                status = "PARTIAL" if matched else "FAIL"
                evidence_found = matched[:5]
                if not matched:
                    gap = f"No matching evidence for constraint"

    elif category == "channel":
        keywords = _extract_keywords(text)
        matched = []
        for kw in keywords:
            if any(kw.lower() in e.lower() for e in evidence["enums"]):
                matched.append(kw)
        if matched:
            status = "PASS"
            evidence_found = matched
        else:
            status = "FAIL"
            gap = f"No enum/const matching '{text}' found"

    elif category == "task":
        if assertion.get("completed"):
            status = "PASS"
            evidence_found = ["Marked complete in tasks.md"]
        else:
            status = "SKIP"
            gap = "Task not yet completed"

    return {
        "id": assertion["id"],
        "text": assertion["text"],
        "source": assertion["source"],
        "priority": assertion["priority"],
        "status": status,
        "evidence": evidence_found,
        "gap": gap,
    }


def _extract_keywords(text: str) -> List[str]:
    """Extract meaningful keywords from assertion text."""
    # Remove stop words
    stop_words = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "shall",
        "should", "may", "might", "must", "can", "could", "to", "of", "in",
        "for", "on", "with", "at", "by", "from", "as", "into", "through",
        "during", "before", "after", "above", "below", "between", "out", "off",
        "over", "under", "again", "further", "then", "once", "here", "there",
        "when", "where", "why", "how", "all", "both", "each", "few", "more",
        "most", "other", "some", "such", "no", "nor", "not", "only", "own",
        "same", "so", "than", "too", "very", "just", "because", "but", "and",
        "or", "if", "it", "its", "this", "that", "these", "those", "i", "me",
        "my", "we", "our", "you", "your", "he", "him", "his", "she", "her",
        "they", "them", "their", "what", "which", "who", "whom", "need", "needs",
        "support", "system", "user", "users",
    }
    words = re.findall(r"[a-zA-Z_][-a-zA-Z_0-9]*", text)
    return [w for w in words if w.lower() not in stop_words and len(w) > 2]


# ─────────────────────────────────────────────────────────────
# Report Generation
# ─────────────────────────────────────────────────────────────

def generate_report(
    project_dir: Path,
    strict: bool = False,
    write_report: bool = False,
) -> Dict[str, Any]:
    """Run full semantic verification and generate compliance report."""
    language = detect_language(project_dir) or "unknown"

    # Find spec files
    assertions: List[Dict[str, Any]] = []
    spec_dirs = [
        project_dir / "openspec" / "changes",
        project_dir / "openspec" / "specs",
    ]
    for spec_dir in spec_dirs:
        if not spec_dir.is_dir():
            continue
        for change_dir in spec_dir.iterdir():
            if not change_dir.is_dir():
                continue
            for spec_file in change_dir.glob("*.md"):
                try:
                    content = spec_file.read_text(encoding="utf-8")
                except OSError:
                    continue
                name = spec_file.stem.lower()
                if name == "proposal":
                    assertions.extend(extract_assertions_from_proposal(content))
                elif name == "design":
                    assertions.extend(extract_assertions_from_design(content))
                elif name == "tasks":
                    assertions.extend(extract_assertions_from_tasks(content))

    if not assertions:
        return {
            "status": "SKIP",
            "reason": "No spec files found to verify against",
            "assertions_checked": 0,
        }

    # Gather evidence
    evidence = gather_evidence(project_dir, language)

    # Check each assertion
    results = [check_assertion(a, evidence) for a in assertions]

    # Summarize
    summary = {"pass": 0, "partial": 0, "fail": 0, "skip": 0, "total": len(results)}
    for r in results:
        status_key = r["status"].lower()
        if status_key in summary:
            summary[status_key] += 1

    critical_gaps = [
        r for r in results
        if r["status"] == "FAIL" and r["priority"] == "HIGH"
    ]

    report = {
        "project_dir": str(project_dir),
        "language": language,
        "status": "FAIL" if critical_gaps else ("PASS" if summary["fail"] == 0 else "PARTIAL"),
        "summary": summary,
        "assertions": results,
        "critical_gaps": critical_gaps,
        "evidence_summary": {
            "endpoints": len(evidence["endpoints"]),
            "classes": len(evidence["classes"]),
            "fields": len(evidence["fields"]),
            "source_files": len(evidence["source_files"]),
            "test_files": len(evidence["test_files"]),
        },
    }

    # Write report
    if write_report:
        harness_dir = project_dir / ".harness"
        harness_dir.mkdir(exist_ok=True)
        (harness_dir / "semantic-report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )

        # Human-readable report
        lines = ["# Semantic Verification Report", ""]
        for r in results:
            icon = {"PASS": "+", "FAIL": "!", "PARTIAL": "~", "SKIP": "."}.get(r["status"], "?")
            lines.append(f"  [{icon}] {r['id']}: {r['text']}")
            if r["gap"]:
                lines.append(f"      Gap: {r['gap']}")
            if r["evidence"]:
                lines.append(f"      Evidence: {', '.join(str(e) for e in r['evidence'][:3])}")
        lines.append("")
        lines.append(f"Summary: {summary['pass']} pass, {summary['partial']} partial, "
                     f"{summary['fail']} fail, {summary['skip']} skip")

        (harness_dir / "semantic-report.md").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
        print("Report written to .harness/semantic-report.md")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Semantic verification: intent-level spec vs code comparison",
    )
    parser.add_argument("--strict", action="store_true", help="Treat PARTIAL as FAIL")
    parser.add_argument("--report", action="store_true", help="Write report to .harness/")
    parser.add_argument("--project-dir", default=".", help="Project directory (default: current)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}")
        sys.exit(1)

    print(f"Semantic Verification: {project_dir}")
    print()

    report = generate_report(project_dir, strict=args.strict, write_report=args.report)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        if report.get("status") == "SKIP":
            print(f"  {report['reason']}")
            sys.exit(0)

        s = report["summary"]
        print(f"  Assertions checked: {s['total']}")
        print(f"  Results: {s['pass']} pass, {s['partial']} partial, {s['fail']} fail, {s['skip']} skip")
        print()

        for r in report["assertions"]:
            icon = {"PASS": "+", "FAIL": "!", "PARTIAL": "~", "SKIP": "."}.get(r["status"], "?")
            priority = r.get("priority", "")
            print(f"  [{icon}] {r['id']} ({priority}): {r['text'][:70]}")
            if r["gap"]:
                print(f"      Gap: {r['gap']}")
            if r["evidence"]:
                ev_str = ", ".join(str(e)[:40] for e in r["evidence"][:3])
                print(f"      Evidence: {ev_str}")

        print()
        if report["critical_gaps"]:
            print(f"  CRITICAL GAPS ({len(report['critical_gaps'])}):")
            for gap in report["critical_gaps"]:
                print(f"    - {gap['id']}: {gap['gap']}")

        es = report.get("evidence_summary", {})
        print()
        print(f"  Evidence: {es.get('endpoints', 0)} endpoints, "
              f"{es.get('classes', 0)} classes, "
              f"{es.get('fields', 0)} fields, "
              f"{es.get('source_files', 0)} source files, "
              f"{es.get('test_files', 0)} test files")

    # Exit code
    if report.get("critical_gaps"):
        sys.exit(2)
    summary = report.get("summary", {})
    if summary.get("fail", 0) > 0:
        sys.exit(1)
    if args.strict and summary.get("partial", 0) > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
