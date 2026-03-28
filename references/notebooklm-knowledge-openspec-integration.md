# OpenSpec + Harness Engineering Integration (NotebookLM Knowledge Base)

> Source: NotebookLM "OpenSpec & Superpowers Workflow" notebook
> Retrieved: 2026-03-28

## Core Relationship: SDD meets Harness Engineering

OpenSpec acts as a critical structural bridge in modern AI-driven development by enforcing Specification-Driven Development (SDD) within a Harness Engineering environment. In a paradigm where "humans steer, agents execute," OpenSpec ensures that an AI agent is provided with clear, deterministic rails to follow before any actual coding begins.

### How They Complement Each Other

- **SDD (via OpenSpec)** operates at the **Spec and Plan layers** — dictates WHAT the AI is allowed to build and HOW it should approach the problem logically
- **Harness Engineering** operates at the **Harness layer** — mechanically enforces those boundaries and verifies the output

The integration is symbiotic: SDD provides the blueprints, the Harness provides the enforcement machinery.

## Repository as Single System of Record

OpenSpec implements SDD by persisting all requirements, architectural designs, and tasks as standard Markdown files inside an `openspec/` directory directly within the code repository. This satisfies the Harness Engineering principle: **making the repository the single "System of Record."**

Because an AI agent cannot read your mind, Slack messages, or external ticketing systems, OpenSpec ensures that all context and architectural assumptions are highly visible and machine-readable directly within the agent's context window.

### Delta Specs

OpenSpec uses "Delta Specs" (tracking changes via ADDED, MODIFIED, and REMOVED tags) to track requirement updates incrementally, much like a Git diff. This prevents the AI's context window from being flooded with a massive, monolithic instruction manual.

## OpenSpec Commands in the Harness Lifecycle

### 1. Propose & Explore (`/opsx:explore`, `/opsx:ff`, `/opsx:continue`)

Before modifying code, the agent must establish its context and plan.

- **Context Gathering**: `/opsx:explore` instructs the AI to read the current code and output an analysis report detailing existing interfaces, data models, and potential bottlenecks
- **Spec Generation**: Using `/opsx:ff` (fast-forward) or `/opsx:continue`, the AI generates three crucial files: `proposal.md` (the "why"), `design.md` (the "how"), and `tasks.md` (the executable checklist)

**Harness Value**: Acts as a **Context Firewall**. By forcing the AI to lock in the scope and technical design first, you prevent the model from going rogue or hallucinating features outside of the agreed-upon boundaries.

### 2. Apply (`/opsx:apply`)

Once the human engineer approves the Markdown documents, the AI is unleashed to write code.

- The AI strictly follows the `tasks.md` checklist, checking off each item sequentially
- Integrates tightly with **Architectural Constraints** of the harness
- Pre-commit hooks, linters, and structural tests provide immediate "back-pressure" if the AI deviates

**Harness Value**: Execution phase with mechanical enforcement via CI/CD, linters, and structural tests.

### 3. Verify (`/opsx:verify`)

After code is written, the system validates the work.

- Forces the AI to check implementation against original specifications across three dimensions:
  - **Completeness**: Were all tasks finished?
  - **Correctness**: Does it handle edge cases?
  - **Consistency**: Does it match the design conventions?

**Harness Value**: Acts as the **Automated Feedback Loop**. Instead of manual review, the agent self-verifies against hard specifications, catching deviations before human review.

### 4. Archive (`/opsx:archive`)

The final step focuses on long-term maintainability.

- Merges successful Delta Specs from temporary workspace into master `openspec/specs/` directory
- Cleans up active workspace

**Harness Value**: Represents **Entropy Management (Garbage Collection)**. Archiving ensures the repository's System of Record is perfectly updated with the latest architectural changes, guaranteeing future AI agents have accurate context.

## Key Insight from OpenAI Research

Engineering discipline in the AI era shows up in the **scaffolding and requirements** rather than the code itself. The code is what the AI produces; the engineering is what the human designs to constrain and guide the AI.
