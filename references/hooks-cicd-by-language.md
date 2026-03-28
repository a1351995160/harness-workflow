# Language-Specific Quality Configuration

> Hooks + CI/CD + PR configuration for different programming languages and project types

## Table of Contents

- [Configuration Overview](#configuration-overview)
- [TypeScript/JavaScript Projects](#typescriptjavascript-projects)
- [Python Projects](#python-projects)
- [Go Projects](#go-projects)
- [Java Projects](#java-projects)
- [Database Projects (SQL)](#database-projects-sql)
- [PR Quality Gate Template](#pr-quality-gate-templates)
- [Quick Setup Commands](#quick-setup-commands)
- [Summary Table](#summary-table)

## Configuration Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Quality Configuration Layered Architecture           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Claude Code Hooks (Development)                                        │
│  ├── PostToolUse: Auto lint/format after file write                     │
│  └── Stop: Verify before session ends                                   │
│                                                                         │
│  Git Hooks (Commit Time)                                                │
│  ├── pre-commit: Fast checks (lint, format, secrets)                    │
│  └── pre-push: Full checks (test, coverage)                             │
│                                                                         │
│  CI/CD (Server-side)                                                    │
│  ├── SAST: SonarQube, Semgrep                                          │
│  ├── SCA: Snyk, Dependabot                                             │
│  └── Test: Unit, Integration, E2E                                       │
│                                                                         │
│  PR Quality Gates (Merge Time)                                          │
│  └── Branch protection: Must pass all checks before merge               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. TypeScript/JavaScript Projects

### 1.1 Claude Code Hooks

```json
// .claude/settings.json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "npx eslint --fix ${file}",
            "timeout": 30000
          },
          {
            "type": "command",
            "command": "npx prettier --write ${file}",
            "timeout": 15000
          }
        ]
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "npm run typecheck",
        "timeout": 60000
      }
    ]
  }
}
```

### 1.2 Git Hooks (Lefthook)

```yaml
# lefthook.yml
pre-commit:
  parallel: true
  commands:
    eslint:
      glob: "*.{js,jsx,ts,tsx}"
      run: npx eslint {staged_files}
      stage_fixed: true

    prettier:
      glob: "*.{js,jsx,ts,tsx,json,css,md}"
      run: npx prettier --check {staged_files}

    typecheck:
      glob: "*.{ts,tsx}"
      run: npx tsc --noEmit

    secrets:
      run: |
        if grep -rE "(api_key|password|secret|token)\s*=\s*['\"][^'\"]+['\"]" {staged_files}; then
          echo "❌ Potential secrets detected"
          exit 1
        fi

pre-push:
  commands:
    test:
      run: npm run test:coverage
      env:
        CI: true

    security:
      run: npm audit --audit-level=moderate
```

### 1.3 CI/CD (GitHub Actions)

```yaml
# .github/workflows/quality.yml
name: Quality Gates

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci

      - name: ESLint
        run: npm run lint

      - name: TypeScript
        run: npm run typecheck

      - name: Test with Coverage
        run: npm run test:coverage

      - name: Upload Coverage
        uses: codecov/codecov-action@v4
        with:
          fail_ci_if_error: true

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Snyk Security
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          command: test
          args: --severity-threshold=high

      - name: Semgrep SAST
        uses: returntocorp/semgrep-action@v1
        with:
          config: p/typescript

  sonarqube:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: SonarQube Scan
        uses: sonarsource/sonarqube-scan-action@master
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}
```

### 1.4 Branch Protection Configuration

```yaml
# GitHub Branch Protection (via API or UI)
branch_protection:
  main:
    required_status_checks:
      strict: true
      contexts:
        - "lint-and-test"
        - "security"
        - "sonarqube"
    enforce_admins: true
    required_pull_request_reviews:
      required_approving_review_count: 1
```

---

## 2. Python Projects

### 2.1 Claude Code Hooks

```json
// .claude/settings.json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "ruff check --fix ${file} && ruff format ${file}",
            "timeout": 30000
          }
        ]
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "mypy src/ --ignore-missing-imports",
        "timeout": 60000
      }
    ]
  }
}
```

### 2.2 Git Hooks (Lefthook)

```yaml
# lefthook.yml
pre-commit:
  parallel: true
  commands:
    ruff:
      glob: "*.py"
      run: ruff check {staged_files}
      stage_fixed: true

    ruff-format:
      glob: "*.py"
      run: ruff format --check {staged_files}

    mypy:
      glob: "*.py"
      run: mypy {staged_files} --ignore-missing-imports

    secrets:
      run: |
        if grep -rE "(api_key|password|secret|token)\s*=\s*['\"][^'\"]+['\"]" {staged_files}; then
          echo "❌ Potential secrets detected"
          exit 1
        fi

pre-push:
  commands:
    test:
      run: pytest --cov=src --cov-fail-under=80

    safety:
      run: safety check
```

### 2.3 CI/CD (GitHub Actions)

```yaml
# .github/workflows/quality.yml
name: Quality Gates

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - run: pip install -r requirements-dev.txt

      - name: Ruff
        run: ruff check .

      - name: Ruff Format
        run: ruff format --check .

      - name: MyPy
        run: mypy src/ --ignore-missing-imports

      - name: Test with Coverage
        run: pytest --cov=src --cov-fail-under=80 --cov-report=xml

      - name: Upload Coverage
        uses: codecov/codecov-action@v4

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - run: pip install safety bandit

      - name: Safety (SCA)
        run: safety check --json

      - name: Bandit (SAST)
        run: bandit -r src/ -ll

  sonarqube:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: SonarQube Scan
        uses: sonarsource/sonarqube-scan-action@master
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}
```

---

## 3. Go Projects

### 3.1 Claude Code Hooks

```json
// .claude/settings.json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "gofmt -w ${file}",
            "timeout": 15000
          },
          {
            "type": "command",
            "command": "goimports -w ${file}",
            "timeout": 15000
          }
        ]
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "go vet ./...",
        "timeout": 60000
      },
      {
        "type": "command",
        "command": "golangci-lint run",
        "timeout": 120000
      }
    ]
  }
}
```

### 3.2 Git Hooks (Lefthook)

```yaml
# lefthook.yml
pre-commit:
  parallel: true
  commands:
    gofmt:
      glob: "*.go"
      run: gofmt -l {staged_files}

    goimports:
      glob: "*.go"
      run: goimports -l {staged_files}

    go-vet:
      glob: "*.go"
      run: go vet ./...

    golangci-lint:
      glob: "*.go"
      run: golangci-lint run --fast

pre-push:
  commands:
    test:
      run: go test -v -race -coverprofile=coverage.out ./...

    coverage:
      run: |
        go tool cover -func=coverage.out | grep total | awk '{if ($3+0 < 80) exit 1}'
```

### 3.3 CI/CD (GitHub Actions)

```yaml
# .github/workflows/quality.yml
name: Quality Gates

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-go@v5
        with:
          go-version: '1.21'

      - name: golangci-lint
        uses: golangci/golangci-lint-action@v3
        with:
          version: latest

      - name: Test with Coverage
        run: |
          go test -v -race -coverprofile=coverage.out ./...
          go tool cover -func=coverage.out

      - name: Upload Coverage
        uses: codecov/codecov-action@v4

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Gosec Security Scanner
        uses: securego/gosec@master
        with:
          args: ./...

      - name: Snyk
        uses: snyk/actions/golang@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
```

---

## 4. Java Projects

### 4.1 Claude Code Hooks

```json
// .claude/settings.json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "mvn spotless:apply -DspotlessFiles=${file}",
            "timeout": 60000
          }
        ]
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "mvn checkstyle:check pmd:check spotbugs:check",
        "timeout": 180000
      }
    ]
  }
}
```

### 4.2 Git Hooks (Lefthook)

```yaml
# lefthook.yml
pre-commit:
  parallel: true
  commands:
    spotless:
      glob: "*.java"
      run: mvn spotless:check

    checkstyle:
      glob: "*.java"
      run: mvn checkstyle:check

pre-push:
  commands:
    test:
      run: mvn test jacoco:report

    coverage:
      run: |
        COVERAGE=$(grep -o '<counter type="INSTRUCTION"[^/]*/>' target/site/jacoco/jacoco.xml | grep -o 'covered="[0-9]*"' | head -1 | grep -o '[0-9]*')
        if [ "$COVERAGE" -lt 80 ]; then
          echo "❌ Coverage below 80%"
          exit 1
        fi

    spotbugs:
      run: mvn spotbugs:check

    pmd:
      run: mvn pmd:check
```

### 4.3 CI/CD (GitHub Actions)

```yaml
# .github/workflows/quality.yml
name: Quality Gates

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'
          cache: 'maven'

      - name: Checkstyle
        run: mvn checkstyle:check

      - name: PMD
        run: mvn pmd:check

      - name: SpotBugs
        run: mvn spotbugs:check

      - name: Test with Coverage
        run: mvn test jacoco:report

      - name: Upload Coverage
        uses: codecov/codecov-action@v4

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: OWASP Dependency Check
        uses: dependency-check/Dependency-Check_Action@main
        with:
          project: 'My Project'
          path: '.'
          format: 'HTML'
          out: 'reports'

      - name: Snyk
        uses: snyk/actions/maven@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}

  sonarqube:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: SonarQube Scan
        uses: sonarsource/sonarqube-scan-action@master
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}
```

---

## 5. Database Projects (SQL)

### 5.1 Claude Code Hooks

```json
// .claude/settings.json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "sqlfluff fix ${file} --dialect postgres",
            "timeout": 30000
          }
        ]
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "sqlfluff lint migrations/ --dialect postgres",
        "timeout": 60000
      }
    ]
  }
}
```

### 5.2 Git Hooks

```yaml
# lefthook.yml
pre-commit:
  commands:
    sql-format:
      glob: "*.sql"
      run: sqlfluff lint {staged_files} --dialect postgres

    dangerous-sql:
      glob: "migrations/*.sql"
      run: |
        if grep -iE "DROP\s+(TABLE|DATABASE|SCHEMA)|TRUNCATE" {staged_files}; then
          echo "⚠️ Dangerous SQL detected - requires manual review"
          exit 1
        fi

pre-push:
  commands:
    migration-check:
      run: |
        # Check migration file naming convention
        for file in migrations/*.sql; do
          if [[ ! "$file" =~ ^migrations/[0-9]{14}_[a-z_]+\.sql$ ]]; then
            echo "❌ Invalid migration filename: $file"
            exit 1
          fi
        done
```

---

## 6. PR Quality Gate Templates

### 6.1 Universal PR Checklist

```markdown
## PR Checklist

### Code Quality
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] No new warnings introduced

### Testing
- [ ] Unit tests added/updated
- [ ] Integration tests passing
- [ ] Test coverage ≥ 80%
- [ ] Manual testing completed

### Security
- [ ] No hardcoded secrets
- [ ] Input validation implemented
- [ ] Authentication/authorization verified
- [ ] No SQL injection / XSS vulnerabilities

### Documentation
- [ ] README updated if needed
- [ ] API documentation updated
- [ ] Changelog updated

### Database (if applicable)
- [ ] Migrations reversible
- [ ] Indexes added for new columns
- [ ] Foreign keys properly indexed
```

### 6.2 GitHub PR Template

```yaml
# .github/pull_request_template.md
---
name: Pull Request
about: Submit a pull request
---

## Description
[Describe the changes]

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Refactoring

## Quality Gates
<!-- These are automatically checked by CI -->
- [ ] Lint passing
- [ ] Tests passing (≥80% coverage)
- [ ] Security scan clean
- [ ] Build successful

## Checklist
- [ ] I have performed a self-review
- [ ] I have added tests
- [ ] I have updated documentation

## Screenshots (if applicable)
[Add screenshots]
```

---

## 7. Quick Setup Commands

### One-Click Setup Script

```bash
#!/bin/bash
# setup-quality-gates.sh - Auto-configure quality gates based on project type

set -e

detect_language() {
    if [ -f "package.json" ]; then echo "node"
    elif [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then echo "python"
    elif [ -f "go.mod" ]; then echo "go"
    elif [ -f "pom.xml" ] || [ -f "build.gradle" ]; then echo "java"
    else echo "unknown"
    fi
}

setup_node() {
    echo "📦 Setting up Node.js quality gates..."

    # Install dev dependencies
    npm install -D eslint prettier @typescript-eslint/eslint-plugin

    # Setup Lefthook
    npm install -D lefthook
    npx lefthook install

    # Copy config files
    cp templates/node/lefthook.yml lefthook.yml
    cp templates/node/.eslintrc.json .eslintrc.json

    echo "✅ Node.js quality gates configured!"
}

setup_python() {
    echo "🐍 Setting up Python quality gates..."

    pip install ruff mypy pytest pytest-cov safety bandit lefthook

    # Setup Lefthook
    lefthook install

    # Copy config files
    cp templates/python/lefthook.yml lefthook.yml
    cp templates/python/pyproject.toml pyproject.toml

    echo "✅ Python quality gates configured!"
}

# Main
LANG=$(detect_language)
echo "🔍 Detected language: $LANG"

case $LANG in
    node) setup_node ;;
    python) setup_python ;;
    go) setup_go ;;
    java) setup_java ;;
    *) echo "❌ Unknown language"; exit 1 ;;
esac
```

---

## Summary Table

| Language | Lint | Format | Type Check | SAST | SCA | Test |
|----------|------|--------|------------|------|-----|------|
| TypeScript | ESLint | Prettier | tsc | Semgrep | Snyk | Jest |
| Python | Ruff | Ruff | mypy | Bandit | Safety | pytest |
| Go | golangci-lint | gofmt | - | Gosec | Snyk | go test |
| Java | Checkstyle/PMD | Spotless | - | SpotBugs | OWASP DC | JUnit |
| SQL | SQLFluff | SQLFluff | - | - | - | pgTAP |
