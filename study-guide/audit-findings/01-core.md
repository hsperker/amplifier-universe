# Audit findings — amplifier-core

## Summary
Chapter 1 covers the kernel mindset, runtime objects, and the five protocols accurately. The biggest gap is **kernel-as-product-of-its-process** material — the release/wheel mandate, the polyglot `on_session_ready` boundary, and the runtime capability-registry idiom (app↔module IoC) vs the static `ProviderInfo.capabilities` taxonomy. A handful of small factual drifts exist.

## A. New terms worth promoting to the glossary

- **`RUST_AVAILABLE` / `_engine` import root** — Boolean exported from `amplifier_core._engine`; the only sanctioned runtime check for the Rust binding — `python/amplifier_core/__init__.py:14-98` — §1.
- **Pre-Merge Gate / "merge is release"** — `amplifier-core` is the only PyPI-published repo; every PR must include the version bump, fresh wheel, and E2E smoke output — `context/release-mandate.md:79-128` — §1 (governance).
- **`module:on_session_ready_failed`** — Event emitted when a Python module's `on_session_ready` raises; the only observable signal (the log alone is invisible to hooks) — `CONTRACTS.md:278-281` — §2.
- **`ApprovalProvider` protocol** — Sixth structural protocol paired with `HookResult(action="ask_user")`; not in the "five contracts" framing but a real mounted role — `CONTRACTS.md:37` — §3.
- **`session.injection_budget_per_turn` / `session.injection_size_limit`** — Mount Plan caps on hook context injection (default 10k tokens/turn, 10 KB/injection) — `MOUNT_PLAN_SPECIFICATION.md:47-48`, `HOOKS_API.md:382` — §2.
- **Static capability constants & cost tiers** — Well-known strings in `amplifier_core.capabilities`; `"thinking"` is canonical for Anthropic and OpenAI-style reasoning — `PROVIDER_SPECIFICATION.md:202-261` — §3.
- **Atomic version-bump script** — `scripts/bump_version.py` is the only sanctioned path to keep `pyproject.toml`, `crates/amplifier-core/Cargo.toml`, and `bindings/python/Cargo.toml` in sync — `release-mandate.md:34-44` — §1 (governance).
- **Ring 0 / "the center stays still"** — Self-positioning slogan and the diagram of what the kernel does *not* decide — `bundle.md:47-63`, `context/kernel-overview.md:7` — §1.

## B. Chapter 1 gaps

- **Capability (runtime)** — §1.2 frames it as inter-module wiring only; misses the canonical app↔module IoC use (e.g. `session.spawn` registered by the CLI, consumed by `tool-task`). Add one sentence + pointer to `docs/CAPABILITY_REGISTRY.md`.
- **Contribution channels** — glossary §2 has them; chapter mentions the channel only in passing (lines 332, 509). Add a 3-line note in Coordinator: pull-based, non-interfering, `observability.events` is canonical.
- **`on_session_ready`** — §1.2 covers timing and fork rules but omits the **no-timeout footgun** and the **Python-only / polyglot exclusion** — both load-bearing (`CONTRACTS.md:274-276, 350-354`).
- **HookResult precedence** — §1.2 line 330 gives ranks but omits that **multiple `inject_context` results merge** (settings from the first) — `HOOKS_API.md:99`.
- **Mount Plan injection budgets** — §1.2's example shows only `orchestrator`/`context`; the two production-relevant `session.injection_*` fields are not mentioned.
- **Static Provider capability taxonomy** — chapter §1.3's Provider entry mentions content blocks but not the well-known capability constants or cost tiers.

## C. Factual errors in Chapter 1

- **§1.1, lines 65-67** — claims submodule imports "currently re-export the same Rust-backed types." `RUST_CORE_LIMITATIONS.md:22-25` and `CONTRACTS.md:113-118` are explicit: submodule imports return **Python** implementations for backward compatibility; only top-level imports are Rust-backed. This is the chapter's most consequential error.
- **§1.2, line 297 (Event list)** — lists `context:pre_compact` / `context:post_compact`; `events.rs:110` and `CONTRACTS.md:375` also define a single combined `context:compaction`. Worth noting all three.
- **§1.2, lines 277-289 (Session forking)** — chapter says "There is nothing else." `SESSION_FORK_SPECIFICATION.md:117-129` specifies the `session:fork` payload also includes a redundant `data.parent` field for compatibility.

## D. Worth-citing references

- **§1.1 Mechanism vs Policy** → `agents/core-expert.md:198-224` ("Definitely Module If / Maybe Kernel If" decision table — most concise litmus codification).
- **§1.2 Coordinator** → `docs/CAPABILITY_REGISTRY.md` (canonical IoC pattern; `session.spawn` example).
- **§1.2 Module ID resolution** → `docs/MODULE_SOURCE_PROTOCOL.md` (`ModuleSource` / `ModuleSourceResolver` protocols and fallback behavior).
- **§1.2 Hook precedence + injection budgets** → `docs/HOOKS_API.md:81-99, 378-383`.
- **§1.3 Provider** → `docs/specs/PROVIDER_SPECIFICATION.md:80-117, 202-261` (content-preservation gotchas, capability/cost-tier constants).
- **§1.1 governance ("two-implementation rule")** → `context/release-mandate.md` (PyPI scope; v1.0.7/v1.2.3/v1.4.0 incident history).

## E. Out of scope but noteworthy

- `bundle.md` shows `core` is itself a bundle that `includes:` foundation — Chapter 2's "every repo is a bundle" framing.
- `agents/core-expert.md` is a model authoring artifact (`meta:` frontmatter, `model_role: general`, `@core:` mentions) — good worked example for Chapter 3's Agent + `@mention` sections.
- `ai_context/DOCUMENTATION_LINKING.md` documents YAML frontmatter on contract files (`related_files`, `relationship` types, `canonical_example`) — Chapter 3/4 authoring convention.
- `session.spawn` / `session.resume` capabilities are app-layer-provided — Chapter 4 CLI section.
