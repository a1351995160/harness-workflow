# Proposal Template

<!-- INSTRUCTIONS: Fill each section based on the approved intent.md. This document justifies WHY the feature should be built. For each section, derive content from the corresponding intent.md section: Background ← intent Problem Statement; Goals ← intent Success Criteria; Risks ← intent Assumptions. Carry forward context constraints from intent.md Section 4 into the Verification Strategy section. -->

> OpenSpec Proposal - The "Why"

## Feature: [Feature Name]

**Proposal ID:** PROP-[YYYY]-[NNN]
**Status:** Draft | Review | Approved | Rejected
**Created:** [Date]
**Author:** [Name]

---

## Executive Summary

[2-3 sentences summarizing the proposal]

---

## Background

### Current State
[Describe the current situation]

### Problem
[What's wrong with the current state]

### Opportunity
[What opportunity does this address]

---

## Proposal

### Overview
[High-level description of the proposed solution]

### Goals
1. [Primary goal]
2. [Secondary goal]
3. [Tertiary goal]

### Non-Goals
1. [What this proposal does NOT address]
2. [Explicit exclusions]

---

## Benefits

| Benefit | Impact | Measurement |
|---------|--------|-------------|
| [Benefit 1] | [High/Medium/Low] | [How to measure] |
| [Benefit 2] | [High/Medium/Low] | [How to measure] |

---

## Alternatives Considered

### Alternative 1: [Name]
- **Description:** [What it is]
- **Pros:** [Advantages]
- **Cons:** [Disadvantages]
- **Why Rejected:** [Reason]

### Alternative 2: [Name]
- **Description:** [What it is]
- **Pros:** [Advantages]
- **Cons:** [Disadvantages]
- **Why Rejected:** [Reason]

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| [Risk 1] | H/M/L | H/M/L | [How to mitigate] |
| [Risk 2] | H/M/L | H/M/L | [How to mitigate] |

---

## Verification Strategy

### Context Constraints
<!-- Carry forward from intent.md Section 4 (Context Constraints). Specify which docs load on demand, sub-agent isolation requirements, and max context window usage. -->
- [Maximum context window usage: e.g., 80%]
- [Sub-agent isolation: yes/no, and for which tasks]
- [Progressive disclosure: which reference docs to load on demand]

### Build-Verify Loop
- [ ] Identify tight loops (lint, unit tests) vs loose loops (integration, e2e)
- [ ] Define max iterations per loop (tight: 10, loose: 3-5)
- [ ] Specify context-efficient mode: silent on success, verbose on failure
- [ ] Enable doom loop detection (threshold: 3 same errors)

### Quality Gates
- [ ] List quality gates that apply to this feature
- [ ] Define which gates are blocking vs non-blocking
- [ ] Specify coverage threshold (default: 80%)

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Design | [X days] | [Dependency] |
| Implementation | [X days] | [Dependency] |
| Testing | [X days] | [Dependency] |
| Deployment | [X days] | [Dependency] |

---

## Resources Required

### Team
- [Role 1]: [X% allocation]
- [Role 2]: [X% allocation]

### Infrastructure
- [Resource 1]
- [Resource 2]

### Budget
- [Cost item]: $[Amount]

---

## Success Metrics

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| [Metric 1] | [Value] | [Value] | [Date] |
| [Metric 2] | [Value] | [Value] | [Date] |

---

## Approval

| Role | Name | Decision | Date |
|------|------|----------|------|
| Sponsor | | ⏳ Pending | |
| Tech Lead | | ⏳ Pending | |
| Security | | ⏳ Pending | |

---

## References

- [Link to related documents]
- [Link to research]
- [Link to discussions]
