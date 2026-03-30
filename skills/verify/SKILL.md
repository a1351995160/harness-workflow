---
name: verify
description: "Verify implementation against OpenSpec specifications with build-verify loop and entropy scan. Use when: user wants final verification; invokes /harness-workflow:verify; code writing is done and needs final check; wants to validate specs match implementation. Combines OpenSpec CLI validation with harness build-verify and entropy scan."
---

# /harness-workflow:verify - Verify Implementation Against Specs

Verify that the implementation matches the OpenSpec specifications.
Combines OpenSpec CLI validation with Harness build-verify and entropy scan.

## Usage

```bash
/harness-workflow:verify
```

## What It Does

Runs a layered verification pipeline:

### Layer 1: OpenSpec CLI Validation (Primary)

```bash
openspec validate --all --strict --json
```

This validates:
- All change proposals have required sections
- All specs have proper structure and content depth
- File references in specs point to existing files
- Delta specs comply with ADDED/MODIFIED/REMOVED format

Additional OpenSpec checks:
```bash
openspec status --json                    # Artifact completion status
openspec show <change-name> --json        # Detailed change view
openspec show <change-name> --deltas-only # Show only deltas
```

### Layer 2: Spec Verification (Harness)

Validates structure, content depth, and file references:

```bash
python ../../scripts/run.py verify_specs.py --strict --report
```

### Layer 3: Build-Verify Loop

Runs lint, typecheck, test in a retry loop:

```bash
python ../../scripts/run.py build_verify.py --loop tight
```

- Exit code 0: All checks passed, proceed
- Exit code 1: Checks failed, read output and fix
- Exit code 2: **Doom loop detected** — pause and ask user

### Layer 4: Entropy Scan

Checks for dead code, style drift, stale docs:

```bash
python ../../scripts/run.py entropy_scan.py
```

## Options

### verify_specs.py

| Option | Description |
|--------|-------------|
| `--strict` | Fail on any deviation (missing sections or files) |
| `--report` | Save report to `.harness/verification-report.md` |
| `--project-dir DIR` | Specify project directory (default: current) |
| `--json` | Output as JSON |

### build_verify.py

| Option | Description |
|--------|-------------|
| `--loop tight\|loose` | tight = lint+typecheck+unit, loose = +e2e |
| `--max-iterations N` | Max retry iterations (default: 3) |
| `--json` | Output as JSON |

### entropy_scan.py

| Option | Description |
|--------|-------------|
| `--fix` | Auto-fix safely fixable issues (unused imports) |
| `--json` | Output as JSON |

<HARD-GATE>
Before marking any verification as "passed" and any work as "done", you MUST invoke the 'superpowers:verification-before-completion' skill using the Skill tool with skill: "superpowers:verification-before-completion". This is NOT optional. This is NOT negotiable. Even if you think everything looks good, this verification step must happen.

If superpowers is NOT available, perform a manual final check:
- Re-read every changed file
- Trace the data flow from user input to output
- Verify error handling at every boundary
- Check for off-by-one errors, null handling, edge cases
</HARD-GATE>

## Claude Instructions

When this command is invoked:

1. **Check OpenSpec CLI availability**:
   ```bash
   openspec --version
   ```

2. **Run Layer 1 - OpenSpec validation** (if available):
   ```bash
   openspec validate --all --strict --json
   ```
   If issues: report specific validation failures and guide user to fix.

3. **Run Layer 2 - Spec verification**:
   ```bash
   python ../../scripts/run.py verify_specs.py --strict --report
   ```

4. **Run Layer 3 - Build-verify loop**:
   ```bash
   python ../../scripts/run.py build_verify.py --loop tight
   ```

5. **Run Layer 4 - Entropy scan**:
   ```bash
   python ../../scripts/run.py entropy_scan.py
   ```

6. **Run Layer 5 - Semantic verification**:
   ```bash
   python ../../scripts/run.py semantic_verify.py --report
   ```

7. **Run Layer 6 - E2E test verification**:
   ```bash
   python ../../scripts/run.py e2e_generate.py
   python ../../scripts/run.py e2e_runner.py --browser chromium
   ```

8. **Report combined results**:
   - OpenSpec validation: pass/fail with details
   - Spec verification: structural compliance
   - Build-verify: lint/typecheck/test results
   - Entropy: dead code, style drift, stale docs
   - Semantic: intent-level spec vs code compliance
   - E2E: generated test stubs and run results

9. **If issues are found**:
   - OpenSpec validation failures: guide user to update specs
   - Missing required sections: guide user to add them
   - Build failures: read error output, implement fixes, re-run
   - Doom loop (exit code 2): recommend human intervention
   - High entropy: list issues and optionally run `--fix`
   - Semantic gaps: list missing implementations by priority
   - E2E failures: capture screenshots, review test output

10. **If all pass**: confirm implementation matches specification
   - Suggest running `/opsx:archive` to archive the completed change

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

## References

- Read [entropy-management.md](../../references/entropy-management.md) when entropy scan reports high drift and you need to interpret or remediate specific findings
- Read [build-verify-loop.md](../../references/build-verify-loop.md) when build-verify loops fail repeatedly or doom loops are detected
- Read [layered-detection.md](../../references/layered-detection.md) for details on the multi-layer verification architecture and how each detection layer contributes to quality assurance

## OPSX Integration

After verification passes, the natural next step is:

```bash
/opsx:archive    # Archive the completed change
```

If verification reveals spec issues that need updating:
```bash
/opsx:continue   # Update the specific artifact that needs changes
```

## Exit Codes

- `0` - All checks pass
- `1` - Verification failures
- `2` - Doom loop detected (build_verify.py only)
