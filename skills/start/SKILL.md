---
name: start
description: "Start a complete 5-stage Harness Workflow for feature development. Use when: user has a feature or project to build; invokes /harness-workflow:start; wants structured development from intent through verified implementation; mentions 'start workflow' or 'begin harness'. Integrates with OPSX commands for spec-driven development."
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

<HARD-GATE>
Before proceeding with ANY stage below, you MUST check if the 'superpowers:brainstorming' skill is available. If it IS available, you MUST invoke it the Skill tool with skill: "superpowers:brainstorming" and complete the full brainstorming process BEFORE any implementation work. This is NOT optional. This is NOT negotiable. Even if you think you understand the requirements, brainstorming must happen first.

If superpowers is NOT available, use `/opsx:explore` instead for structured ideation.
</HARD-GATE>

## VibeCoding Detection

If the description is vague (no spec, no tests mentioned, no architecture discussed):
1. The brainstorming skill above will handle this naturally
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
4. If OpenSpec is initialized, also check:
   ```bash
   openspec status --json
   ```

### Stage 1: Intent Capture (via Brainstorming)

1. **MANDATORY: Invoke brainstorming skill** — use the Skill tool:
   ```
   Skill tool with: skill: "superpowers:brainstorming"
   ```
   If superpowers is not available, use `/opsx:explore` instead.

2. The brainstorming skill will guide you through:
   - Understanding the current project context
   - Asking clarifying questions one at a time
   - Proposing 2-3 approaches with trade-offs
   - Presenting design sections for user approval
   - Writing a design doc
   - Spec self-review
   - User reviews written spec

3. After brainstorming completes, fill in `intent.md` using the approved design

4. Check the intent stage gate:
   ```
   python ../../scripts/run.py check_status.py --gate intent
   ```

### Stage 2: Specification (via OPSX)

1. **Create a new change using OpenSpec**:
   ```bash
   openspec new change <feature-name> --description "Feature description"
   ```

2. **Generate planning artifacts** using OPSX commands:

   **Quick path** (generate all at once):
   ```bash
   /opsx:propose
   ```

   **Or incremental path** (one artifact at a time):
   ```bash
   /opsx:continue    # Creates next artifact based on dependency graph
   /opsx:continue    # Repeat until all planning artifacts are done
   ```

   **Or fast-forward** (all planning artifacts at once):
   ```bash
   /opsx:ff <feature-name>
   ```

3. **Check artifact status**:
   ```bash
   openspec status --change <feature-name> --json
   ```

4. **Validate artifacts**:
   ```bash
   openspec validate --changes --strict --json
   ```

5. Fallback (no OpenSpec CLI) — fill templates manually in `openspec/changes/<feature>/`:
   - `proposal.md` - The "why" (problem, goals, success criteria)
   - `design.md` - The "how" (architecture, components, data model)
   - `tasks.md` - The execution steps (phased task breakdown)

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

1. **Use `/opsx:apply`** to implement tasks:
   ```bash
   /opsx:apply <feature-name>
   ```

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

5. **Verify implementation** using OPSX:
   ```bash
   openspec validate --all --strict --json
   ```
   Plus harness verification:
   ```
   python ../../scripts/run.py verify_specs.py --strict --report
   python ../../scripts/run.py entropy_scan.py
   ```

6. Update `.harness/state.json` stage "execute" to "complete"

7. **Archive the change**:
   ```bash
   /opsx:archive
   ```

## Progress Tracking

After each stage, check status:
```bash
# Harness status
python ../../scripts/run.py check_status.py

# OpenSpec status
openspec status --json

# Or use the combined command
/harness-workflow:status
```

## Quality Gates

Each stage must pass quality gates before proceeding:
- Stage 1: `check_status.py --gate intent` passes + brainstorming completed
- Stage 2: `openspec validate --changes --strict` passes
- Stage 3: Plan has task breakdown with dependencies and assignments
- Stage 4: Harness has agent config and quality gates configured
- Stage 5: `build_verify.py` exits 0, `openspec validate --all` passes, entropy scan clean

## Doom Loop Recovery

If `build_verify.py` exits with code 2 (doom loop):
1. Read the error output carefully
2. Check doom loop status: `python ../../scripts/run.py doom_loop.py --status`
3. Consider: different approach, simpler fix, or ask user for guidance
4. Reset history if starting fresh: `python ../../scripts/run.py doom_loop.py --reset`
