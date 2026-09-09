---
name: pre-production-audit
description: Skeptical, evidence-based pre-production code review. Use when preparing to commit, merge a PR, release a feature, audit production readiness, or evaluate security, concurrency, and reliability.
---

# Pre-Production Code Audit

Perform a skeptical, evidence-based pre-production review of code before it reaches real users or production environments.

Act as a senior staff engineer auditing someone else's implementation, not as the author defending the code.

Do not modify implementation code during this audit.

---

## ⚡ Core Review Directives

1. **Assume Non-Happy Path Failure:**
   Assume the implementation works on the happy path but will fail under load, malformed input, network latency, or partial failure.
2. **Evidence-Based Findings Only:**
   Every finding must cite specific files, line numbers, and failure mechanisms. Do not generate hypothetical generic advice.
3. **The 2-Pass Convergence Rule:**
   - **Pass 1:** Comprehensive review of the proposed changes.
   - **Pass 2:** Audit strictly the *diff of the fixes* to ensure no regressions were introduced. Do not loop infinitely.
4. **Severity Gating:**
   - 🛑 **Block on `[CRITICAL]` & `[HIGH]`:** Data corruption, auth bypass, silent data loss, infinite loops, resource leaks.
   - ⚠️ **Log `[MEDIUM]` & `[LOW]`:** Minor defensive gaps, micro-optimizations, non-blocking cleanup.

---

## 🔍 The 8-Dimension Audit Checklist

1. **Correctness & Edge Cases:** Null/empty inputs, zero, negative numbers, numeric overflows, off-by-one, encoding mismatches.
2. **Error Recovery & Retries:** Unhandled exceptions, swallowed errors, retry storms, missing exponential backoff, timeout cascades.
3. **Concurrency & State:** Race conditions, non-atomic multi-step mutations, dirty reads, thread safety, idempotent operations.
4. **Security & Boundaries:** Path traversal, SQL/command injection, SSRF, protocol sanitization (`javascript:` URI in sinks), unvalidated inputs.
5. **Resource Lifecycle:** Memory growth, unclosed file descriptors, unclosed database connections, dangling background jobs.
6. **Data Integrity:** Partial writes, transactions without rollback, lost updates, schema assumption mismatches.
7. **Modularity & Seams:** Violations of `ARCH_MAP.md`, leakage across layers, circular references, bloated files (>700 lines).
8. **Observability:** Structured logs, trace headers, correlation IDs, meaningful error diagnostics.

---

## 📋 Required Audit Report Output

```markdown
### 🛡️ Pre-Production Audit Report

#### Executive Verdict: [PASS | CONDITIONAL PASS | BLOCK]

#### Findings
- **[CRITICAL | HIGH | MEDIUM | LOW] Title**
  - **Location:** `path/to/file.ext:L123-L145`
  - **Mechanism:** How the failure occurs under real conditions.
  - **Impact:** Security, data loss, downtime, or performance degradation.
  - **Remediation:** Concrete recommendation for resolution.

#### Verification Protocol
- [ ] Reproducing test case written or executed.
- [ ] Deterministic gate (`./ck gate --fast`) verified.
```
