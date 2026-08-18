---
name: root-cause-debug
description: Rigorous, evidence-based debugging and incident triage. Use when encountering a bug, test failure, runtime error, or unexpected behavior. Forbids speculative code edits until the root cause is isolated with a reproducing test.
---

# Evidence-Based Root Cause Debugging

Perform structured, evidence-based debugging to isolate and eliminate defects without trial-and-error code churn.

Act with scientific discipline: formulate hypotheses, test them against evidence, and prove the root cause before modifying source code.

Do not guess or apply speculative patches.

---

## ⚡ Core Rules & Directives

1. **Strict Separation of Diagnosis & Fix:**
   Never edit production source files until the root cause is verified with concrete evidence (stack trace, logged state, or failing test).
2. **Reproduce First:**
   Create an isolated reproducing command, script, or unit test demonstrating the exact failure before touching implementation code.
3. **Trace State Transitions:**
   Inspect inputs, boundary values, and state mutations leading up to the point of failure.
4. **Minimal, Targeted Remediation:**
   Once proven, apply the smallest possible fix that addresses the underlying defect without introducing architectural regressions.
5. **Verify Clean Quality Gates:**
   After applying the fix, run `./ck preflight <file>` and `./ck gate --fast` to confirm zero collateral damage.

---

## 🔬 Investigation Workflow

### Step 1: Capture the Exact Failure Signature
- Full error message, exception type, and stack trace.
- The exact command or user action that triggered the error.
- Relevant inputs and environmental state.

### Step 2: Formulate & Test Hypotheses
- List 1–3 candidate root causes based on the stack trace.
- Check relevant source lines using `./ck show <file>` or `view_file`.
- Check if the defect stems from:
  - **Input validation failure:** Null, undefined, malformed shape, unexpected type.
  - **State mutation timing:** Race condition, stale read, uninitialized variable.
  - **Unhandled edge case:** Division by zero, empty list, encoding mismatch.
  - **Contract mismatch:** Caller passed arguments in unexpected format or order.

### Step 3: Write a Reproducing Test
- Add a test case to the test suite (e.g. `tests/test_...`) that reliably fails with the exact observed bug.

### Step 4: Fix and Verify
- Apply the targeted fix in the source code.
- Run the reproducing test to verify it turns green.
- Run `./ck gate --fast` to ensure all linters, typecheckers, and existing tests pass cleanly.

---

## 📋 Required Debug Report

1. **Defect Signature:** Precise failure mode and error output.
2. **Isolated Root Cause:** Why the code failed under these specific conditions.
3. **Reproducing Test:** File and function name of the test proving the defect.
4. **Remediation Summary:** Explanation of the minimal code change applied.
5. **Verification Evidence:** Output of test suite and quality gates confirming resolution.
