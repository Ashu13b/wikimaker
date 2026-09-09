---
name: dependency-vetter
description: Enforce standard-library-first policy and audit new third-party packages for bloat, maintenance status, license compatibility, and security vulnerabilities. Use before adding any dependency to package.json, requirements.txt, pyproject.toml, or Cargo.toml.
---

# Dependency & Supply-Chain Vetter

Perform a strict supply-chain and dependency audit before introducing any third-party library to the repository.

The goal is to maintain a lightweight, zero-bloat codebase, prevent unmaintained dependencies from entering production, and prefer standard library solutions.

---

## ⚡ Core Rules & Directives

1. **The Stdlib-First Rule:**
   Before adding a package, prove that the required functionality cannot be cleanly implemented in <30 lines of standard library code.
2. **Reject Micro-Packages:**
   Never add trivial one-function packages (e.g. `is-number`, `left-pad`, `pad-string`, `uuid-v4-lite`).
3. **Inspect Transitive Footprint:**
   Evaluate total install size and deep transitive dependency trees. Heavy frameworks for single utilities are forbidden.
4. **Maintenance & Security Health Check:**
   - Active commits within the past 12 months.
   - Zero unpatched Critical/High CVEs.
   - Permissive license compatible with project policy (MIT, Apache-2.0, BSD, ISC).
5. **Update Manifest & DEPS_MAP:**
   Always record new dependencies in the canonical manifest and run `./ck build` to update `DEPS_MAP.md`.

---

## 🔍 Evaluation Protocol

1. **Requirement Analysis:** What exact capability is missing from the stdlib / existing dependencies?
2. **Candidate Comparison:** Compare 2 alternatives on size, dependency count, maintenance, and bundle cost.
3. **In-House Feasibility:** Write a 10-line prototype using existing tools to verify if external library is truly necessary.

---

## 📋 Required Output Report

```markdown
### 📦 Dependency Vetting Report

- **Proposed Package:** `name@version`
- **Purpose:** Brief description of need.
- **Stdlib Alternative Evaluated:** [Why stdlib is/isn't sufficient]
- **Transitive Dependency Count:** N dependencies (~X MB)
- **License & Health:** [License Type] | Last updated: [Date/Status]
- **Verdict:** [APPROVED | REJECTED - USE STDLIB | REJECTED - ALTERNATIVE SUGGESTED]
```
