---
name: verify
description: "Verify implementation against OpenSpec specifications with build-verify loop and entropy scan. Use when: user wants final verification; invokes /harness-workflow:verify; code writing is done and needs final check; wants to validate specs match implementation. Runs spec validation, build-verify, and entropy scan."
---

# /harness-workflow:verify - Verify Implementation Against Specs

Verify that the implementation matches the OpenSpec specifications.

## Usage

```bash
/harness-workflow:verify
```

## What It Does

Runs multiple verification scripts:

1. **OpenSpec CLI validation** (if available):
   ```
   openspec validate --all --json
   ```

2. **Spec verification** - validates structure, content depth, file references:
   ```
   python ../../scripts/run.py verify_specs.py --strict --report
   ```

3. **Build-verify loop** - runs lint, typecheck, test:
   ```
   python ../../scripts/run.py build_verify.py --loop tight
   ```

4. **Entropy scan** - checks for dead code, style drift, stale docs:
   ```
   python ../../scripts/run.py entropy_scan.py
   ```

## Options (verify_specs.py)

| Option | Description |
|--------|-------------|
| `--strict` | Fail on any deviation (missing sections or files) |
| `--report` | Save report to `.harness/verification-report.md` |
| `--project-dir DIR` | Specify project directory (default: current) |
| `--json` | Output as JSON |

## Options (build_verify.py)

| Option | Description |
|--------|-------------|
| `--loop tight\|loose` | tight = lint+typecheck+unit, loose = +e2e |
| `--max-iterations N` | Max retry iterations (default: 3) |
| `--json` | Output as JSON |

## Options (entropy_scan.py)

| Option | Description |
|--------|-------------|
| `--fix` | Auto-fix safely fixable issues (unused imports) |
| `--json` | Output as JSON |

## Claude Instructions

When this command is invoked:

1. Run all verification steps:
   ```
   python ../../scripts/run.py verify_specs.py --strict --report
   python ../../scripts/run.py build_verify.py --loop tight
   python ../../scripts/run.py entropy_scan.py
   ```

2. Read the output and report results to the user

3. If issues are found:
   - Missing required sections: guide user to add them to the spec
   - Build failures: read error output, implement fixes, re-run build_verify
   - Doom loop (exit code 2): recommend human intervention or alternative approach
   - High entropy: list issues and optionally run `--fix`

4. If all pass: confirm implementation matches specification

## Verification Checks

### Spec Structure Validation (content-aware)
- **Proposal**: requires Problem, Goals, Success Criteria sections (50+ chars each)
- **Design**: requires Architecture, Components sections (100+ chars each)
- **Tasks**: requires Phase section + at least one task item (`- [ ]` or `- [x]`)

### File Reference Checking
- Extracts file paths from specs recursively
- Verifies each referenced file exists in the codebase

### Design Cross-Reference
- Extracts component names from design spec
- Searches codebase for matching source files

### Delta Spec Validation
- Checks ADDED/MODIFIED/REMOVED sections for compliance
- MODIFIED sections need "(Previously: ...)" notation
- REMOVED sections need a reason

## Exit Codes

- `0` - All checks pass
- `1` - Verification failures
- `2` - Doom loop detected (build_verify.py only)
