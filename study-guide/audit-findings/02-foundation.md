# Audit findings — amplifier-foundation

## Summary
Foundation's `context/` philosophy docs and the `agents/` delegation/multi-agent docs are the richest unmined seam. The biggest single gap is the **Bricks-and-Studs** metaphor + the **delegate-tool two-parameter context system** (`context_depth` × `context_scope`) — glossary-grade primitives absent from the study guide. Secondary gaps: kernel-philosophy governance vocabulary and operational concepts (session repair, three-level logging) that orphan whole expert agents.

## A. New terms worth promoting to the glossary

- **Context poisoning** — Inconsistent or stale information in context/docs that misleads the LLM into wrong-but-confident decisions; also "structural poisoning" when heavy docs are eagerly loaded — `amplifier-foundation/context/CONTEXT_POISONING.md:7,283`; LANGUAGE_PHILOSOPHY:83 — §5 (composition).
- **Bricks and Studs** — Modular metaphor: each module is a "brick" with stable "studs/sockets" (interface contracts) so any single module can be regenerated wholesale and snapped back in — `context/MODULAR_DESIGN_PHILOSOPHY.md:6-8`; LANGUAGE_PHILOSOPHY.md:43-51 — §1.
- **Verification spectrum** — Ranking of languages by how much the toolchain catches before runtime; underpins Amplifier's Rust/Python split — `context/LANGUAGE_PHILOSOPHY.md:55-68` — §1.
- **Complexity budget / complexity ledger** — Governance rule: every kernel addition must "pay rent" by retiring equivalent complexity elsewhere — `context/KERNEL_PHILOSOPHY.md:51-52,98` — §1.
- **`context_depth` / `context_scope`** — Orthogonal two-parameter system on `tool-delegate` controlling how-much vs which-content context inheritance (`none|recent|all` × `conversation|agents|full`) — `modules/tool-delegate/README.md:11-24`; `context/agents/delegation-instructions.md:184-204` — §5 (authoring) or §4.
- **Self-delegation (`agent="self"`)** — Spawn yourself as a sub-agent for context-window relief; recommended with `context_depth="all", context_scope="full"` — `context/agents/multi-agent-patterns.md:186-195` — §5.
- **Delegation Imperative / "Orchestrator, not worker"** — Slogan: direct tool use should be rare; agents are context sinks and the default operating mode — `context/agents/delegation-instructions.md:7-15,144` — §5.
- **Retcon, don't evolve** — Documentation discipline: rewrite docs as if the new way was always true; historical info goes to git, not docs — `context/CONTEXT_POISONING.md:182-201` — §5.
- **Conventions via instructions, not code** — Anti-shared-helper principle: encode trivial cross-module patterns as guidance, not a shared library — `context/IMPLEMENTATION_PHILOSOPHY.md:199` — §1.
- **AGENTS.md anchor** — Auto-loaded per-conversation file (`~/.amplifier/`, `.amplifier/`, repo root) where agents persist learned context — `context/shared/common-agent-base.md:159-205` — §6 (CLI/app layer).
- **Source-override resolution order** — Six-step lookup (env var → `.amplifier/modules/` → project settings → user settings → bundle `source:` → entry point) for swapping a module's source — `context/shared/common-agent-base.md:140-156` — §4 (composition).
- **Iron Law of `mount()`** — Authoring rule: `mount()` MUST register on the coordinator or return a Tool; no-op stubs fail `protocol_compliance` validation — `skills/creating-amplifier-modules/SKILL.md:18-26` — §3.

## B. Chapter 2 gaps (composition)

1. **Source-override resolution order** is invisible. The 6-step precedence (env var → workspace `.amplifier/modules/` → settings → bundle `source:` → entry point) is what apps and devs actually rely on; §2.5 mentions only `source_resolver`. Add to §2.5.
2. **Polyglot transports clone-integrity markers.** `POLYGLOT_BUNDLES.md:30-38` lists the file markers (`pyproject.toml`, `bundle.md`, `amplifier.toml`) that prove a clone succeeded; this matters for debugging "module not found." Add to §2.5 prepare() pitfalls.
3. **`bundle.dot` / `bundle.png` auto-docs.** Foundation auto-regenerates a 7-cluster diagram per repo with `source_hash` freshness, gated by `enhance_diagrams` — `skills/bundle-to-dot/SKILL.md`; `context/bundle-awareness.md:52`. Brief sidebar in §2.6.
4. **`session.raw: true`.** Foundation's `bundle.md:43` enables raw streaming mode plus `extended_thinking: true`; this is a real, undocumented `session:` field beyond `orchestrator`/`context`. Add a one-line note in §2.2 section table.
5. **Soft-reference vs `@mention` pitfall is well-treated**, but Chapter 2 §2.4 misses that `@` in YAML *silently fails* — the asymmetry is buried in a pitfall bullet; CONTEXT_POISONING and bundle-awareness both rely on it. Already in pitfalls; consider promoting.
6. **Mutable-vs-immutable refs reproducibility** is in the glossary and §2.5 mentions it, but the `amplifier reset --remove cache -y` recovery flow that ISSUE_HANDLING and common-agent-base both prescribe is not. Cross-link §2.5 cache pitfall to Chapter 4.

## C. Chapter 3 gaps (authoring)

1. **`context_depth` / `context_scope` matrix.** Currently absent. The two-parameter system is the central authoring decision for any agent that delegates — `delegation-instructions.md:184-245`. Add a table in §3.6 or as a new §3.6.x.
2. **Multi-agent patterns** — parallel dispatch, agent chain with accumulated knowledge (`context_scope="agents"`), parallel-investigation-with-synthesis, and session resumption for iterative critique loops — `context/agents/multi-agent-patterns.md`. None covered. Add a §3.6.x sidebar.
3. **Self-delegation for token relief.** Distinct enough to warrant a paragraph; pairs with the context-sink pattern. Source: `multi-agent-patterns.md:186-195`.
4. **"Delegation Imperative" / "Orchestrator, not worker."** This is the *primary* operating-mode slogan for foundation's coordinator and is invisible in §3.3 — `delegation-instructions.md:7-15`.
5. **Design-first decomposition.** zen-architect → modular-builder → zen-architect cycle and the rule "specs before modular-builder" — `multi-agent-patterns.md:92-156`. Best fit: §3.3 or §3.6.
6. **Agent domain honoring.** When an agent description says MUST/REQUIRED, the orchestrator MUST delegate — `delegation-instructions.md:151-166`. This makes the §3.3 advice on the description field load-bearing. Currently implicit.
7. **AGENTS.md per-project anchor file.** Auto-loaded; agents update it; never mentioned. Source: `common-agent-base.md:159-205`.
8. **Hooks as policy concretized.** `hooks-progress-monitor` (analysis-paralysis detector) and `hooks-todo-display` are concrete examples that would anchor §3.5's policy-vs-bundle-behavior discussion — `modules/hooks-progress-monitor/README.md`.

## D. Factual errors in chapters 2 or 3

None found. URI_FORMATS adds `git+ssh://...` which Chapter 2 §2.5 omits but does not contradict. Chapter 3 §3.1's directory layout matches foundation's actual structure.

## E. Worth-citing references

- §2.4 (composition pitfalls) → `context/CONTEXT_POISONING.md:282-345` "Structural Prevention in Amplifier" — directly motivates the @mention vs context.include rule and the thin-pointer pattern.
- §2.5 (prepare) → `context/POLYGLOT_BUNDLES.md:18-38` — explains why prepare() skips Python install for non-Python modules.
- §3.3 (agents) → `context/agents/delegation-instructions.md:74-148` "Context Sink Pattern" — the canonical statement, with the orchestrator/agent token-flow diagram.
- §3.5 (policy behaviors) → `context/KERNEL_PHILOSOPHY.md:21-37` "Mechanism, not policy" tenets 1, 6, 9 — the philosophy bedrock of the bundle/policy distinction.
- §3.6 (spawn) → `modules/tool-delegate/README.md:11-46` — the canonical reference for delegate parameters.
- §3.7 (recipes) → `recipes/validate-agents.yaml` thresholds match `docs/DOMAIN_VALIDATOR_GUIDE.md` "explicit PASS thresholds" pattern — cross-link in §3.3 description checklist.
- New Chapter 3 sidebar → `context/agents/multi-agent-patterns.md:36-66` "Complementary Agent Combinations" table — best one-page reference for orchestration patterns.
- §3.2 (context-sink) → `context/IMPLEMENTATION_PHILOSOPHY.md:199` "Conventions via instructions, not code" — gives the deeper "why" behind thin awareness pointers.

## F. Out of scope but noteworthy

- **Session repair (FM1/FM2/FM3, REPAIR vs REWIND, COMPLETE vs REPLACE)** and `scripts/amplifier-session.py` belong in Chapter 4 (operational tooling) — `context/agents/session-repair-knowledge.md`.
- **events.jsonl line-size hazard** and the three-level logging system (INFO/DEBUG/RAW) — Chapter 4 debugging — `context/agents/session-storage-knowledge.md:14-130`.
- **ISSUE_HANDLING 7-phase workflow** with GATE 1/GATE 2 and the gate-efficiency rule — Chapter 4 ecosystem/process — `context/ISSUE_HANDLING.md`.
- **External PRs are communication, not proposals** — Chapter 4 contributor guide — `docs/PR_REVIEW_GUIDE.md:9-83`.
- **`amplifier-dev` workspace lifecycle (create→work→destroy)** with SCRATCH.md — Chapter 4 — `context/amplifier-dev/dev-workflows.md`.
- **Implementation philosophy "Wabi-sabi / Occam / Trust in emergence / Pragmatic trust"** quartet — Chapter 1 sidebar; ground truth for the "ruthless simplicity" slogan.
