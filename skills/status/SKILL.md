---
name: status
description: "Check the current state of a Harness Workflow with content validation. Use when: user wants to know workflow progress; invokes /harness-workflow:status; asks 'what stage am I at' or 'workflow status'; wants to check if a stage gate passes. Combines OpenSpec CLI status with harness state validation."
---

# /harness-workflow:status - Check Workflow Status

Display the current state of an active Harness Workflow with content validation.
Combines OpenSpec CLI status with Harness state tracking.

## Usage

```bash
/harness-workflow:status
```

## What It Does

### Primary: OpenSpec CLI Status

If OpenSpec CLI is installed:

```bash
openspec status --json
```

This shows:
- Active changes and their artifact completion status
- Artifact dependency graph state (BLOCKED / READY / DONE)
- Which artifacts are ready to create next

List all changes and specs:
```bash
openspec list --json         # List changes
openspec list --specs --json # List specs
```

### Secondary: Harness State

```bash
python ../../scripts/run.py check_status.py [options]
```

This provides:
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

1. **Check OpenSpec CLI availability**:
   ```bash
   openspec --version
   ```

2. **If OpenSpec is initialized**, run:
   ```bash
   openspec status --json
   openspec list --json
   ```
   This shows artifact-level status for all active changes.

3. **Run harness status**:
   ```bash
   python ../../scripts/run.py check_status.py
   ```

4. **For machine-readable output**:
   ```bash
   python ../../scripts/run.py check_status.py --json
   ```

5. **To check a specific stage gate**:
   ```bash
   python ../../scripts/run.py check_status.py --gate spec
   ```
   - Exit code 0: Gate passes
   - Exit code 1: Gate blocked (reasons listed)

6. **Report the combined findings** to the user:
   - OpenSpec change status (which artifacts are done/ready/blocked)
   - Harness stage progress (which stages are complete/in progress/pending)
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

## OPSX Integration

Status also shows which OPSX commands are available for the next step:

| Current State | Recommended Next Command |
|---------------|------------------------|
| No change created | `/opsx:explore` or `/opsx:propose` |
| Proposal done, specs blocked | `/opsx:continue` to create specs |
| All planning done | `/opsx:apply` to implement |
| Implementation done | `/harness-workflow:verify` then `/opsx:archive` |

## Example Output

```
============================================================
Harness Workflow Status
============================================================
Project: /path/to/project
Language: python
Framework: fastapi
Current stage: spec

OpenSpec Changes:
  add-auth (active):
    proposal: DONE
    specs: READY (ready to create)
    design: BLOCKED (needs: specs)
    tasks: BLOCKED (needs: specs, design)

Harness Stages:
  intent: COMPLETE
  spec: IN PROGRESS
    [-] proposal.md: exists, valid
    [-] design.md: missing
    [-] tasks.md: missing
  plan: PENDING
  harness: PENDING
  execute: PENDING

Next: Run /opsx:continue to create specs for add-auth
```

## Exit Codes

- `0` - Always for standard status (informational)
- `0/1` - For `--gate` mode (0 = passes, 1 = blocked)
