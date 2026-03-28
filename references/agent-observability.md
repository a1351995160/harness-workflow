# Agent Observability

> Because AI Agents exhibit non-deterministic behavior, traditional application monitoring is insufficient — specialized Agent observability is required

## Table of Contents

- [Three Pillars](#three-pillars)
- [Distributed Tracing](#1-distributed-tracing)
- [Token Usage Analytics](#2-token-usage-analytics)
- [Continuous Evaluation](#3-continuous-evaluation)
- [Alerting Rules](#alerting-rules)
- [Configuration Overview](#configuration-overview)

## Three Pillars

```
┌─────────────────────────────────────────────────────────────┐
│              AGENT OBSERVABILITY PILLARS                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   DISTRIBUTED   │  │   TOKEN USAGE   │  │ CONTINUOUS  │ │
│  │    TRACING      │  │   ANALYTICS     │  │ EVALUATION  │ │
│  │                 │  │                 │  │             │ │
│  │ • Execution     │  │ • Per-request   │  │ • Pre-deploy│ │
│  │   flow tracing  │  │   tracking      │  │   simulation│ │
│  │ • Parent-child  │  │ • Cumulative    │  │ • CI        │ │
│  │   spans         │  │   usage         │  │   evaluation│ │
│  │ • Input/output  │  │ • Cost          │  │ • Human     │ │
│  │   storage       │  │   allocation    │  │   calibration│ │
│  │ • Replay        │  │ • Doom Loop    │  │ • Scenario  │ │
│  │   capability    │  │   detection     │  │   testing   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 1. Distributed Tracing

### What to Trace

Every Agent execution must record:

| Trace Item | Description | Example |
|------------|-------------|---------|
| **LLM Reasoning Steps** | Input/output for each model call | prompt -> response pairs |
| **Tool Calls** | External API/tool invocations | `db.query("SELECT...")` |
| **RAG Retrieval** | Knowledge base retrieval operations | Vector search query -> results |
| **Sub-agent Calls** | Parent-child agent relationships | orchestrator -> researcher |
| **Intermediate Outputs** | Intermediate step results | Search results, analysis reports |

### Span Structure

```
Trace: feature-user-auth
│
├── Span: orchestrator (parent)
│   ├── Span: brainstorming (child)
│   │   └── Span: llm_call (grandchild)
│   │       ├── input: "What providers?"
│   │       └── output: "OAuth2, SAML..."
│   │
│   ├── Span: codebase_explorer (child)
│   │   ├── Span: file_read (grandchild)
│   │   └── Span: search (grandchild)
│   │
│   └── Span: executor (child)
│       ├── Span: write_file (grandchild)
│       └── Span: run_tests (grandchild)
```

### Storage Requirements

```yaml
tracing:
  storage:
    # Required storage items
    store:
      - prompt_configurations    # Prompt configurations
      - input_artifacts          # Input artifacts
      - intermediate_outputs     # Intermediate outputs
      - tool_call_results        # Tool call results
      - error_details            # Error details

    # Replay capability
    replay:
      enabled: true              # Support execution replay
      retention_days: 30         # Retain for 30 days
```

## 2. Token Usage Analytics

### Tracked Metrics

```yaml
token_analytics:
  metrics:
    per_request:
      - prompt_tokens            # Input token count
      - completion_tokens        # Output token count
      - total_tokens             # Total
      - latency_ms               # Response latency
      - model_used               # Model used

    cumulative:
      - total_tokens_session     # Session cumulative
      - total_tokens_project     # Project cumulative
      - cost_estimate            # Cost estimate

    allocation:
      - by_feature               # By feature
      - by_agent_type            # By Agent type
      - by_task                  # By task
```

### Doom Loop Detection

A Doom Loop is a cycle where the Agent consumes tokens without making meaningful progress (repeatedly attempting the same failing approach).

```yaml
doom_loop_detection:
  enabled: true

  rules:
    - name: "repeated_same_error"
      threshold: 3               # 3 consecutive identical errors
      action: "pause_and_alert"
      message: "Agent may be stuck in a Doom Loop — please investigate"

    - name: "token_spike"
      threshold: "2x"            # 2x spike in token usage
      window: "5m"               # 5-minute window
      action: "throttle"

    - name: "no_progress"
      threshold: 10              # 10 iterations with no substantive progress
      action: "pause_and_escalate"
      message: "Agent is not making progress — human intervention required"
```

### Token Usage Report

```
┌──────────────────────────────────────────────────┐
│  Token Usage Report — Session #42                │
│                                                   │
│  Total: 45,230 tokens ($0.68)                    │
│                                                   │
│  By Agent:                                        │
│  ┌──────────────┬──────────┬────────┬─────────┐ │
│  │ Agent        │ Tokens   │ Cost   │ %       │ │
│  ├──────────────┼──────────┼────────┼─────────┤ │
│  │ executor     │ 18,420   │ $0.28  │ 40.7%   │ │
│  │ planner      │ 12,300   │ $0.25  │ 27.2%   │ │
│  │ reviewer     │  8,510   │ $0.12  │ 18.8%   │ │
│  │ researcher   │  6,000   │ $0.03  │ 13.3%   │ │
│  └──────────────┴──────────┴────────┴─────────┘ │
│                                                   │
│  Efficiency:                                      │
│  • Useful output ratio: 62%                       │
│  • Retry rate: 15%                                │
│  • Doom loops detected: 0                         │
└──────────────────────────────────────────────────┘
```

## 3. Continuous Evaluation

### Evaluation Tiers

```
┌─────────────────────────────────────────────────────────┐
│  Level 3: PRODUCTION                                    │
│  • Online A/B testing                                   │
│  • User satisfaction tracking                           │
│  • Periodic human calibration                           │
│                                                          │
│  Level 2: STAGING                                       │
│  • CI/CD automated evaluation (LLM-as-Judge)            │
│  • Accuracy, helpfulness, safety scoring                │
│                                                          │
│  Level 1: DEVELOPMENT                                   │
│  • Pre-deployment simulation (hundreds of scenarios)    │
│  • Unit-level Agent testing                             │
│  • Regression test suite                                │
└─────────────────────────────────────────────────────────┘
```

### LLM-as-Judge Configuration

```yaml
continuous_eval:
  llm_as_judge:
    enabled: true
    model: "claude-sonnet-4-6"      # Evaluation model

    dimensions:
      - name: accuracy
        weight: 0.4
        threshold: 0.85

      - name: helpfulness
        weight: 0.3
        threshold: 0.80

      - name: safety
        weight: 0.3
        threshold: 0.95             # Higher safety requirement

    scenarios:
      - "user_requests_harmful_code"
      - "ambiguous_requirements"
      - "complex_multi_step_task"
      - "error_recovery"

  human_in_loop:
    frequency: "weekly"             # Weekly human calibration
    sample_size: 20                 # 20 samples per review
    calibration_threshold: 0.1      # Trigger when auto-eval deviation > 10%
```

## Alerting Rules

```yaml
alerting:
  channels:
    - type: "slack"
      webhook: "${SLACK_WEBHOOK}"
    - type: "file"
      path: ".harness/alerts/"

  rules:
    - name: "token_spike"
      condition: "tokens_per_minute > 2 * baseline"
      severity: "warning"

    - name: "doom_loop"
      condition: "same_error_count >= 3"
      severity: "critical"
      action: "pause_agent"

    - name: "eval_score_drop"
      condition: "accuracy_score < 0.80"
      severity: "warning"

    - name: "safety_violation"
      condition: "safety_score < 0.90"
      severity: "critical"
      action: "halt_and_notify"

    - name: "high_retry_rate"
      condition: "retry_rate > 30%"
      severity: "info"
```

## Configuration Overview

```yaml
# .harness/config.yaml
observability:
  tracing:
    enabled: true
    store_artifacts: true
    replay_enabled: true
    retention_days: 30

  token_analytics:
    enabled: true
    track_per_request: true
    track_cumulative: true
    cost_allocation: true
    doom_loop_detection: true

  continuous_eval:
    enabled: true
    llm_as_judge:
      enabled: true
      dimensions: [accuracy, helpfulness, safety]
    human_calibration:
      enabled: true
      frequency: "weekly"

  alerting:
    enabled: true
    channels: [slack, file]
    rules: [token_spike, doom_loop, eval_score_drop, safety_violation]

  dashboard:
    metrics:
      - trace_span_count
      - token_usage_trend
      - evaluation_scores
      - retry_rate
      - agent_efficiency
      - doom_loop_incidents
```
