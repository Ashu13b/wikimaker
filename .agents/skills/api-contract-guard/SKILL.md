---
name: api-contract-guard
description: Audit API contracts, endpoints, serialization schemas, and public interfaces for backward compatibility and breaking changes. Use before modifying routes, request/response models, GraphQL schemas, or exported function signatures.
---

# API Contract & Schema Stability Guard

Inspect proposed API and schema modifications to guarantee zero breaking changes for downstream clients, frontends, or external integrations.

---

## ⚡ Core Rules & Directives

1. **The Backward-Compatibility Invariant:**
   Never delete fields, rename fields, or change existing field types in public request/response schemas.
2. **Additive Changes Only:**
   New fields must be optional or provide sensible default values so existing consumers continue functioning without updates.
3. **Explicit Error Contracts:**
   Error response shapes (e.g. `{ "error": { "code": "...", "message": "..." } }`) must remain consistent across all HTTP status codes.
4. **Deprecation Protocol:**
   If a field or endpoint must be retired:
   - Mark as deprecated in OpenAPI/schema documentation.
   - Maintain dual-support for at least one major version or migration window.

---

## 🔍 Audit Checklist

- [ ] **Field Removal Check:** Have any fields been removed from response payloads?
- [ ] **Type Mutation Check:** Have any field types changed (e.g., `string` $\rightarrow$ `number` or `object` $\rightarrow$ `array`)?
- [ ] **Requiredness Check:** Have any optional input fields been converted to required?
- [ ] **Endpoint URL / Verb Check:** Have route paths or HTTP methods changed without redirect/alias?
- [ ] **Status Code Check:** Have expected HTTP response status codes changed?

---

## 📋 Required Audit Output

```markdown
### 📑 API Contract Stability Report

- **Target Route / Interface:** `GET /api/v1/resource` or `interface UserProfile`
- **Breaking Changes Detected:** [None | List of breaking changes]
- **Compatibility Status:** [FULLY COMPATIBLE | BREAKING CHANGE BLOCKED]
- **Recommended Remediation:** [Additive design or versioned path e.g. `/v2/`]
```
