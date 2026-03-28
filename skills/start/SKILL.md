---
name: start
description: "Start a complete 5-stage Harness Workflow for feature development. Use when: user has a feature or project to build; invokes /harness-workflow:start with a description; wants structured development from intent through verified implementation; mentions 'start workflow' or 'begin harness'. Handles VibeCoding (vague requests) and structured requests alike."
---

# /harness-workflow:start - Start Complete Development Workflow

Start a new feature or project using the full 5-layer Harness Workflow.
Works for both structured requests and VibeCoding (vague "build me X" requests).

## Usage

```bash
/harness-workflow:start "Feature description"
```

## Parameters

- `description` (required): Natural language description of what you want to build

## VibeCoding Detection

If the description is vague (no spec, no tests mentioned, no architecture discussed):
1. Invoke `superpowers:brainstorming` Skill tool to explore the idea
2. Use brainstorming results to fill `intent.md`
3. Continue with standard workflow below

## Claude Instructions

When this command is invoked, follow these stages:

### Stage 0: Initialization Check

1. Check if `.harness/state.json` exists in the project
2. If not initialized, run:
   ```
   python ../../scripts/run.py init_harness.py . --feature <feature-name>
   ```
3. Read state to determine current progress:
   ```
   python ../../scripts/run.py check_status.py --json
   ```

### Stage 1: Intent Capture

1. **Invoke `superpowers:brainstorming` Skill** for structured ideation:
   ```
   Use Skill tool with: skill: "superpowers:brainstorming"
   ```
2. Ask about: problem being solved, stakeholders, success criteria, constraints
3. Fill in `intent.md` using `../../templates/intent.md` as the guide
4. Check the intent stage gate:
   ```
   python ../../scripts/run.py check_status.py --gate intent
   ```

### Stage 2: Specification

1. Check the spec stage gate:
   ```
   python ../../scripts/run.py check_status.py --gate spec
   ```
2. Create OpenSpec documents from the intent:

   **If OpenSpec CLI is available:**
   - Use `openspec` commands to create proposal, design, and tasks

   **Fallback (no OpenSpec CLI):**
   - Fill templates in `openspec/changes/<feature>/`
   - `proposal.md` - The "why" (problem, goals, success criteria)
   - `design.md` - The "how" (architecture, components, data model)
   - `tasks.md` - The execution steps (phased task breakdown)

3. Verify the gate passes:
   ```
   python ../../scripts/run.py check_status.py --gate spec
   ```

### Stage 3: Planning

1. Parse the task list from `tasks.md`
2. Build a dependency graph from task dependencies
3. Identify parallel execution opportunities
4. Assign tasks to appropriate agents from `../../agents/harness-agents.yaml`
5. Update `.harness/state.json` stage "plan" to "complete"

### Stage 4: Harness (Agent Orchestration)

1. Configure agent pool based on plan
2. Set up quality gates per `../../config/harness-config.yaml`
3. Prepare context engineering (progressive disclosure)
4. Initialize build-verify feedback loops
5. Update `.harness/state.json` stage "harness" to "in_progress"

### Stage 5: Execute & Verify

1. Run implementation agents in optimal order
2. Execute build-verify loops after each task:
   ```
   python ../../scripts/run.py build_verify.py --loop tight --max-iterations 3
   ```
   - Exit code 0: All checks passed, proceed
   - Exit code 1: Checks failed, read output and fix
   - Exit code 2: **Doom loop detected** — pause and ask user for guidance

3. Run code review and security review

4. **Invoke `superpowers:verification-before-completion` Skill** before marking done:
   ```
   Use Skill tool with: skill: "superpowers:verification-before-completion"
   ```
   This ensures all acceptance criteria are met before closing out.

5. Verify against OpenSpec specs:
   ```
   python ../../scripts/run.py verify_specs.py --strict --report
   ```
6. Run entropy scan before commit:
   ```
   python ../../scripts/run.py entropy_scan.py
   ```
7. Update `.harness/state.json` stage "execute" to "complete"

## Progress Tracking

After each stage, check status:
```
python ../../scripts/run.py check_status.py
```

## Quality Gates

Each stage must pass quality gates before proceeding:
- Stage 1: `check_status.py --gate intent` passes (intent.md has Problem + Success Criteria)
- Stage 2: `check_status.py --gate spec` passes (proposal, design, tasks have required sections)
- Stage 3: Plan has task breakdown with dependencies and assignments
- Stage 4: Harness has agent config and quality gates configured
- Stage 5: `build_verify.py` exits 0, `verify_specs.py --strict` passes, entropy scan clean

## Doom Loop Recovery

If `build_verify.py` exits with code 2 (doom loop):
1. Read the error output carefully
2. Check doom loop status: `python ../../scripts/run.py doom_loop.py --status`
3. Consider: different approach, simpler fix, or ask user for guidance
4. Reset history if starting fresh: `python ../../scripts/run.py doom_loop.py --reset`
