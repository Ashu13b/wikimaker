---
name: seam-audit
description: Architectural boundary, dependency seam, and import cycle audit. Use before adding cross-directory imports, creating new modules, refactoring subsystem boundaries, or planning significant feature additions.
---

# Architectural Seam & Boundary Audit

Perform an evidence-based architectural boundary inspection before adding cross-module imports or creating new components.

The goal is to maintain clean separation of concerns, prevent circular dependencies, and protect architectural seams.

Do not write implementation code during this audit.

---

## ⚡ Core Rules & Directives

1. **Consult `ARCH_MAP.md` First:**
   Always inspect the existing directory-to-directory import graph and cycle flags before proposing cross-directory dependencies.
2. **Respect Declared Compartments:**
   Consult `.context-kit/boundaries` (if present) to enforce declared compartment access rules (e.g. `core` must not import `cli`, `engine` must not depend on `ui`).
3. **Prevent Circular Dependencies:**
   Detect and block any multi-node cycles (`A` → `B` → `A`) and self-referential cycles (`A` → `A`).
4. **Enforce Modularity Limits:**
   Verify that existing target files are not already near the soft modularity cap (700 lines). If a file exceeds 700 lines, require decomposing into sub-modules rather than appending.

---

## 🔍 Investigation Workflow

1. **Map the Proposed Dependency:** Identify exactly which file/symbol will be imported and where it lives.
2. **Trace the Layer Hierarchy:** Determine if the import moves downward (higher-level orchestrator calling lower-level utility: **allowed**) or upward/sideways (utility calling orchestrator: **forbidden boundary crossing**).
3. **Verify Boundary Policy:** Check if the target module is internal/private or an exported public API.
4. **Evaluate Coupling Risk:** Does introducing this import tightly couple two independent subsystems that should communicate via interfaces or events?

---

## 📋 Required Audit Output

Every seam audit must produce:
1. **Architectural Seam Summary:** Overview of the proposed module boundaries.
2. **Directional Dependency Check:** Validation of `Caller -> Callee` hierarchy.
3. **Cycle & Boundary Risk Assessment:** Pass/Fail assessment on circular import risk and modularity limits.
4. **Recommendation:** Proceed with import, or create an intermediary abstraction/interface.
