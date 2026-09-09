---
name: adr-architect
description: Architectural Decision Record generator and trade-off analyzer. Use when designing new subsystems, evaluating conflicting technical approaches, selecting database/caching strategies, or refactoring major components.
---

# Architectural Decision Record (ADR) Architect

Structure, evaluate, and document high-impact architectural decisions before implementation begins.

Prevents hasty, unexamined architectural choices by forcing explicit comparison of 2–3 alternatives with clear trade-off analysis.

---

## ⚡ Core Rules & Directives

1. **Rule of 3 Options:**
   Always compare at least **2 distinct technical architectures** against the status quo (Option A vs Option B vs Option C).
2. **Explicit Trade-Off Matrix:**
   Every choice has downsides. Unconditionally identify complexity, operational overhead, latency, and failure modes for every option.
3. **Commit to `docs/adr/`:**
   Document approved decisions in numbered markdown records (`docs/adr/000X-title.md`) so future agents understand the rationale.

---

## 📋 ADR Document Template

```markdown
# ADR-000X: [Title of Decision]

## Status
[PROPOSED | ACCEPTED | SUPERSEDED]

## Context & Problem Statement
What problem are we solving? What are the key business and technical constraints?

## Decision Drivers
- Latency / throughput requirements
- Maintenance complexity
- Standard library / zero-dependency posture
- Operational cost

## Considered Options
1. **Option A:** [Description]
2. **Option B:** [Description]
3. **Option C:** [Description]

## Trade-off Comparison Matrix

| Criteria | Option A | Option B | Option C |
| :--- | :--- | :--- | :--- |
| **Complexity** | Low | Medium | High |
| **Performance** | Good | Excellent | Best |
| **Dependencies** | 0 (Stdlib) | 1 external package | Heavy framework |
| **Failure Modes** | Simple local crash | Network latency | Distributed sync lag |

## Chosen Decision & Rationale
Chosen: **Option X** because [clear technical justification].

## Consequences & Mitigations
- **Positive:** [Benefits]
- **Negative / Risks:** [Downsides and how they will be mitigated]
```
