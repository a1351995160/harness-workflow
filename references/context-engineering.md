# Context Engineering

> Strategies for managing Agent context windows, ensuring the Agent always has precise, minimal, and sufficient information

## Core Principle

From the Agent's perspective, **anything it cannot access within its context window effectively does not exist**. Context Engineering is about ensuring the Agent has the precise information it needs to make correct decisions.

## Three Types of Context

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTEXT TYPES                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  STATIC CONTEXT (always available)                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • CLAUDE.md / AGENTS.md                             │   │
│  │ • Architecture specs, API contracts                  │   │
│  │ • Code style guides, naming conventions              │   │
│  │ • Dependency layering rules                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  DYNAMIC CONTEXT (real-time awareness)                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • Directory structure mapping (at startup)           │   │
│  │ • CI/CD pipeline status                              │   │
│  │ • Observability data (logs, metrics, traces)         │   │
│  │ • Git diff / change status                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ON-DEMAND CONTEXT (load as needed)                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • Detailed design docs for specific modules          │   │
│  │ • Database schema definitions                        │   │
│  │ • Third-party API documentation                      │   │
│  │ • Historical decision records                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Progressive Disclosure

**Problem**: Stuffing a 1,000-page instruction manual into context consumes valuable context tokens and confuses the model.

**Solution**: Use AGENTS.md as a "table of contents" and load deeper documents on demand.

```
┌──────────────────────────────────────────────────────────┐
│  AGENTS.md (lightweight TOC, always in context)           │
│  ┌────────────────────────────────────────────────────┐  │
│  │ # Project Guide                                     │  │
│  │                                                     │  │
│  │ ## Architecture                                     │  │
│  │ See: docs/architecture.md (load for design tasks)  │  │
│  │                                                     │  │
│  │ ## API Contracts                                    │  │
│  │ See: docs/api-specs.md (load for API changes)      │  │
│  │                                                     │  │
│  │ ## Database                                         │  │
│  │ See: docs/database-schema.md (load for DB tasks)   │  │
│  │                                                     │  │
│  │ ## Quality Standards                                │  │
│  │ See: docs/quality-gates.md (load for reviews)      │  │
│  └────────────────────────────────────────────────────┘  │
│       │          │          │          │                   │
│       ▼          ▼          ▼          ▼                   │
│  [Load only   [Only for  [Only for   [Load only           │
│   for design   API        database    during reviews]      │
│   tasks]       changes]   tasks]                           │
└──────────────────────────────────────────────────────────┘
```

> **Validation from OpenAI projects**: Teams found that giant AGENTS.md files quickly rot and overwhelm the model. Instead, use AGENTS.md as a lightweight table of contents, with the actual knowledge base version-controlled in a structured docs/ directory.

## Sub-agent Context Firewall

**Problem**: As the context window fills up with logs, search results, and tool outputs, the Agent suffers from "context rot" -- reasoning ability degrades sharply.

**Solution**: Use sub-agents as "context firewalls".

```
Orchestration Agent (clean context)
    │
    ├──▶ Research Sub-agent (fresh context)
    │    └── Performs extensive searches and file reads
    │    └── Returns: refined summary + list of key file paths
    │
    ├──▶ Code Exploration Sub-agent (fresh context)
    │    └── Deep traversal of codebase structure
    │    └── Returns: list of relevant modules + interface definition summary
    │
    └──▶ Security Scan Sub-agent (fresh context)
         └── Runs full security scanning toolchain
         └── Returns: vulnerability report only (no scan logs)
```

**Rules:**
1. Sub-agents run in **fresh context windows**
2. They return **highly refined summaries** (referencing file paths rather than returning raw code)
3. The orchestration agent's context **remains clean at all times**
4. Intermediate tool outputs **stay in the sub-agent's context** and are not propagated upward

## Context Compaction

When tools return large volumes of output:

| Strategy | Implementation | Use Case |
|----------|---------------|----------|
| **Head + Tail** | Keep the first N and last N lines of output | Log files, stack traces |
| **Filesystem Offload** | Write full output to a file; keep only the path in context | Search results, large diffs |
| **Summary Extraction** | LLM generates a structured summary | Long documents, API responses |
| **Silence on Success** | Passing tests/checks are not injected into context | Build-verify loop |

## Decision Flow

```
Need to add information to context?
    │
    ├── Is it critical reference info? ──→ STATIC: always include
    │
    ├── Is it real-time status? ──→ DYNAMIC: fetch on demand
    │
    ├── Only needed for specific tasks? ──→ ON-DEMAND: Progressive Disclosure
    │
    ├── Is the output large? ──→ COMPACTION: compress or offload
    │
    └── Is it an intermediate result? ──→ SUB-AGENT: delegate to sub-agent
```

## Configuration Example

```yaml
# .harness/config.yaml
context_engineering:
  progressive_disclosure: true
  agents_md_as_toc: true

  context_firewall:
    enabled: true
    delegate_to_subagents:
      - research
      - codebase_exploration
      - security_scanning
    return_format: "summary_only"  # Do not return raw output

  compaction:
    max_context_ratio: 0.8         # Trigger compaction at 80%
    strategy: "head_tail"          # head_tail | summary | filesystem
    head_lines: 20
    tail_lines: 20
    offload_to: ".harness/outputs/"
    silent_on_success: true        # Do not inject into context on success
```
