# Build-Verify Loop (Ralph Wiggum Loop)

> Self-verification loop pattern — core practice from the OpenAI zero-human-code project

## Executable Script: build_verify.py

The skill provides `scripts/build_verify.py` as the core enforcement engine:

```bash
python scripts/run.py build_verify.py --loop tight              # lint + typecheck + unit tests
python scripts/run.py build_verify.py --loop loose              # + e2e tests
python scripts/run.py build_verify.py --max-iterations 5        # custom iteration cap
python scripts/run.py build_verify.py --json                    # structured JSON output
python scripts/run.py build_verify.py --project-dir /path       # target project
```

**Exit codes**:

| Code | Meaning | Agent Action |
|------|---------|-------------|
| 0 | All checks passed | Proceed to next stage |
| 1 | Checks failed | Read errors, fix code, re-run |
| 2 | Doom loop detected | Escalate to human |

**Tight loop** (default): lint -> typecheck -> unit tests (fast, sub-minute)
**Loose loop**: lint -> typecheck -> unit tests -> e2e tests (thorough)

**Config integration**: Automatically reads `.harness/config.yaml` via `load_harness_config()` to override auto-detected build commands.

**Doom loop detection**: Delegates to `doom_loop.py` — if same error hash repeats 3+ consecutive times, exits with code 2.

**JSON output structure**:
```json
{
  "status": "passed|failed|doom_loop",
  "iteration": 2,
  "timestamp": "2026-03-28T08:30:00+00:00",
  "checks": {
    "lint": {"success": true, "returncode": 0},
    "typecheck": {"success": true, "returncode": 0},
    "test": {"success": true, "returncode": 0}
  }
}
```

## Core Concept

The agent is placed in an iterative execution loop: write code, run tests, read errors, iterate and fix, until all tests pass. This pattern is named after the way agents in the OpenAI project self-review and iterate.

```
┌─────────────────────────────────────────────────────────────┐
│                  BUILD-VERIFY LOOP                           │
│                                                              │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│   │  WRITE   │───▶│  BUILD   │───▶│  TEST    │             │
│   │  CODE    │    │  & RUN   │    │  SUITE   │             │
│   └──────────┘    └──────────┘    └────┬─────┘             │
│       ▲                               │                     │
│       │         ┌──────────┐          │                     │
│       │         │  READ    │◀─────────┤                     │
│       └─────────│  ERRORS  │    FAIL  │                     │
│           FIX   └──────────┘          │                     │
│                                       ▼                     │
│                                 ┌──────────┐               │
│                                 │  PASS ✓  │               │
│                                 │  EXIT    │               │
│                                 └──────────┘               │
└─────────────────────────────────────────────────────────────┘
```

## Context-Efficient Verification

This is the key optimization of the Build-Verify Loop:

| Test Result | Context Behavior | Reason |
|-------------|-----------------|--------|
| **Pass** | Completely silent — no output injected | Success messages waste context tokens |
| **Fail** | Only inject error logs and exit code | Keep only the minimum info needed for fixing |

```
❌ Traditional approach (wastes context):
  ✅ test_user_auth ... ok
  ✅ test_login_flow ... ok
  ✅ test_token_refresh ... ok     ← 3 lines of useless success output
  ❌ test_password_reset ... FAIL
     Expected 200, got 404

✅ Context-Efficient approach:
  FAIL: test_password_reset
  Expected 200, got 404
  at src/auth/handler.ts:42       ← Only failure info
```

## Tight Loop vs Loose Loop

### Tight Loop
- **Best for**: Unit tests, linting, type checking
- **Characteristics**: Second-level feedback, can iterate 10+ times quickly
- **Context cost**: Low (only error info per iteration)
- **Configuration**:
```yaml
build_verify:
  tight_loop:
    max_iterations: 15
    timeout_per_iteration: 30    # seconds
    commands:
      - "npm run lint"
      - "npm run typecheck"
      - "npm run test:unit"
    context_efficient: true      # silent on success
```

### Loose Loop
- **Best for**: E2E tests, integration tests, security scans
- **Characteristics**: Minute-level feedback, fewer iterations
- **Context cost**: Medium (more diagnostic info needed)
- **Configuration**:
```yaml
build_verify:
  loose_loop:
    max_iterations: 5
    timeout_per_iteration: 300   # seconds
    commands:
      - "npm run test:e2e"
      - "npm run test:integration"
    context_efficient: true
    on_failure:
      include_screenshot: true   # Screenshot on E2E failure
      include_logs: true         # Include server logs
```

## Best Practices

1. **Run fast checks first, slow checks last** — lint/typecheck → unit tests → e2e
2. **Limit iteration count** — pause when max iterations exceeded, request human intervention
3. **Keep error messages concise** — only retain errors related to the failed test, not full output
4. **Use filesystem for staging** — write intermediate results to files, don't keep everything in context
5. **Doom Loop detection** — if the same error repeats for 3 consecutive iterations, flag for human attention

## Configuration Example

```yaml
# .harness/config.yaml
build_verify_loop:
  enabled: true
  context_efficient: true

  stages:
    - name: lint
      command: "npm run lint"
      type: tight
      max_iterations: 10

    - name: unit_test
      command: "npm run test:unit"
      type: tight
      max_iterations: 10

    - name: integration_test
      command: "npm run test:integration"
      type: loose
      max_iterations: 5

    - name: e2e_test
      command: "npm run test:e2e"
      type: loose
      max_iterations: 3

  doom_loop_detection:
    enabled: true
    same_error_threshold: 3    # Consecutive same-error count
    action: "pause_and_notify" # or "auto_escalate"
```

## Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|-------------|---------|-----------------|
| Running all tests at once | One failure requires re-running everything | Layer execution: fast first, slow last |
| Keeping all output in context | Wastes context tokens | Context-Efficient: silent on success |
| Infinite iteration | Agent gets stuck in a loop | Set max_iterations |
| Only looking at the last error line | May miss root cause | Provide structured error summary |
