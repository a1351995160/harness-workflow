# Harness Engineering Philosophy

> If the AI is a powerful but unpredictable racehorse, the harness is the reins, saddle, and bit that channel that power. The human acts as rider — providing direction, not doing the running.

## Prompt Engineering vs Harness Engineering

| Dimension | Prompt Engineering | Harness Engineering |
|-----------|-------------------|-------------------|
| **Scope** | Single interaction | Entire agent system |
| **Control** | Suggestions | Mechanical enforcement (linters, tests, CI) |
| **Reliability** | What AI *knows* | What AI *can do* and how it *recovers* |
| **Feedback** | One-shot | Continuous build-verify loops |

**Systemic fix rule**: When an agent makes a mistake, design a mechanical solution so it never repeats it.

---

## The 5-Layer Architecture

```
+-------------------------------------------------------------+
|                    HARNESS WORKFLOW ARCHITECTURE              |
+-------------------------------------------------------------+
|  Layer 5: EXECUTION        -> Build-Verify loops, self-healing|
|  Layer 4: HARNESS          -> Agent orchestration & constraints|
|  Layer 3: PLAN             -> Task breakdown & sequencing     |
|  Layer 2: SPEC             -> Formalized requirements (OpenSpec)|
|  Layer 1: INTENT           -> User goals (brainstorm/propose) |
+-------------------------------------------------------------+
```

---

## The 4 Pillars of a Harness

### Pillar 1: Context Engineering
Context window is a **scarce resource** — actively curate to prevent "context rot".
- **Repository as System of Record**: All decisions version-controlled and machine-readable. Agent cannot act on knowledge in Slack threads or human heads.
- **Progressive Disclosure**: Short AGENTS.md as TOC, load details on demand.
- **Sub-Agent Context Firewall**: Delegate heavy tasks to isolated sub-agents. They return only condensed summaries.
- **Compaction & Memory**: Dynamically summarize past interactions; persist state across sessions.

### Pillar 2: Architectural Constraints
**Constraining the solution space makes agents more productive.** Instead of prompting "write good code," mechanically enforce what good code looks like.
- Fixed dependency layers with custom linters
- Structural tests that reject non-compliant code
- **Self-Repair Loops**: Linter failures inject correction instructions back into agent context

### Pillar 3: Tools and Environments
- **Sandboxes**: Isolated execution (Docker, cloud sandboxes) with observability
- **Agent Legibility**: Agents can boot the app, drive the UI, observe runtime events (requires runtime infrastructure)
- **Human-in-the-Loop (HITL)**: For destructive/sensitive actions, pause until human approves

### Pillar 4: Feedback Loops
- **Build-Verify Loop**: `build_verify.py` runs lint -> typecheck -> test iteratively
- **Back-Pressure**: Force agent to face test suites, typechecks before marking complete
- **Entropy Management**: `entropy_scan.py` scans for AI slop (dead code, style drift, stale docs)
