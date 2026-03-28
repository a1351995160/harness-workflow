---
name: status
description: "Check the current state of a Harness Workflow with content validation. Use when: user wants to know workflow progress; invokes /harness-workflow:status; asks 'what stage am I at' or 'workflow status'; wants to check if a stage gate passes. Validates artifact content, not just file existence."
---

# /harness-workflow:status - Check Workflow Status

Display the current state of an active Harness Workflow with content validation.

## Usage

```bash
/harness-workflow:status
```

## What It Does

Runs `python ../../scripts/run.py check_status.py [options]` which:

1. **Reads `.harness/state.json`** to get workflow state
2. **Validates artifact content** - checks required sections with minimum content
3. **Determines stage progress** - cross-references state with validated artifacts
4. **Reports current stage** and next action
5. **Checks stage gates** - enforces quality requirements per stage

## Options

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON for scripting |
| `--project-dir DIR` | Specify project directory (default: current) |
| `--gate <stage>` | Check if a stage gate passes (exit 0/1) |

### Stage Gate Stages

| Stage | Requires |
|-------|----------|
| `intent` | intent.md with Problem + Success Criteria sections (50+ chars) |
| `spec` | proposal.md (Goals), design.md (Architecture), tasks.md (Phase + task items) |
| `plan` | state.json stages.plan = "complete" |
| `harness` | state.json stages.harness = "complete" |
| `execute` | state.json stages.execute = "complete" |

## Claude Instructions

When this command is invoked:

1. Run the status script:
   ```
   python ../../scripts/run.py check_status.py
   ```

2. For machine-readable output:
   ```
   python ../../scripts/run.py check_status.py --json
   ```

3. To check a specific stage gate:
   ```
   python ../../scripts/run.py check_status.py --gate spec
   ```
   - Exit code 0: Gate passes
   - Exit code 1: Gate blocked (reasons listed)

4. Report the findings to the user:
   - Which stages are complete, in progress, or pending
   - Which artifacts have valid content vs. are missing sections
   - What the recommended next action is

## Content Validation

Unlike checking only file existence, status validates content:

| Artifact | Required Sections | Min Content |
|----------|------------------|-------------|
| `intent.md` | Problem, Success Criteria | 50 chars |
| `proposal.md` | Goals, Constraints | 50 chars |
| `design.md` | Architecture, Components | 100 chars |
| `tasks.md` | Phase + task items | 50 chars |

## OpenSpec CLI Integration

If OpenSpec CLI is installed, status will also show `openspec status` output.

## Example Output

```
============================================================
Harness Workflow Status
============================================================
Project: /path/to/project
Language: python
Framework: fastapi
Current stage: spec

Stages:
  intent: INCOMPLETE
    [-] intent.md: exists
        Missing required section: 'Success Criteria'
  spec: INCOMPLETE
    [-] proposal.md: missing
    [-] design.md: missing
    [-] tasks.md: missing
  plan: PENDING
  harness: PENDING
  execute: PENDING

Next: Edit intent.md with your project goals and success criteria
```

## Exit Codes

- `0` - Always for standard status (informational)
- `0/1` - For `--gate` mode (0 = passes, 1 = blocked)
