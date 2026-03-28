# Quality Gates

> Quality control module for Harness Workflow, covering code standards, SAST/SCA scanning, and database design validation

## Quality Control Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        QUALITY GATES ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────┤
│  Gate 4: PRODUCTION    → Performance testing, security audit, compliance│
│  Gate 3: STAGING       → E2E testing, integration testing, pen testing  │
│  Gate 2: CI/CD         → SAST, SCA, code standards, unit testing        │
│  Gate 1: PRE-COMMIT    → Lint, Format, TypeCheck, Secrets Detection     │
│  Gate 0: IDE           → Real-time lint, AI-assisted review             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. SAST vs SCA Comparison

| Type | SAST (Static Application Security Testing) | SCA (Software Composition Analysis) |
|------|---------------------------------------------|-------------------------------------|
| **Target** | Source code vulnerabilities | Third-party dependency vulnerabilities |
| **Timing** | Before compilation | At build/deploy time |
| **Detects** | SQL injection, XSS, hardcoded secrets | CVE vulnerabilities, license risks |
| **Tools** | SonarQube, Snyk Code, Semgrep | Snyk, Dependabot, OWASP DC |

## 2. SonarQube vs Snyk Comparison

| Dimension | SonarQube | Snyk |
|-----------|-----------|------|
| **SAST** | ✅ Strong | ✅ Snyk Code |
| **SCA** | ✅ Limited | ✅ Strong (specialized) |
| **Deployment** | Self-hosted / Cloud | SaaS / Self-hosted |
| **Language Support** | 29+ languages | Major languages |
| **Pricing** | Community edition free | Limited free tier |

## 3. Language-Specific Linters

### JavaScript/TypeScript
```yaml
# ESLint rules
rules:
  no-unused-vars: error
  @typescript-eslint/no-explicit-any: error
  complexity: [error, 10]        # Cyclomatic complexity ≤ 10
  max-depth: [error, 4]          # Nesting depth ≤ 4
  max-lines-per-function: [error, 50]
```

### Python
```toml
# Ruff (replaces Flake8/Black/Isort)
[tool.ruff]
select = ["E", "W", "F", "I", "B", "UP"]
line-length = 100
```

### Java
```xml
<!-- PMD + Checkstyle + SpotBugs -->
<plugin>
  <artifactId>maven-pmd-plugin</artifactId>
  <configuration>
    <rulesets>
      <ruleset>/rulesets/java/design.xml</ruleset>
      <ruleset>/rulesets/java/security.xml</ruleset>
    </rulesets>
  </configuration>
</plugin>
```

### Go
```yaml
# golangci-lint
linters:
  enable:
    - govet
    - staticcheck
    - gocyclo        # Cyclomatic complexity
    - goconst        # Repeated strings
```

---

## 4. Database Quality Control

### Schema Validation Rules
```yaml
schema_rules:
  naming:
    tables: snake_case
    indexes: idx_{table}_{cols}

  required_columns:
    - id (UUID, PRIMARY KEY)
    - created_at (TIMESTAMP)
    - updated_at (TIMESTAMP)

  forbidden:
    - nullable_primary_keys
    - orphan_foreign_keys
    - unindexed_foreign_keys

  indexing:
    - all_foreign_keys: true
    - frequently_queried: true
```

### Migration Checks
```yaml
pre_migration:
  - backup_exists
  - foreign_key_integrity

post_migration:
  - schema_consistency
  - index_validity
  - data_integrity
```

### Database Unit Tests
```sql
-- pgTAP (PostgreSQL)
SELECT has_table('users');
SELECT has_column('users', 'email');
SELECT col_is_unique('users', 'email');
SELECT fk_ok('orders', 'user_id', 'users', 'id');
```

---

## 5. CI/CD Quality Gates

```yaml
# GitHub Actions
jobs:
  lint:
    runs: npm run lint && npm run typecheck

  sast:
    runs: sonarqube-scan + semgrep

  sca:
    runs: snyk test + dependency-review

  secrets:
    runs: gitleaks + trufflehog

  test:
    runs: npm run test:coverage
    threshold: 80%

  db-validation:
    runs: migration-check + db-tests
```

---

## 6. Quality Rule Severity Levels

| Severity | Example Rules | Behavior |
|----------|--------------|----------|
| **CRITICAL** | SQL injection, hardcoded secrets, null primary keys | Block merge |
| **HIGH** | XSS, high-severity CVEs, unindexed foreign keys | Warning + SLA |
| **MEDIUM** | Code smells, medium-severity CVEs | Record as tech debt |
| **LOW** | Style issues, code duplication | Report only |

---

## 7. Integration with Harness Workflow

```yaml
# .harness/config.yaml
quality_gates:
  pre_commit:   [lint, format, typecheck, secrets]
  pre_push:     [test, coverage, security]
  pre_merge:    [sast, sca, review, db_check]
  pre_deploy:   [e2e, performance, compliance]

  blocking:
    critical: true   # CRITICAL must be fixed
    high: true       # HIGH blocks merge
    medium: false    # MEDIUM warning only
```

---

## Summary Table

| Quality Dimension | Tool | Timing | Blocking |
|-------------------|------|--------|----------|
| Code Standards | ESLint/PMD/Checkstyle | Pre-commit | ✅ |
| Type Checking | TypeScript/mypy | Pre-commit | ✅ |
| SAST | SonarQube/Snyk/Semgrep | Pre-merge | ✅ |
| SCA | Snyk/Dependabot | Pre-merge | ✅ |
| Secrets | Gitleaks/Trufflehog | Pre-commit | ✅ |
| Test Coverage | Jest/pytest | Pre-push | 80% |
| Database | pgTAP/tSQLt | Pre-merge | ✅ |
