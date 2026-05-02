# Independent re-audit findings

## Method
I read the primary sources listed in the brief (kernel docs/contracts/specs, foundation README/CONCEPTS/BUNDLE_GUIDE/AGENT_AUTHORING/PATTERNS/POLICY_BEHAVIORS/URI_FORMATS, the four foundation context files, amplifier README/USER_GUIDE/MODULES/MODULE_DEVELOPMENT/REPOSITORY_RULES, development-hygiene, recipes-usage, GLOSSARY) and built my outline first. Then I read only the H2 headings of the four chapters via `grep "^## "`, never the prose.

## My independent outline

### Chapter 1 — kernel layer
- Mechanism vs policy; two-implementation rule
- Rust kernel + PyO3 bridge; `RUST_AVAILABLE`
- Mount Plan schema and validation
- Session lifecycle: `initialize → execute → cleanup`
- Coordinator: mount points, capability registry, contribution channels
- `mount()` cleanup contract; `on_session_ready()` + polyglot caveat
- The five protocols: Provider/Tool/Orchestrator/ContextManager/HookHandler
- Hooks API: HookResult actions, precedence, injection budgets
- Events: required `execution:start/end`, `orchestrator:complete`
- Session forking: `parent_id`, `session:fork`, lineage
- Module source resolution: `ModuleSourceResolver` + entry-point fallback
- Polyglot transports (native/python/grpc/wasm) and `amplifier.toml`

### Chapter 2 — composition layer
- Bundles vs Mount Plans (bundles optional)
- Bundle file format: frontmatter + markdown body
- `compose()` per-section merge rules (deep-merge / by-id / replace)
- `includes:` as the single composition primitive
- Source URIs; mutable vs immutable refs
- Root vs nested bundles; namespace from `bundle.name`
- @mentions vs soft refs vs `context.include` (different semantics)
- `prepare()` → `PreparedBundle` → `create_session()`
- BundleRegistry, caching, `source_resolver` injection
- Polyglot bundles: `amplifier.toml`, transport-aware activation
- Foundation capabilities: `session.working_dir`, `bundle_package_paths`
- Bundle with root Python package; `[tool.uv.sources]` pitfalls

### Chapter 3 — authoring artifacts
- Agents are bundles: `meta:` vs `bundle:` frontmatter
- `meta.description`: WHY/WHEN/WHAT/HOW + examples
- Instruction structure and Output Contract
- Behavior pattern: reusable feature wiring
- Thin bundle pattern: 14-line `bundle.md` + behavior
- Context sink + thin awareness pointer (vs context poisoning)
- Model selection: `model_role`, fallback chains, `provider_preferences`
- `spawn:` and `tool-delegate` (`exclude_tools`/`inherit_tools`)
- `context_depth` × `context_scope` and self-delegation
- Tool modules: layout, `mount()` Iron Law, placeholder pattern
- Recipes and Skills: bundle-supplied, not kernel
- Bundle vs policy behaviors (`parent_id` check)
- Authoring anti-patterns: `@` in YAML, repo-name namespaces, force-include

### Chapter 4 — CLI app and ecosystem
- Install via `uv tool install`, `amplifier init`, first-run wizard
- Run modes: `amplifier run`, chat, `--bundle`/`--provider` overrides
- Provider/bundle/module command families
- Settings hierarchy + 6-layer module source override order
- Sessions: project slug, persistence, `continue`, `session list/show/resume`
- Plan mode (`/think`/`/do`) and chat slash commands
- Cache directory and `amplifier reset` (never `rm -rf`)
- `amplifier module dev`: init/link/list/status/test/create
- `amplifier update` + mutable-vs-immutable refs
- AGENTS.md anchor file
- Ecosystem map: amplifierd, amplifier-chat, log-viewer, community
- Naming: `amplifier-bundle-*`, `-module-*`, `-app-*`; ID vs package vs import

## Existing outline (from H2 headings only)

### Chapter 1
1.1 The kernel mindset; 1.2 Runtime objects; 1.3 The five module protocols; 1.4 Putting it together; 1.5 Self-check.

### Chapter 2
2.1 From Mount Plan to Bundle; 2.2 Bundle anatomy; 2.3 Composition and merge rules; 2.4 Includes, namespaces, and @mentions; 2.5 Source URIs and prepare(); 2.6 The thin bundle pattern; 2.7 Putting it together; 2.8 Self-check.

### Chapter 3
3.1 Authoring inside a bundle; 3.2 Instructions and context; 3.3 Agents; 3.4 Model selection; 3.5 Behaviors and the thin bundle pattern; 3.6 Spawn: tool inheritance for child agents; 3.7 Recipes; 3.8 Skills; 3.9 Choosing the right artifact; 3.10 Self-check. (Stray H2s — Operating Principles / Workflow / Output Contract — appear to be example-agent prose at top level.)

### Chapter 4
4.1 First contact; 4.2 Providers; 4.3 Bundles in the CLI; 4.4 Sessions and persistence; 4.5 Plan mode and chat affordances; 4.6 Debugging: log viewer; 4.7 Repo naming conventions; 4.8 Module entry points; 4.9 Cache directory and module resolution; 4.10 Developing modules locally; 4.11 The ecosystem at a glance; 4.12 Self-check.

## A. Topics in my outline missing from the existing guide
1. Hook precedence, injection budgets, ephemeral injections (no dedicated hook section).
2. `on_session_ready()` lifecycle method (no-timeout / Python-only / failure-event footguns).
3. Required orchestrator events (`execution:start/end`, `orchestrator:complete`).
4. Session forking mechanism (`parent_id`, `session:fork`) — kernel hook delegation rides on.
5. Polyglot transports + `amplifier.toml` (native/grpc/wasm story is invisible).
6. `context.include` (accumulates) vs `@mention` (replaces) vs soft ref — silent-failure pitfall.
7. `context_depth` × `context_scope` and self-delegation.
8. `amplifier update` + mutable-vs-immutable ref reproducibility.

## B. Topics in the existing guide that surprised me
1. 3.7 Recipes and 3.8 Skills as separate H2s — both are bundle-supplied features; could over-reach.
2. 2.5 combines "Source URIs" and "prepare()" — I'd split bundle composition from module activation.
3. Stray H2s in Ch.3 (Operating Principles / Workflow / Output Contract) look like a markdown nesting bug from an example agent.
4. 3.5 "Behaviors and the thin bundle pattern" — I'd have placed thin bundle in Ch.2; defensible.
5. No section on policy behaviors visible in TOC despite glossary prominence.

## C. Vocabulary divergences
1. "Module entry points" (4.8) — verify it covers the three-name confusion (module ID / package / import path).
2. "Cache directory and module resolution" (4.9) merges hygiene with the 6-layer source override order — distinct in sources.
3. 3.6 "Spawn" — sources also use `exclude_tools`/`inherit_tools` on `tool-delegate`; ensure both names appear.
4. 4.5 "Plan mode and chat affordances" — sources name the toggles `/think` and `/do`; ensure both names appear.
5. "Policy behavior" (glossary) — not visible in TOC; likely buried in 3.5.

## D. Recommended additions
1. **Hooks section in Ch.1** between 1.3 and 1.4. Sources: `amplifier-core/docs/HOOKS_API.md`, `MOUNT_PLAN_SPECIFICATION.md`. Why: precedence and injection budgets are first-class kernel mechanism, easily missed.
2. **Session forking + required orchestrator events in Ch.1** after the protocols. Sources: `SESSION_FORK_SPECIFICATION.md`, `contracts/ORCHESTRATOR_CONTRACT.md`. Why: kernel contracts the delegation and observability stacks ride on.
3. **Polyglot transports section** (Ch.1 after protocols, or Ch.4 near 4.8). Sources: `amplifier-core/docs/CORE_DEVELOPMENT_PRINCIPLES.md`, `amplifier-foundation/context/POLYGLOT_BUNDLES.md`. Why: `transport:` and `amplifier.toml` are absent.
4. **Expand Ch.2 §2.4** to contrast `context.include` (accumulates) vs `@mention` (replaces) vs soft refs. Source: `amplifier-foundation/docs/BUNDLE_GUIDE.md`. Why: silent-failure pitfall called out explicitly in source.
5. **`context_depth`/`context_scope` and self-delegation in Ch.3** near 3.6. Sources: `GLOSSARY.md` (citing `tool-delegate/README.md`, `multi-agent-patterns.md`). Why: glossary calls this "the central authoring decision" for delegating agents.
6. **`amplifier update` + mutable-vs-immutable refs in Ch.4** after 4.10. Sources: `amplifier/docs/USER_GUIDE.md` "Keeping Amplifier Up to Date", `GLOSSARY.md`. Why: only place pinning/reproducibility is explained.
