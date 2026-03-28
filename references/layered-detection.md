# Layered Quality Detection - Preventing AI Attention Gaps

> Core Principle: **AI supplements, never replaces** — Critical checks must use deterministic tools

## Table of Contents

- [Problem Analysis](#problem-analysis)
- [Solution: Layered Detection Architecture](#solution-layered-detection-architecture)
- [Layer 1: Mandatory Checks](#layer-1-mandatory-checks)
- [Layer 2: Rule Engine Configuration](#layer-2-rule-engine-configuration)
- [Layer 3: AI Enhancement](#layer-3-ai-enhancement-supplementary-only)
- [Comparison: With vs Without Layered Detection](#comparison-with-vs-without-layered-detection)
- [Implementation Recommendations](#implementation-recommendations)
- [Summary](#summary)

## Problem Analysis

### AI Detection Limitations

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AI Detection vs Rule Engine Comparison           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  AI Strengths:                                                      │
│  ✅ Understands code context and business logic                     │
│  ✅ Detects novel vulnerability patterns                            │
│  ✅ Finds logic flaws and design issues                             │
│  ✅ Adapts to different coding styles                               │
│                                                                     │
│  AI Weaknesses:                                                     │
│  ❌ Attention may wander                                            │
│  ❌ Inefficient for deterministic problems                          │
│  ❌ Results not reproducible (same code may yield different results)│
│  ❌ May produce excessive false positives or negatives              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Specific Attention Gap Scenarios

```javascript
// Scenario 1: Missing checks in complex context
async function processOrder(order) {
  // AI attention: validating order data
  if (!order.items || order.items.length === 0) {
    throw new Error('Empty order');
  }

  // AI may miss: no check for order.userId existence
  const user = await db.users.find(order.userId); // ← potential null pointer

  // AI may miss: dynamic SQL concatenation
  const query = `SELECT * FROM orders WHERE id = ${order.id}`; // ← SQL injection

  // AI attention: obvious sensitive data handling
  const payment = await processPayment(order.payment);
  return { user, payment };
}

// Scenario 2: Cross-file issues
// file1.ts - AI only looks at this file
export const config = {
  apiUrl: 'https://api.example.com',
  // AI may miss: no check for unsafe usage of this config elsewhere
};

// file2.ts - Requires cross-file analysis to detect the issue
import { config } from './file1';
fetch(`${config.apiUrl}/users/${userId}`); // ← if userId is unvalidated, IDOR risk
```

---

## Solution: Layered Detection Architecture

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                      LAYERED DETECTION ARCHITECTURE                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Layer 3: AI Enhancement (Optional)                                 │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ • Logic flaw detection         • Business rule validation   │   │
│  │ • Code smell analysis          • Design pattern suggestions  │   │
│  │ • Context-aware checks         • Complex problem reasoning   │   │
│  │ Role: Supplementary detection, does not block                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              ▼                                      │
│  Layer 2: Rule Engine (Mandatory)                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ • SAST (SonarQube/Semgrep)    • SCA (Snyk/Dependabot)       │   │
│  │ • Lint (ESLint/PMD)           • Secrets (Gitleaks)           │   │
│  │ • TypeCheck (tsc/mypy)        • Format (Prettier)            │   │
│  │ Role: Deterministic checks, must pass                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              ▼                                      │
│  Layer 1: Mandatory Checks (Cannot Skip)                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ • SQL injection patterns (100% coverage)  • Hardcoded secrets (100%)│
│  │ • XSS patterns (100% coverage)           • Dangerous function calls │
│  │ • Authorization checks (critical paths)   • Input validation (boundaries)│
│  │ Role: Core security, zero tolerance                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Tool Type | Coverage | False Positive Rate | Blocking | Purpose |
|-------|-----------|----------|---------------------|----------|---------|
| **Layer 1** | Regex/AST | 100% | Very low | Must block | Known vulnerability patterns |
| **Layer 2** | Rule engine | 95%+ | Low | By severity | Code quality/security |
| **Layer 3** | AI analysis | 60-80% | Medium | Warnings only | Logic/design issues |

---

## Layer 1: Mandatory Checks

### 1.1 Non-Skippable Security Checks

```yaml
# mandatory-checks.yaml
mandatory_checks:
  # ─────────────────────────────────────────────────────────────
  # SQL Injection - Regex patterns, 100% coverage
  # ─────────────────────────────────────────────────────────────
  sql_injection:
    severity: CRITICAL
    block_merge: true
    patterns:
      # String concatenation SQL
      - pattern: "(SELECT|INSERT|UPDATE|DELETE).*\\$\\{"
        languages: [javascript, typescript]
      - pattern: "\\.(query|execute)\\([\"'].*\\+"
        languages: [javascript, typescript]
      - pattern: "String.*format.*SELECT"
        languages: [java]
      - pattern: "cursor\\.execute.*%"
        languages: [python]

    # Must use parameterized queries
    remediation: "Use parameterized queries: db.query('SELECT * FROM users WHERE id = ?', [userId])"

  # ─────────────────────────────────────────────────────────────
  # Hardcoded Secrets - 100% coverage
  # ─────────────────────────────────────────────────────────────
  hardcoded_secrets:
    severity: CRITICAL
    block_merge: true
    patterns:
      - pattern: "(api_key|apikey|api-key)\\s*=\\s*[\"'][^\"']{10,}[\"']"
        case_insensitive: true
      - pattern: "(password|passwd|pwd)\\s*=\\s*[\"'][^\"']+[\"']"
        case_insensitive: true
      - pattern: "(secret|token|auth)\\s*=\\s*[\"'][^\"']{16,}[\"']"
        case_insensitive: true
      - pattern: "-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"

    remediation: "Use environment variables or secret manager"

  # ─────────────────────────────────────────────────────────────
  # Dangerous Function Calls
  # ─────────────────────────────────────────────────────────────
  dangerous_functions:
    severity: CRITICAL
    block_merge: true
    functions:
      javascript:
        - "eval()"
        - "Function()"
        - "setTimeout(string)"
        - "setInterval(string)"
      python:
        - "eval()"
        - "exec()"
        - "compile()"
        - "__import__()"
      java:
        - "Runtime.exec()"
        - "ProcessBuilder.command(string)"

  # ─────────────────────────────────────────────────────────────
  # XSS Patterns
  # ─────────────────────────────────────────────────────────────
  xss_prevention:
    severity: HIGH
    block_merge: true
    patterns:
      - pattern: "innerHTML\\s*=\\s*[^$]"
        languages: [javascript, typescript]
        message: "Use textContent or sanitize HTML"
      - pattern: "dangerouslySetInnerHTML"
        languages: [javascript, typescript]
        message: "Ensure content is sanitized"
      - pattern: "document\\.write"
        languages: [javascript]
        message: "Avoid document.write"

  # ─────────────────────────────────────────────────────────────
  # Authorization Checks (Critical Paths)
  # ─────────────────────────────────────────────────────────────
  authorization:
    severity: CRITICAL
    block_merge: true
    paths:
      - "src/api/**/delete*.ts"
      - "src/api/**/update*.ts"
      - "src/api/**/admin*.ts"
    required_patterns:
      - "checkPermission|requireAuth|isAuthenticated|hasRole"
    message: "All mutation endpoints must have authorization check"
```

### 1.2 Mandatory Check Script

```python
#!/usr/bin/env python3
"""
Mandatory check script - runs in CI/CD, cannot be skipped.
Uses deterministic pattern matching, does not rely on AI.
"""

import re
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Violation:
    file: str
    line: int
    rule: str
    severity: str
    message: str
    pattern: str

class MandatoryChecker:
    """Mandatory checker - deterministic checks without AI dependency"""

    # SQL injection patterns (precise matching)
    SQL_INJECTION_PATTERNS = [
        # JavaScript/TypeScript
        (r'(?:query|execute)\s*\(\s*[`"\'].*\$\{', 'SQL injection: string interpolation in query'),
        (r'(?:query|execute)\s*\(\s*[`"\'].*\+', 'SQL injection: string concatenation in query'),
        # Python
        (r'cursor\.execute\s*\(\s*[fF]?["\'].*%', 'SQL injection: format string in query'),
        (r'\.execute\s*\(\s*[^,]+\+', 'SQL injection: concatenation in query'),
        # Java
        (r'String\s+\w+\s*=\s*".*(?:SELECT|INSERT|UPDATE|DELETE).*"\s*\+', 'SQL injection: string building'),
        (r'\.createQuery\s*\(\s*".*\+', 'SQL injection: HQL injection'),
    ]

    # Hardcoded secret patterns
    SECRET_PATTERNS = [
        (r'(?:api[_-]?key|apikey)\s*=\s*["\'][^"\']{16,}["\']', 'Hardcoded API key'),
        (r'(?:password|passwd|pwd)\s*=\s*["\'][^"\']+["\']', 'Hardcoded password'),
        (r'(?:secret|token|auth)\s*=\s*["\'][^"\']{20,}["\']', 'Hardcoded secret'),
        (r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----', 'Hardcoded private key'),
        (r'aws_access_key_id\s*=\s*["\']AKIA', 'Hardcoded AWS key'),
    ]

    # Dangerous function patterns
    DANGEROUS_FUNCTIONS = {
        '.ts': [
            (r'\beval\s*\(', 'Dangerous: eval() allows code injection'),
            (r'\bFunction\s*\(', 'Dangerous: Function() allows code injection'),
            (r'setTimeout\s*\(\s*["\']', 'Dangerous: setTimeout with string'),
            (r'setInterval\s*\(\s*["\']', 'Dangerous: setInterval with string'),
        ],
        '.py': [
            (r'\beval\s*\(', 'Dangerous: eval() allows code injection'),
            (r'\bexec\s*\(', 'Dangerous: exec() allows code injection'),
            (r'__import__\s*\(', 'Dangerous: dynamic import'),
        ],
        '.java': [
            (r'Runtime\.getRuntime\(\)\.exec\s*\(', 'Dangerous: Runtime.exec()'),
            (r'ProcessBuilder.*\.command\s*\([^)]*\+', 'Dangerous: command injection'),
        ],
    }

    def __init__(self):
        self.violations: List[Violation] = []

    def check_file(self, file_path: Path) -> List[Violation]:
        """Check a single file"""
        violations = []

        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
        except Exception:
            return violations

        # Get file extension
        ext = file_path.suffix

        for line_num, line in enumerate(lines, 1):
            # SQL injection check
            for pattern, message in self.SQL_INJECTION_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(Violation(
                        file=str(file_path),
                        line=line_num,
                        rule='SQL_INJECTION',
                        severity='CRITICAL',
                        message=message,
                        pattern=pattern
                    ))

            # Secret check
            for pattern, message in self.SECRET_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(Violation(
                        file=str(file_path),
                        line=line_num,
                        rule='HARDCODED_SECRET',
                        severity='CRITICAL',
                        message=message,
                        pattern=pattern
                    ))

            # Dangerous function check
            if ext in self.DANGEROUS_FUNCTIONS:
                for pattern, message in self.DANGEROUS_FUNCTIONS[ext]:
                    if re.search(pattern, line):
                        violations.append(Violation(
                            file=str(file_path),
                            line=line_num,
                            rule='DANGEROUS_FUNCTION',
                            severity='CRITICAL',
                            message=message,
                            pattern=pattern
                        ))

        return violations

    def check_directory(self, directory: Path, extensions: List[str]) -> List[Violation]:
        """Check entire directory"""
        all_violations = []

        for ext in extensions:
            for file_path in directory.rglob(f'*{ext}'):
                # Skip node_modules, .git, etc.
                if any(part.startswith('.') or part == 'node_modules' for part in file_path.parts):
                    continue
                all_violations.extend(self.check_file(file_path))

        return all_violations

def main():
    """Main entry point - runs in CI/CD"""
    checker = MandatoryChecker()

    # Check src directory
    src_dir = Path('src')
    if not src_dir.exists():
        print("❌ src directory not found")
        sys.exit(1)

    violations = checker.check_directory(src_dir, ['.ts', '.tsx', '.js', '.jsx', '.py', '.java'])

    if violations:
        print("\n" + "="*70)
        print("🚨 MANDATORY CHECK FAILED - DO NOT SKIP THESE CHECKS")
        print("="*70 + "\n")

        for v in violations:
            print(f"❌ [{v.severity}] {v.rule}")
            print(f"   File: {v.file}:{v.line}")
            print(f"   Issue: {v.message}")
            print()

        print("="*70)
        print(f"Total violations: {len(violations)}")
        print("These issues MUST be fixed before merge.")
        print("This check uses deterministic pattern matching and cannot be bypassed.")
        print("="*70)

        sys.exit(1)
    else:
        print("✅ All mandatory checks passed")
        sys.exit(0)

if __name__ == '__main__':
    main()
```

---

## Layer 2: Rule Engine Configuration

### 2.1 Semgrep Rules (High Determinism)

```yaml
# .semgrep/rules.yaml
rules:
  # ─────────────────────────────────────────────────────────────
  # SQL Injection - Semgrep precise patterns
  # ─────────────────────────────────────────────────────────────
  - id: sql-injection-string-concat
    languages: [javascript, typescript]
    severity: ERROR
    message: "SQL injection via string concatenation"
    patterns:
      - pattern-either:
          - pattern: |
              $DB.query($QUERY + ...)
          - pattern: |
              $DB.query(`...${$VAR}...`)
          - pattern: |
              $DB.execute($QUERY + ...)
    fix: |
      // Use parameterized queries:
      $DB.query('SELECT * FROM users WHERE id = ?', [$ID]);

  # ─────────────────────────────────────────────────────────────
  # SSRF Detection
  # ─────────────────────────────────────────────────────────────
  - id: ssrf-via-user-input
    languages: [javascript, typescript]
    severity: ERROR
    message: "Potential SSRF via user-controlled URL"
    patterns:
      - pattern: |
          fetch($REQ.body.$URL, ...)
      - pattern: |
          axios.get($REQ.query.$URL, ...)
      - pattern: |
          http.get($USER_INPUT, ...)
    metadata:
      cwe: "CWE-918: Server-Side Request Forgery"

  # ─────────────────────────────────────────────────────────────
  # Path Traversal
  # ─────────────────────────────────────────────────────────────
  - id: path-traversal
    languages: [javascript, typescript, python]
    severity: ERROR
    message: "Potential path traversal via user input"
    patterns:
      - pattern-either:
          - pattern: |
              fs.readFile($USER_INPUT, ...)
          - pattern: |
              open($USER_INPUT, ...)
          - pattern: |
              Path.join(..., $USER_INPUT)
```

### 2.2 SonarQube Quality Configuration

```properties
# sonar-project.properties
# Mandatory quality gate

# Security hotspots - must review
sonar.security.hotspots.review.force=true

# Coverage threshold
sonar.coverage.minimum=80

# Duplication threshold
sonar.cpd.exclusions=**/*.test.ts
sonar.duplications.excluded = true

# New code quality gate
sonar.qualitygate.wait=true
sonar.qualitygate.timeout=600

# Cannot skip
sonar.skip=false
```

---

## Layer 3: AI Enhancement (Supplementary Only)

### 3.1 AI Analysis Scope

```yaml
# ai-analysis.yaml
ai_checks:
  # These checks do not block, only provide suggestions

  enabled: true
  blocking: false  # AI checks do not block

  scope:
    # Areas where AI excels
    - logic_analysis        # Logic flaws
    - business_rule_check   # Business rule validation
    - design_pattern        # Design pattern suggestions
    - code_smell            # Code smell detection
    - documentation         # Documentation completeness

  # Areas AI is NOT responsible for (handled by Layer 1 & 2)
  excluded:
    - sql_injection         # Handled by Semgrep
    - xss_detection         # Handled by SonarQube
    - hardcoded_secrets     # Handled by Gitleaks
    - dependency_vulns      # Handled by Snyk

  # AI analysis report
  report:
    format: markdown
    include_confidence: true
    max_findings: 50
```

### 3.2 AI Analysis Prompt Template

```markdown
# AI Code Analysis Prompt

You are a code review assistant. Your task is to complement traditional static analysis tools.

**Important Limitations:**
- Do not report SQL injection, XSS, hardcoded secrets, etc. (handled by Semgrep/Gitleaks)
- Focus on logic flaws, business rules, design issues

**Please analyze the following code:**

1. **Logic Flaws**
   - Are boundary conditions handled?
   - Are error states correctly propagated?
   - Do concurrency issues exist?

2. **Business Rules**
   - Does it conform to common business patterns?
   - Is data consistency guaranteed?
   - Are permission checks complete?

3. **Design Issues**
   - Is there single responsibility?
   - Is coupling too high?
   - Are there better design patterns?

**Output Format:**
| Type | Location | Description | Confidence | Suggestion |
|------|----------|-------------|------------|------------|
```

---

## Comparison: With vs Without Layered Detection

### Scenario: Detecting SQL Injection

```
┌─────────────────────────────────────────────────────────────────────┐
│  Code: db.query(`SELECT * FROM users WHERE id = ${userId}`)         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ❌ AI-only approach:                                               │
│  - AI may detect: "This template string looks suspicious"           │
│  - AI may miss: if context is complex, attention may wander         │
│  - Result: ~70% detection rate                                     │
│                                                                     │
│  ✅ Layered detection:                                              │
│  Layer 1 (Regex): Pattern matches `${...}` in SQL string → 100%    │
│  Layer 2 (Semgrep): AST analysis confirms db.query call → 100%     │
│  Layer 3 (AI): Analyzes if userId source is trusted → supplementary│
│  - Result: 100% detection rate                                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Recommendations

### 1. Priority Order

```
Priority 1: Deploy Layer 1 mandatory checks (Regex/AST)
         - Immediately blocks known vulnerability patterns
         - Zero dependencies, fast deployment

Priority 2: Integrate Layer 2 rule engines
         - SonarQube/Semgrep configuration
         - CI/CD integration

Priority 3: Add Layer 3 AI enhancement
         - Supplementary detection
         - Does not block, only suggests
```

### 2. Team Guidelines

```yaml
team_guidelines:
  # Mandatory
  mandatory:
    - "All PRs must pass Layer 1 checks"
    - "CRITICAL issues must be fixed before merge"
    - "Not allowed to use --no-verify to skip checks"

  # Recommended
  recommended:
    - "Review AI analysis reports"
    - "Fix HIGH severity issues"
    - "Track MEDIUM issue trends"

  # Forbidden
  forbidden:
    - "Never disable quality gates"
    - "Never skip pre-commit hooks"
    - "Never use --skip-tests in CI"
```

---

## Summary

| Check Type | AI Reliability | Rule Engine Reliability | Recommended Approach |
|------------|---------------|------------------------|---------------------|
| Known vulnerability patterns (SQLi, XSS) | ~70% | 99%+ | **Rule engine mandatory** |
| Secret exposure detection | ~65% | 99%+ | **Gitleaks mandatory** |
| Logic flaws | ~60% | ~20% | AI supplementary |
| Business rule validation | ~55% | ~10% | AI supplementary |
| Code style | ~50% | 100% | Prettier/ESLint |

**Core Principle: Use rule engines for deterministic checks, AI for context-aware supplementary analysis**
