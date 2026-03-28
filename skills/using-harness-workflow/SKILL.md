---
name: using-harness-workflow
description: Use when starting any conversation - establishes how to find and use harness-workflow skills for specification-driven development
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this skill.
</SUBAGENT-STOP>

You have the **harness-workflow** plugin installed. It provides specification-driven development with 5 stages: Intent, Specification, Planning, Harness (agent orchestration), and Execute & Verify.

## Available Commands

| Command | Purpose |
|---------|---------|
| `/harness-workflow:init` | Initialize a project with Harness Workflow structure |
| `/harness-workflow:start` | Start a complete 5-stage development workflow |
| `/harness-workflow:status` | Check current workflow state with content validation |
| `/harness-workflow:verify` | Verify implementation against OpenSpec specifications |

## Available Skills

These skills are auto-triggered by context but can also be invoked explicitly via the Skill tool:

- **harness-workflow:init** - Initialize project with `.harness/` state, OpenSpec structure, and optional hooks
- **harness-workflow:start** - Full 5-stage workflow from intent capture through verified implementation
- **harness-workflow:status** - Content-aware status checking with stage gate validation
- **harness-workflow:verify** - Multi-layer verification: spec validation, build-verify loop, entropy scan

## When to Use

- **Starting a new feature/project** → `/harness-workflow:init` then `/harness-workflow:start`
- **Checking progress** → `/harness-workflow:status`
- **Final verification** → `/harness-workflow:verify`
- **User mentions "harness", "workflow", "openspec"** → invoke the relevant skill

## Quality Gates

The workflow enforces quality gates at each stage:
1. **Intent gate**: intent.md has Problem + Success Criteria
2. **Spec gate**: proposal, design, tasks have required sections
3. **Plan gate**: task breakdown with dependencies
4. **Execute gate**: build-verify passes, spec verification passes, entropy clean

## Integration with Other Plugins

harness-workflow works well with superpowers skills:
- Use `superpowers:brainstorming` for structured ideation during Intent stage
- Use `superpowers:verification-before-completion` before marking work done
- Use `superpowers:writing-plans` for creating implementation plans from specs
