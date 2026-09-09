---
name: adversarial-tester
description: Generate adversarial, edge-case, and failure-mode test suites. Use when writing tests for new features, hardening critical logic, testing external API integrations, or fuzzing inputs.
---

# Adversarial & Edge-Case Testing

Generate skeptical, non-happy-path test suites that actively attempt to break the implementation under review.

Do not write trivial "2 + 2 = 4" happy-path tests. Focus on boundary conditions, malformed data, partial outages, and unexpected sequence timing.

---

## ⚡ Testing Dimensions & Attack Vectors

1. **Boundary & Malformed Inputs:**
   - Empty collections (`[]`, `{}`), empty strings (`""`), single-character strings, whitespace-only.
   - Boundary numbers: `0`, `-1`, `MAX_INT`, `float("inf")`, `float("nan")`, extreme decimals.
   - Unicode & Encodings: Null bytes (`\0`), emojis, RTL characters, multi-byte sequences, control characters.
   - Extremely large payloads (100KB+ strings, 10,000 items) to check memory/time complexity.

2. **Network & I/O Fault Injection:**
   - Upstream API returning `500 Internal Server Error`, `502 Bad Gateway`, `429 Too Many Requests`.
   - Upstream timeout / socket hangup mid-response.
   - Truncated or malformed JSON payloads returned by dependencies.

3. **Concurrency & Race Conditions:**
   - Multiple concurrent calls to stateful functions / database update routines.
   - Duplicate idempotency keys submitted simultaneously.
   - Out-of-order event delivery.

4. **Data Corruption & Partial Failures:**
   - Exceptions thrown halfway through multi-step transactions to test rollback.
   - Disk/filesystem write failures or readonly file descriptor simulation.

---

## 🔬 Test Generation Protocol

1. Identify the public entry point or core domain service.
2. Formulate 3–5 realistic chaotic failure scenarios based on the attack vectors above.
3. Write automated unit/integration tests with explicit assertions on error handling, status codes, and state consistency.
4. Run the test suite and verify that all adversarial cases are handled gracefully without uncaught panics.
