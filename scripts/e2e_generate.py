#!/usr/bin/env python3
"""Generate E2E test stubs from OpenSpec specification files.

Reads proposal.md, design.md, and tasks.md to extract user-facing features
and generates Playwright test stubs for end-to-end testing.

Usage:
    python run.py e2e_generate.py
    python run.py e2e_generate.py --framework playwright-ts
    python run.py e2e_generate.py --output-dir tests/e2e --json

Exit codes:
    0: Tests generated successfully
    1: Error
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from harness_shared import detect_language, detect_framework


# ─────────────────────────────────────────────────────────────
# Spec Parsing
# ─────────────────────────────────────────────────────────────

def extract_section(content: str, heading: str) -> str:
    """Extract markdown section content by heading."""
    pattern = rf"^##\s+.*{re.escape(heading)}.*\n(.*?)(?=\n##\s|\Z)"
    match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_features_from_proposal(content: str) -> List[Dict[str, str]]:
    """Extract user-facing features from proposal success criteria."""
    features = []
    section = extract_section(content, "Success Criteria")
    if not section:
        section = extract_section(content, "Goals")

    for line in section.splitlines():
        line = line.strip()
        if not line.startswith(("- ", "* ", "1. ", "2. ")):
            continue
        text = re.sub(r"^[-*\d.]+\s*", "", line).strip()
        if len(text) > 5:
            # Convert to test-friendly name
            test_name = re.sub(r"[^a-zA-Z0-9\s]", "", text.lower())
            test_name = re.sub(r"\s+", "_", test_name)[:50]
            features.append({
                "name": test_name,
                "description": text,
                "source": "proposal",
            })
    return features


def extract_endpoints_from_design(content: str) -> List[Dict[str, str]]:
    """Extract API endpoints from design spec."""
    endpoints = []
    # Match HTTP methods + paths
    for match in re.finditer(
        r"(GET|POST|PUT|PATCH|DELETE)\s+(/[^\s]+)",
        content, re.IGNORECASE,
    ):
        method = match.group(1).upper()
        path = match.group(2).strip().strip("`")
        test_name = f"{method.lower()}_{path.strip('/').replace('/', '_').replace('{', '').replace('}', '')}"
        endpoints.append({
            "name": test_name,
            "method": method,
            "path": path,
            "description": f"{method} {path}",
            "source": "design",
        })
    return endpoints


def extract_ui_components_from_design(content: str) -> List[Dict[str, str]]:
    """Extract UI components and pages from design spec."""
    components = []
    section = extract_section(content, "Component")

    for match in re.finditer(
        r"(?:###|component)[:\s]+(\w[\w\s]*\w)",
        section, re.IGNORECASE,
    ):
        name = match.group(1).strip()
        if name.lower() not in ("component", "components"):
            components.append({
                "name": name.lower().replace(" ", "_"),
                "description": f"UI component: {name}",
                "source": "design",
            })
    return components


# ─────────────────────────────────────────────────────────────
# Test Generation
# ─────────────────────────────────────────────────────────────

def generate_playwright_ts(
    features: List[Dict],
    endpoints: List[Dict],
    components: List[Dict],
    feature_name: str,
) -> str:
    """Generate Playwright TypeScript test file."""
    lines = [
        f"import {{ test, expect }} from '@playwright/test';",
        "",
        f"test.describe('{feature_name}', () => {{",
    ]

    # Feature tests from proposal
    for feat in features:
        lines.extend([
            "",
            f"  test('{feat['description'][:60]}', async ({{ page }}) => {{",
            f"    // From spec: \"{feat['description']}\"",
            f"    // TODO: Navigate to the relevant page",
            f"    // await page.goto('/');",
            f"    // TODO: Add assertions for: {feat['description'][:80]}",
            f"  }});",
        ])

    # API endpoint tests
    for ep in endpoints:
        lines.extend([
            "",
            f"  test('API: {ep['method']} {ep['path']}', async ({{ request }}) => {{",
            f"    // From design: {ep['description']}",
            f"    const response = await request.{ep['method'].lower()}('{ep['path']}');",
            f"    // TODO: Add status code assertion",
            f"    // expect(response.ok()).toBeTruthy();",
            f"    // TODO: Add response body assertions",
            f"  }});",
        ])

    # UI component tests
    for comp in components:
        lines.extend([
            "",
            f"  test('UI: {comp['description']}', async ({{ page }}) => {{",
            f"    // From design: {comp['description']}",
            f"    // TODO: Navigate to page with {comp['name']} component",
            f"    // await page.goto('/');",
            f"    // TODO: Assert component renders correctly",
            f"    // await expect(page.locator('[data-testid=\"{comp['name']}\"]')).toBeVisible();",
            f"  }});",
        ])

    if not features and not endpoints and not components:
        lines.extend([
            "",
            "  test('placeholder - customize this test', async ({ page }) => {",
            "    // TODO: Replace with actual E2E test",
            "    // await page.goto('/');",
            "    // await expect(page).toHaveTitle(/.*/);",
            "  });",
        ])

    lines.extend(["", "});", ""])
    return "\n".join(lines)


def generate_playwright_py(
    features: List[Dict],
    endpoints: List[Dict],
    components: List[Dict],
    feature_name: str,
) -> str:
    """Generate Playwright Python test file."""
    lines = [
        "from playwright.sync_api import Page, expect",
        "",
        "",
        f"class Test{feature_name.replace('_', '').title().replace(' ', '')}:",
    ]

    for feat in features:
        test_name = f"test_{feat['name']}"
        lines.extend([
            "",
            f"    def {test_name}(self, page: Page) -> None:",
            f"        \"\"\"From spec: {feat['description']}\"\"\"",
            f"        # TODO: Navigate to the relevant page",
            f"        # page.goto('/')",
            f"        # TODO: Add assertions for: {feat['description'][:80]}",
            f"        pass",
        ])

    for ep in endpoints:
        test_name = f"test_api_{ep['name']}"
        lines.extend([
            "",
            f"    def {test_name}(self, page: Page) -> None:",
            f"        \"\"\"From design: {ep['description']}\"\"\"",
            f"        # TODO: Make API request",
            f"        # response = page.request.{ep['method'].lower()}('{ep['path']}')",
            f"        # expect(response).to_be_ok()",
            f"        pass",
        ])

    if not features and not endpoints:
        lines.extend([
            "",
            "    def test_placeholder(self, page: Page) -> None:",
            "        \"\"\"TODO: Replace with actual E2E test\"\"\"",
            "        # page.goto('/')",
            "        pass",
        ])

    lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate E2E test stubs from OpenSpec specifications",
    )
    parser.add_argument("--project-dir", default=".", help="Project directory")
    parser.add_argument(
        "--output-dir", default=None,
        help="Output directory for generated tests (auto-detected if not specified)",
    )
    parser.add_argument(
        "--framework",
        choices=["auto", "playwright-ts", "playwright-py"],
        default="auto",
        help="Test framework (default: auto-detect)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}")
        sys.exit(1)

    # Find spec files
    features = []
    endpoints = []
    components = []
    feature_name = "feature"

    spec_dirs = [
        project_dir / "openspec" / "changes",
        project_dir / "openspec" / "specs",
    ]
    for spec_dir in spec_dirs:
        if not spec_dir.is_dir():
            continue
        for change_dir in sorted(spec_dir.iterdir()):
            if not change_dir.is_dir():
                continue
            feature_name = change_dir.name
            for spec_file in change_dir.glob("*.md"):
                try:
                    content = spec_file.read_text(encoding="utf-8")
                except OSError:
                    continue
                name = spec_file.stem.lower()
                if name == "proposal":
                    features.extend(extract_features_from_proposal(content))
                elif name == "design":
                    endpoints.extend(extract_endpoints_from_design(content))
                    components.extend(extract_ui_components_from_design(content))

    if not features and not endpoints and not components:
        print("No testable features found in specs.")
        print("Ensure proposal.md and design.md contain Success Criteria and API endpoints.")
        sys.exit(1)

    # Detect framework
    if args.framework == "auto":
        language = detect_language(project_dir) or "typescript"
        if language == "python":
            framework = "playwright-py"
        else:
            framework = "playwright-ts"
    else:
        framework = args.framework

    # Generate test content
    if framework == "playwright-py":
        content = generate_playwright_py(features, endpoints, components, feature_name)
        ext = ".py"
        prefix = "test_"
    else:
        content = generate_playwright_ts(features, endpoints, components, feature_name)
        ext = ".spec.ts"
        prefix = ""

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        # Auto-detect common E2E directories
        candidates = [
            project_dir / "e2e",
            project_dir / "tests" / "e2e",
            project_dir / "test" / "e2e",
            project_dir / "__tests__" / "e2e",
        ]
        output_dir = next((d for d in candidates if d.exists()), candidates[0])

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{prefix}{feature_name}{ext}"
    output_file.write_text(content, encoding="utf-8")

    summary = {
        "generated": str(output_file),
        "framework": framework,
        "features_count": len(features),
        "endpoints_count": len(endpoints),
        "components_count": len(components),
        "total_tests": len(features) + len(endpoints) + len(components),
    }

    if args.json:
        summary["features"] = features
        summary["endpoints"] = endpoints
        summary["components"] = components
        print(json.dumps(summary, indent=2))
    else:
        print(f"E2E Test Generator")
        print(f"  Framework: {framework}")
        print(f"  Features: {len(features)} (from proposal)")
        print(f"  Endpoints: {len(endpoints)} (from design)")
        print(f"  Components: {len(components)} (from design)")
        print(f"  Total test stubs: {summary['total_tests']}")
        print(f"  Output: {output_file}")
        print()
        print("Next steps:")
        print("  1. Review generated test stubs")
        print("  2. Fill in TODO assertions with actual test logic")
        print("  3. Run: npx playwright test" if framework == "playwright-ts" else "  3. Run: pytest --headed")

    sys.exit(0)


if __name__ == "__main__":
    main()
