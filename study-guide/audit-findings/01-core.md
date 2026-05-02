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

- **Capability (runtime)** — chapter §1.2 frames it only as inter-module wiring; misses the canonical use as the **app↔module IoC seam** (e.g. `session.spawn` registered by the CLI, consumed by `tool-task`). Add one sentence + pointer to `docs/CAPABILITY_REGISTRY.md`.
- **Contribution channels** — glossary §2 has them; Chapter 1 mentions the channel only inside the Hook section (lines 332, 509). Add a 3-line subsection or merge into Coordinator: pull-based, non-interfering, `observability.events` is the canonical channel.
- **`on_session_ready`** — chapter §1.2 covers timing and the fork rule but omits the **no-timeout footgun** and the **Python-only / polyglot exclusion**. Both are load-bearing for module authors. (`CONTRACTS.md:274-276, 350-354`.)
- **HookResult action precedence** — chapter §1.2 lines 330 give numeric ranks but skip the explicit rule that **multiple `inject_context` results merge** (settings from the first). (`HOOKS_API.md:99`.)
- **Mount Plan `session.injection_budget_per_turn` / `injection_size_limit`** — chapter §1.2's Mount Plan example shows only `orchestrator`/`context`; these two production-relevant fields are not mentioned anywhere.
- **Static "Provider capabilities" taxonomy** — glossary calls them out in §3; chapter §1.3's Provider entry mentions content blocks but never the well-known capability constants or cost tiers.

## C. Factual errors in Chapter 1

- **§1.1, lines 65-67** — claims submodule imports "currently re-export the same Rust-backed types." `docs/RUST_CORE_LIMITATIONS.md:22-25` and `CONTRACTS.md:113-118` say the opposite: submodule imports return the **Python** implementations for backward compatibility; only top-level imports are Rust-backed. This is the chapter's most consequential error — a reader checking implementation type by submodule path will get the wrong answer.
- **§1.2, line 297 (Event list)** — lists `context:pre_compact` and `context:post_compact`. Both exist, but the canonical reference table in `CONTRACTS.md:375` and `events.rs:110` also defines `context:compaction`; worth noting all three rather than implying two.
- **§1.2, lines 277-289 (Session forking)** — chapter says "There is nothing else." `SESSION_FORK_SPECIFICATION.md:117-129` specifies that `session:fork` carries `parent_id` *and* a redundant `data.parent` field for compatibility — a small but verifiable detail readers will hit when filtering events.

## D. Worth-citing references

- **§1.1 Mechanism vs Policy** → `agents/core-expert.md:198-224` (the "Definitely Module If / Maybe Kernel If" decision table is the most concise litmus codification in the repo).
- **§1.2 Coordinator** → `docs/CAPABILITY_REGISTRY.md` (canonical IoC pattern; `session.spawn` example; the "always check, fail gracefully" guidance).
- **§1.2 Module / Module ID resolution** → `docs/MODULE_SOURCE_PROTOCOL.md` (defines `ModuleSource` / `ModuleSourceResolver` protocols and the kernel's fallback behavior — the seam Chapter 4 will hit).
- **§1.2 Hook precedence + injection budgets** → `docs/HOOKS_API.md:81-99, 122-138, 378-383` (the only place the merge-on-`inject_context` rule and the budget knobs are spelled out together).
- **§1.3 Provider** → `docs/specs/PROVIDER_SPECIFICATION.md:80-117, 202-261` (content-preservation gotchas, role-conversion table, capability/cost-tier constants).
- **§1.1 governance ("two-implementation rule")** → `context/release-mandate.md` (gives the rule its real teeth: PyPI scope, the v1.0.7 / v1.2.3 / v1.4.0 incident history that motivated the gate).

## E. Out of scope but noteworthy

- `bundle.md` shows `core` is itself a bundle that `includes:` foundation — relevant to Chapter 2's "every repo is a bundle" framing.
- `agents/core-expert.md` is a model authoring artifact (frontmatter `meta:`, `model_role: general`, `@core:` mentions, output-contract-style template) — good worked example for Chapter 3's Agent and `@mention` sections.
- `ai_context/DOCUMENTATION_LINKING.md` documents YAML frontmatter on contract files (`related_files`, `relationship` types, `canonical_example`) — a small but real authoring convention worth mentioning in Chapter 3 or Chapter 4 (ecosystem tooling).
- Capability-registry `session.spawn` / `session.resume` are app-layer-provided — fits Chapter 4's CLI section.
