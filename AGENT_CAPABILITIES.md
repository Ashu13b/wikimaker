# Agent Capability Negotiation

This repository uses context-kit's versioned agent-capability protocol. Contexty
and the active agent describe their capabilities separately; verified shared
capabilities determine behavior.

## Inspect

```text
.context-kit/ck capabilities contexty
.context-kit/ck capabilities agent
.context-kit/ck capabilities effective
.context-kit/ck capabilities effective --json
```

For an unknown CLI, record a declarative manifest with `.context-kit/ck
agent-declare '<json>'`. Protocol 1 requires `protocol_version`, an `agent` object
with `family` and `version`, and a `claims` object containing only boolean values.
Declarations never contain executable commands and remain unverified claims.

Run `.context-kit/ck agent-probe`; after its exact nonce reaches the agent, confirm
it with the printed command. Cached evidence is invalidated when the agent,
Contexty capability code, hooks, host shell, or declaration changes.

Automatic diagnostics are change-triggered and bounded. Normal unchanged sessions
stay silent; full manifests and evidence are pull-only so project context remains
primary.

When local telemetry is explicitly enabled, `.context-kit/ck report` summarizes
capability reports, declaration counts, probe confirmation rate, profile-change
notices, the latest compatibility score, and aggregate advertised-hot-context
characters/estimated tokens/files/lines. Events never include agent identity or
version, nonce, fingerprint, project name, filenames, contents, or custom capability names.
