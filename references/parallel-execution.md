# Parallel Agent Execution

> How Harness Workflow dispatches multiple agents in parallel for faster execution.

## Architecture

```
tasks.md
    │
    ▼
parallel_execute.py ──► Execution Plan (batches)
    │
    ▼
Claude Code reads plan ──► Launches Agent tool calls
    │                         │
    │                    ┌────┼────┐
    │                    ▼    ▼    ▼
    │                 Agent  Agent  Agent  (parallel in one message)
    │                    │    │    │
    │                    └────┼────┘
    │                         │
    ▼                         ▼
build-verify.py ◄───── Batch complete, check gates
    │
    ▼
Next batch...
```

## How It Works

### 1. Task Parsing

`parallel_execute.py` reads `tasks.md` from `openspec/changes/<feature>/` and extracts:
- Task ID and description
- Completion status (`[x]` vs `[ ]`)
- Dependencies (from `T2 → T1` or `depends on T1` patterns)
- Agent assignment (inferred from task description keywords)

### 2. Batch Resolution (Topological Sort)

Tasks are grouped into execution batches:
- **Batch 1**: Tasks with no dependencies (can all run in parallel)
- **Batch 2**: Tasks that depend on Batch 1
- **Batch N**: Tasks that depend on Batch N-1
- Maximum `max_parallel` tasks per batch (default: 3)

### 3. Agent Dispatch

Each task is assigned to an agent type based on keyword matching:

| Keyword Pattern | Agent | Model |
|----------------|-------|-------|
| security, auth, vulnerability | security-reviewer | sonnet |
| test, spec, coverage, mock | test-engineer | sonnet |
| review, check, audit | code-reviewer | opus |
| implement, create, build | executor | sonnet |
| design, architecture | architect | opus |
| debug, error, bug, fix | debugger | sonnet |
| verify, complete, done | verifier | sonnet |
| plan, breakdown | planner | opus |
| document, readme | writer | haiku |

### 4. Claude Code Execution

Claude Code reads the execution plan and dispatches agents:

```
# Batch 1 (PARALLEL): Launch all 3 in one message
Agent(description="Implement notification model", subagent_type="oh-my-claudecode:executor", ...)
Agent(description="Write notification tests", subagent_type="oh-my-claudecode:test-engineer", ...)
Agent(description="Review notification design", subagent_type="oh-my-claudecode:architect", ...)

# Wait for all 3 to complete, then run build-verify
# ...

# Batch 2 (SEQUENTIAL): Run one at a time
Agent(description="Review notification code", subagent_type="oh-my-claudecode:code-reviewer", ...)
```

## CLI Usage

```bash
# Auto-discover tasks from openspec/
python run.py parallel_execute.py

# Read from specific plan file
python run.py parallel_execute.py --plan-file plan.md

# Adjust parallelism
python run.py parallel_execute.py --max-parallel 5

# Dry run (just show plan)
python run.py parallel_execute.py --dry-run --json
```

## Parallel Groups

Some agent types are designed to run in parallel:

| Group | Agents | Why parallel |
|-------|--------|-------------|
| tdd_cycle | tester + architect | Tests and interface review are independent |
| review_triple | reviewer + security + verifier | Three review perspectives, no conflicts |
| docs_parallel | writer + gc-agent | Documentation and cleanup are independent |

## Dependency Rules

```
executor ──► tester (tests depend on implementation)
executor ──► reviewer (review depends on implementation)
executor ──► security (security review depends on implementation)
executor ──► verifier (verification depends on implementation)
executor + tester ──► verifier (needs both code and tests)
executor ──► writer (docs depend on implementation)
```

## Integration with start/SKILL.md

Stage 4 (Harness) uses `parallel_execute.py` to plan execution:

1. After agent pool is configured, run `parallel_execute.py --dry-run`
2. Show execution plan to user for approval
3. In Stage 5, execute batches:
   - For each PARALLEL batch: launch multiple Agent tool calls in one message
   - For each SEQUENTIAL batch: run one agent at a time
   - Run `build_verify.py --loop tight` between batches
   - If doom loop detected, pause and notify user
