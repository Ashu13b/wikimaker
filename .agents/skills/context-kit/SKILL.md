---
name: context-kit
description: Token-optimized codebase navigation, architectural seam compliance, and automated pre-flight quality-gate verification. Use when locating symbols, inspecting file structures, making edits, or verifying code changes in context-kit enabled repositories.
---

# Context-Kit: Agent Guidance & Execution Protocol

**Context-Kit serves as the reins for AI agents and vibecoders alike.** A capable frontier model possesses immense intelligence, but arrives context-blind and undirected. Context-Kit provides standing direction, structural seams, and self-correcting feedback loops so the agent operates like a disciplined senior engineer from turn one.

---

## ⚡ Core Directives for Agents

1. **Never brute-force scan:** Do not spawn blind `grep`, `rg`, or `find` pipelines over the codebase to locate functions, types, or classes.
2. **Consult Maps Before Grep/Read:** The always-loaded index maps (`CODE_MAP.md`, `ARCH_MAP.md`, `DEPS_MAP.md`, `CONVENTIONS_MAP.md`) contain the codebase structure.
3. **Continuous Self-Correction:** Run fast preflights (`ck preflight <file>`) or auto-fixes (`ck fix`) after editing to resolve syntax and lint errors before handing work to the user.
4. **Verify Before Handing Over:** Always run the quality gate (`ck gate --fast`) after making edits to intercept type errors, linting bugs, and undeclared dependencies in flight.

---

## 🔄 5-Step Execution Lifecycle

### Step 1: Orient & Check State
Before starting work or after resuming:
```bash
sh .context-kit/ck brief
```
- Checks map freshness, active rigor profile, and any uncommitted interruption state from prior sessions.

---

### Step 2: Zero-Guess Symbol & File Lookup
- **Find symbol definition:**
  ```bash
  sh .context-kit/ck where <symbol_name>
  ```
  Returns exact file location and declaration line without full-text grep scans.

- **Inspect file outline/structure:**
  ```bash
  sh .context-kit/ck show <path_to_file>
  ```
  Returns file composition, top-level classes, methods, and functions without burning tokens reading thousands of lines.

---

### Step 3: Check Architectural Seams & Dependencies
- **Cross-directory imports:** Check `ARCH_MAP.md` before importing across directories to ensure you do not create circular dependencies or violate boundary policies (`.context-kit/boundaries`).
- **Dependencies & Env Keys:** Consult `DEPS_MAP.md` before assuming an external package or environment key is present.
- **House Style & Naming:** Consult `CONVENTIONS_MAP.md` for casing and naming patterns.

---

### Step 4: Focused Task Compartments
For complex multi-file tasks, retrieve only the active 2-hop dependency neighborhood:
```bash
sh .context-kit/ck compartment auto
# or declared compartment: sh .context-kit/ck compartment <name>
```

---

### Step 5: Pre-Flight Gate Verification & Map Refresh
Immediately after modifying or creating source files:

1. **Run Fast Quality Gate:**
   ```bash
   sh .context-kit/ck gate --fast
   ```
   - Catches linting regressions (`ruff`, `eslint`), type errors (`pyright`, `tsc`), modularity bloat, and undeclared imports (`dependency-guard`).
   - If any check fails, resolve it immediately before reporting completion to the user.

2. **Rebuild Index Maps:**
   ```bash
   sh .context-kit/ck build
   ```
   - Synchronizes `CODE_MAP.md`, `ARCH_MAP.md`, and other index files with your latest changes.
