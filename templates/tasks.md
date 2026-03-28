# Tasks Template

<!-- INSTRUCTIONS: Fill each section based on the approved design.md. For each task: (1) derive acceptance criteria from design.md requirements — each criterion must be a specific, testable statement, not a vague goal; (2) set dependencies based on the dependency graph; (3) assign the appropriate agent type from the agent catalog. Replace [bracketed placeholders] with actual content. -->

> OpenSpec Tasks - The Execution Steps

## Table of Contents

- [Phase 1: Foundation](#phase-1-foundation)
- [Phase 2: Core Implementation](#phase-2-core-implementation)
- [Phase 3: Integration](#phase-3-integration)
- [Phase 4: Testing](#phase-4-testing)
- [Phase 5: Entropy Check & Cleanup](#phase-5-entropy-check--cleanup)
- [Phase 6: Review & Deploy](#phase-6-review--deploy)
- [Dependency Graph](#dependency-graph)
- [Parallel Execution Opportunities](#parallel-execution-opportunities)
- [Risk Register](#risk-register)
- [Change Log](#change-log)

## Feature: [Feature Name]

**Task List ID:** TASK-[YYYY]-[NNN]
**Design:** DES-[YYYY]-[NNN]
**Status:** Not Started | In Progress | Blocked | Complete
**Created:** [Date]

---

## Task Summary

| Status | Count |
|--------|-------|
| ✅ Complete | 0 |
| 🔄 In Progress | 0 |
| ⏳ Pending | 0 |
| 🚫 Blocked | 0 |
| **Total** | 0 |

---

## Phase 1: Foundation

### Task 1.1: [Task Name]
- **Priority:** P0 (Critical) | P1 (High) | P2 (Medium) | P3 (Low)
- **Estimate:** [Hours/Days]
- **Dependencies:** None
- **Assignee:** [Agent Type]
- **Status:** ⏳ Pending

**Description:**
[What needs to be done]

**Acceptance Criteria:**
- [ ] [Criterion 1 — must be specific and testable, e.g., "Returns 401 for unauthenticated requests"]
- [ ] [Criterion 2 — reference the design.md requirement this validates]

**Technical Notes:**
[Implementation hints, gotchas]

---

### Task 1.2: [Task Name]
- **Priority:** P0
- **Estimate:** [Hours]
- **Dependencies:** Task 1.1
- **Assignee:** [Agent Type]
- **Status:** ⏳ Pending

**Description:**
[What needs to be done]

**Acceptance Criteria:**
- [ ] [Criterion 1 — must be specific and testable, e.g., "Processes 1000 req/s with <200ms p99 latency"]
- [ ] [Criterion 2 — reference the design.md requirement this validates]

---

## Phase 2: Core Implementation

### Task 2.1: [Task Name]
- **Priority:** P0
- **Estimate:** [Hours]
- **Dependencies:** Phase 1 Complete
- **Assignee:** executor
- **Status:** ⏳ Pending

**Description:**
[What needs to be done]

**Acceptance Criteria:**
- [ ] [Criterion 1 — specific, testable, e.g., "Module exports all functions defined in design.md Section 3"]
- [ ] [Criterion 2 — reference the design.md requirement this validates]

---

## Phase 3: Integration

### Task 3.1: [Task Name]
- **Priority:** P1
- **Estimate:** [Hours]
- **Dependencies:** Phase 2 Complete
- **Assignee:** executor
- **Status:** ⏳ Pending

**Description:**
[What needs to be done]

**Acceptance Criteria:**
- [ ] [Criterion 1 — specific, testable, e.g., "API returns correct response for all endpoints defined in design.md Section 4"]
- [ ] [Criterion 2 — reference the design.md requirement this validates]

---

## Phase 4: Testing

### Task 4.1: Write Unit Tests
- **Priority:** P0
- **Estimate:** [Hours]
- **Dependencies:** Phase 2 Complete
- **Assignee:** tester
- **Status:** ⏳ Pending

**Description:**
Write comprehensive unit tests for all new modules.

**Acceptance Criteria:**
- [ ] 80%+ code coverage
- [ ] All edge cases covered
- [ ] All tests passing

---

### Task 4.2: Write Integration Tests
- **Priority:** P1
- **Estimate:** [Hours]
- **Dependencies:** Task 4.1
- **Assignee:** tester
- **Status:** ⏳ Pending

**Description:**
Write integration tests for API endpoints and database operations.

**Acceptance Criteria:**
- [ ] All endpoints tested
- [ ] Database operations verified
- [ ] Error handling tested

---

### Task 4.3: Write E2E Tests
- **Priority:** P1
- **Estimate:** [Hours]
- **Dependencies:** Phase 3 Complete
- **Assignee:** tester
- **Status:** ⏳ Pending

**Description:**
Write end-to-end tests for critical user flows.

**Acceptance Criteria:**
- [ ] Critical paths covered
- [ ] Happy path + error scenarios
- [ ] All E2E tests passing

---

## Phase 5: Entropy Check & Cleanup

### Task 5.0: Entropy Scan
- **Priority:** P1
- **Estimate:** [Hours]
- **Dependencies:** Phase 4 Complete
- **Assignee:** gc-agent
- **Status:** ⏳ Pending

**Description:**
Scan for AI-generated code quality issues (AI slop): outdated documentation, unused imports, dead code, circular dependencies, and style inconsistencies.

**Acceptance Criteria:**
- [ ] No outdated documentation referencing removed features
- [ ] No unused imports or dead code paths
- [ ] No circular dependencies
- [ ] No hardcoded values that should be configuration
- [ ] Quality grade report generated

---

## Phase 6: Review & Deploy

### Task 6.1: Code Review
- **Priority:** P0
- **Estimate:** [Hours]
- **Dependencies:** Phase 4 Complete
- **Assignee:** reviewer
- **Status:** ⏳ Pending

**Description:**
Comprehensive code review of all changes.

**Acceptance Criteria:**
- [ ] No critical issues
- [ ] High issues resolved
- [ ] Medium issues documented

---

### Task 6.2: Security Review
- **Priority:** P0
- **Estimate:** [Hours]
- **Dependencies:** Task 5.0
- **Assignee:** security
- **Status:** ⏳ Pending

**Description:**
Security review of authentication, authorization, and data handling.

**Acceptance Criteria:**
- [ ] No critical vulnerabilities
- [ ] OWASP Top 10 checked
- [ ] Secrets not exposed

---

### Task 6.3: Documentation
- **Priority:** P1
- **Estimate:** [Hours]
- **Dependencies:** Phase 4 Complete
- **Assignee:** writer
- **Status:** ⏳ Pending

**Description:**
Update documentation for new feature.

**Acceptance Criteria:**
- [ ] API documentation updated
- [ ] README updated
- [ ] Inline comments complete

---

### Task 6.4: Deploy
- **Priority:** P0
- **Estimate:** [Hours]
- **Dependencies:** Task 6.1, Task 6.2
- **Assignee:** executor
- **Status:** ⏳ Pending

**Description:**
Deploy to production environment.

**Acceptance Criteria:**
- [ ] All tests passing
- [ ] Quality gates passed
- [ ] Monitoring verified

---

## Dependency Graph

```
Phase 1 (Foundation)
    │
    ├── Task 1.1 ──┐
    │              │
    └── Task 1.2 ──┼──► Phase 2 (Core)
                   │         │
                   │         └── Task 2.1 ──┬──► Phase 3 (Integration)
                   │                        │
                   └────────────────────────┴──► Phase 4 (Testing)
                                                    │
                                                    ├── Task 4.1 ──┐
                                                    │              │
                                                    ├── Task 4.2 ──┼──► Phase 5 (Entropy Check)
                                                    │              │
                                                    └── Task 4.3 ──┘          │
                                                                               ▼
                                                                        Phase 6 (Review & Deploy)
```

---

## Parallel Execution Opportunities

| Parallel Group | Tasks | Agents |
|----------------|-------|--------|
| Group A | Task 4.1, Task 4.2 | tester, tester |
| Group B | Task 2.1, Task 2.2 | executor, executor |

---

## Risk Register

| Risk | Tasks Affected | Mitigation |
|------|----------------|------------|
| [Risk 1] | [Tasks] | [Mitigation] |
| [Risk 2] | [Tasks] | [Mitigation] |

---

## Change Log

| Date | Author | Change | Tasks Affected |
|------|--------|--------|----------------|
| [Date] | [Name] | [Description] | [Task IDs] |

---

## Notes

[Any additional notes or context for the implementation team]
