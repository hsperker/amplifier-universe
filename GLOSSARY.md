# Amplifier Glossary

A working glossary of the important terms across the three submodules
(`amplifier-core`, `amplifier-foundation`, `amplifier`). Use it as a
quick reference when reading code, docs, or commits.

## 1. Architecture & process model

| Term | What it means |
|---|---|
| **Kernel** | The Rust core (`amplifier-core`) — module loader, session lifecycle, hook dispatcher. Everything else is "userspace." |
| **Mechanism vs Policy** | Design rule splitting kernel from everything else: kernel provides capabilities, modules/bundles make decisions. Litmus test: "could two teams want different behavior?" → policy. |
| **Userspace** | All swappable code outside the kernel — providers, tools, behaviors, bundles. |
| **PyO3 bridge** | The Rust↔Python boundary. `RUST_AVAILABLE` flag tells you which side a type lives on. |
| **Ruthless simplicity / text-first** | Recurring philosophy slogans — favor markdown/YAML, one composition primitive, no abstractions before they earn their keep. |
| **Polyglot transports** | The four module transports the kernel supports: `native` (Rust), `python`, `grpc`, `wasm`. The transport choice is a packaging concern; the protocol the module implements is the same. |
| **Two-implementation rule** | Governance norm: a kernel feature is only added when at least two real userspace implementations need it. Stops the kernel from accreting policy. |
| **Bricks and Studs** | Modular metaphor for the system: each module is a "brick" with stable "studs/sockets" (its protocol contract). Any single brick can be regenerated wholesale and snapped back in. Source: `amplifier-foundation/context/MODULAR_DESIGN_PHILOSOPHY.md`. |
| **Complexity budget** | Governance norm: every kernel feature must "pay rent" by retiring equivalent complexity elsewhere. Stops the kernel from accreting weight even through additive changes. Source: `amplifier-foundation/context/KERNEL_PHILOSOPHY.md`. |
| **Pre-Merge Gate / "merge is release"** | Governance rule for `amplifier-core` (the only PyPI-published repo): every PR must include the version bump, fresh wheel build, and end-to-end smoke output before merge. Source: `amplifier-core/context/release-mandate.md`. |

## 2. Runtime objects (kernel)

| Term | What it means |
|---|---|
| **Session** (`AmplifierSession`) | Live execution context. Lifecycle: `initialize → execute → cleanup`. Use as `async with`. |
| **Coordinator** | Per-session infrastructure object injected into modules. Holds `session_id`, config, hook registry, mount points, capabilities. |
| **Mount Plan** | Flat config dict the kernel consumes. Sections: `session`, `providers`, `tools`, `hooks`, `agents`. Output of compiling bundles. |
| **Mount / mount points** | Act of registering a module instance under a category (`providers`, `tools`, `hooks`). Each module's `mount(coordinator, config)` is its entry point. |
| **Module** | Anything mounted. Always has a `mount()` and returns a `cleanup()` callable. |
| **Module ID** | Stable string identifier (e.g. `provider-anthropic`, `tool-bash`). Used for entry points, merge rules, configuration. |
| **Cancellation Token** | Rust-backed cooperative cancellation primitive surfaced to Python. |
| **Capability** | Named value registered on the coordinator at runtime (e.g. `session.working_dir`). Modules query it; not part of the Mount Plan. |
| **Session forking** | Kernel-level mechanism to spawn a child session with a `parent_id`. Used by the app layer to delegate to sub-agents. |
| **Hook** | Callback fired on events (`pre_tool_use`, `post_tool_use`, etc.). Returns a `HookResult`. |
| **HookResult** | Hook return value with actions: continue / inject context / deny / replace output. Has precedence rules. |
| **Event** | Payload emitted into the kernel's event stream. Hooks subscribe; observability rides on this. |
| **`on_session_ready()`** | Optional second module entry point alongside `mount()`. Runs after all modules are mounted, so it can safely depend on cross-module wiring. **Footguns:** no timeout, Python-only (polyglot transports skip it). Failures are surfaced via the `module:on_session_ready_failed` event — the log alone is invisible to hooks. |
| **Contribution channels** | Cross-module discovery primitive. Modules call `register_contributor(channel, …)`; consumers call `collect_contributions(channel)`. The canonical channel is `observability.events`. Distinct from the runtime capability registry. |
| **Injection budgets** | Mount Plan caps on hook context injection: `session.injection_budget_per_turn` (default 10 000 tokens/turn) and `session.injection_size_limit` (default 10 KB per single injection). Stops a chatty hook from blowing the context window. Source: `MOUNT_PLAN_SPECIFICATION.md`, `HOOKS_API.md`. |

## 3. Module protocols (the five contracts)

These are the structural-typing protocols every module implements. They are *the* core public API.

| Protocol | Responsibility | Key methods |
|---|---|---|
| **Provider** | LLM backend | `complete()`, `parse_tool_calls()`, `list_models()`, `get_info()` |
| **Tool** | Agent capability | `execute(input) → ToolResult`; has `name`, `description` |
| **Orchestrator** | The execution loop strategy | `execute()` |
| **ContextManager** | Conversation memory | `add_message()`, `get_messages()`, `compact()` |
| **Hook** | Observability/control | `__call__(event, data) → HookResult` |

**Static provider capabilities** (`ProviderInfo.capabilities`) — declared by a Provider in `get_info()` to advertise what it can do (e.g. `tools`, `streaming`, `vision`). Distinct from runtime **Capability** values on the coordinator; static = declared by the module, runtime = registered during a session.

## 4. Composition layer (foundation)

| Term | What it means |
|---|---|
| **Bundle** | Markdown + YAML-frontmatter file describing a composable configuration unit. Compiles to a Mount Plan. |
| **Bundle sections** | `bundle` (metadata), `session`, `providers`, `tools`, `hooks`, `agents`, `context`, `instruction`, `spawn`. |
| **Compose** | `base.compose(overlay)` — layer bundles. Later wins. Section-specific merge rules (deep-merge for `session`/`spawn`, merge-by-module-ID for lists, replace for `instruction`). |
| **Includes** | `includes:` key — pull other bundles in. The single composition primitive. |
| **Prepare / PreparedBundle** | Result of resolving sources, downloading remote modules, installing deps. Has `create_session()`. |
| **Root bundle** | A `/bundle.md` at the top of a repo. Establishes a namespace. `is_root = True`. |
| **Nested bundle** | Bundle loaded via `#subdirectory=` URI or `@namespace:path`. Shares the root's namespace. `is_root = False`. |
| **Namespace** | Comes from `bundle.name` (not repo URL). The handle used in `@mentions`. |
| **@Mention** | `@namespace:path` reference inside an instruction; resolved to file content from the bundle's base path. |
| **Thin bundle pattern** | Recommended idiom — `bundle.md` is ~14 lines of `includes:` only; real content lives in behaviors/agents/context files. |
| **Source URI** | Where a bundle/module comes from. Forms: local path, `git+https://…@ref#subdirectory=…`. |
| **BundleRegistry** | In-process registry of loaded bundles for lookup and update checks. |
| **`source_base_paths`** | Per-bundle dict mapping namespace → on-disk base path. The actual data structure that powers `@namespace:path` resolution after composition. |
| **Soft reference** | A bare `namespace:path` token (no leading `@`) inside instructions or context. Acts as a load-on-demand pointer — the model can request the file, but it is not eagerly inlined like an `@mention`. Saves tokens. |
| **`source_resolver`** | Optional callback passed to `prepare()`. Lets the app layer override how module sources are fetched (e.g. swap remote URLs for local mirrors). The seam between bundle composition and the kernel's `ModuleSourceResolver`. |
| **Mutable vs immutable refs** | In source URIs: `@main` (mutable — moves), `@v1.0.0` (semi-stable — usually pinned), full SHA (immutable). Material to reproducibility; the CLI's update commands target mutable refs by default. |
| **Source-override resolution order** | Six-layer lookup the runtime walks to find a module's source: (1) env var `AMPLIFIER_MODULE_<ID>` → (2) workspace `.amplifier/modules/<id>/` → (3) project `settings.yaml` → (4) user `settings.yaml` → (5) bundle `source:` → (6) installed package entry point. First match wins. Source: `amplifier/docs/LOCAL_DEVELOPMENT.md`. |

## 5. Authoring artifacts (foundation + bundles)

| Term | What it means |
|---|---|
| **Agent** | A bundle with `meta:` frontmatter (`name` + `description`) instead of `bundle:`. Loaded by the same `load_bundle()`. |
| **Behavior** | A reusable bundle fragment that wires up a tool + its agents + its context as a unit. Imported via `includes:`. |
| **Bundle behavior vs policy behavior** | Bundle behaviors = composable feature wiring. Policy behaviors = app-level cross-cutting policies (logging, redaction) controlled by settings. |
| **Context (file)** | Markdown file injected into the session's instruction context — the "knowledge" an agent reads. |
| **Context sink** | Authoring pattern: heavy domain knowledge lives in agent files, not in always-loaded context. |
| **Instruction** | The system-prompt body of a bundle — the markdown beneath the YAML frontmatter. |
| **Spawn (policy)** | Frontmatter section controlling tool inheritance for child agents. |
| **model_role** | Agent frontmatter field naming a *role* (e.g. `architect`, `worker`) the app maps to a concrete model. |
| **provider_preferences** | Escape hatch on agents to pin a specific provider/model. |
| **Recipe** | YAML workflow file (steps + context + recursion limits) executed by the `recipes` tool. Shipped by the `amplifier-bundle-recipes` bundle — *not* a kernel concept. |
| **Skill** | Reusable invocable capability shipped by the `skills` bundle (separate from "tool"). |
| **Output Contract** | Section of an agent's instruction that defines the response shape callers can rely on (fields, format, error semantics). Required for any agent meant to be spawned by another. |
| **Thin awareness pointer** | Authoring pattern for context-sink agents: a 25–40 line context file that gives the always-loaded session just enough to know an expert agent exists, while the deep knowledge lives inside the agent itself. |
| **Context poisoning** | Named anti-pattern: stale, inconsistent, or eagerly-loaded heavy context that misleads the LLM into wrong-but-confident decisions. Drives the thin-pointer / context-sink discipline and the "retcon, don't evolve" rule. Source: `amplifier-foundation/context/CONTEXT_POISONING.md`. |
| **Delegation Imperative / "Orchestrator, not worker"** | Operating-mode slogan: the main session should orchestrate, not execute. Direct tool use is rare; agents are the default. Source: `amplifier-foundation/context/agents/delegation-instructions.md`. |
| **`context_depth` / `context_scope`** | Two orthogonal parameters on `tool-delegate` controlling how-much vs which-content context inheritance. `context_depth ∈ {none, recent, all}` × `context_scope ∈ {conversation, agents, full}`. The central authoring decision for any agent that delegates. Source: `amplifier-foundation/modules/tool-delegate/README.md`. |
| **Self-delegation (`agent="self"`)** | Spawn the current agent as a sub-agent with a fresh context window. Used for token-budget relief on long iterative tasks. Recommended pairing: `context_depth="all"`, `context_scope="full"`. Source: `amplifier-foundation/context/agents/multi-agent-patterns.md`. |
| **Iron Law of `mount()`** | Authoring rule: a module's `mount()` MUST register on the coordinator or return a Tool. No-op stubs fail `protocol_compliance` validation. Source: `amplifier-foundation/skills/creating-amplifier-modules/SKILL.md`. |
| **Retcon, don't evolve** | Documentation discipline: rewrite docs as if the new way was always true. Historical context belongs in git, not in the docs. Counter to context poisoning through accumulated evolution traces. Source: `amplifier-foundation/context/CONTEXT_POISONING.md`. |

## 6. CLI / app layer (`amplifier`)

| Term | What it means |
|---|---|
| **`foundation` bundle** | The default bundle — providers, filesystem/bash/web/search tools, 14 agents, standard behaviors. |
| **Provider switching** | `amplifier provider use <name>` — runtime swap of LLM backend. |
| **Bundle add/use/list** | Registry operations on the user's installed bundles. |
| **Session persistence** | Sessions auto-saved per project. `amplifier continue`, `amplifier session resume <id>`. |
| **Plan mode (`/think` / `/do`)** | Chat toggle between read-only planning and execution. |
| **Log viewer** | Separate dev tool (`amplifier-log-viewer`) for debugging session logs. Defaults to `http://localhost:8180`. |
| **Project slug** | Path-derived directory name under `~/.amplifier/projects/<slug>/`. Drives session scoping — `amplifier session list` filters by the current directory's slug. Behind the "where did my sessions go?" surprises. |
| **Cache directory** (`~/.amplifier/cache/`) | Where the actually-running module/library code lives as editable installs. The CLI's site-packages egg-links point here. **Wiping this directly breaks the install** — use `amplifier reset` instead. Source: `amplifier/context/development-hygiene.md`. |
| **`amplifier reset`** | Safe replacement for `rm -rf ~/.amplifier`: uninstalls and reinstalls the CLI in step, keeping the cache and site-packages in sync. Use `amplifier reset --full -y` for a non-interactive full reset. |
| **`amplifier module dev`** | Subcommand family for module development: `init`, `link`, `list`, `status`, `test`, `create`. The on-ramp for editing a module locally without rebuilding wheels. Source: `amplifier/docs/MODULE_DEVELOPMENT.md`. |
| **AGENTS.md anchor file** | Auto-loaded per-conversation file (searched at `~/.amplifier/AGENTS.md`, `.amplifier/AGENTS.md`, then repo-root `AGENTS.md`). Where agents persist learned context across sessions. Source: `amplifier-foundation/context/shared/common-agent-base.md`. |

## 7. Repo / packaging vocab

| Term | What it means |
|---|---|
| **`amplifier-bundle-*`** | Naming convention for bundle repos (e.g. `amplifier-bundle-recipes`). |
| **`amplifier-module-*`** | Naming convention for single-module repos. |
| **`amplifier-app-*`** | Naming convention for application repos (e.g. `amplifier-app-cli`). |
| **Entry point** | `[project.entry-points."amplifier.modules"]` in `pyproject.toml` — how a Python package advertises its `mount()` function. |
| **Ecosystem** | Umbrella term for all the above + community repos listed in `amplifier/docs/MODULES.md`. |
| **Module ID vs package name vs import path** | Three names for the same module: the **module ID** in bundle config (kebab, e.g. `tool-delegate`), the **package name** in PyPI (kebab with prefix, e.g. `amplifier-module-tool-delegate`), and the **import path** in Python (snake, e.g. `amplifier_module_tool_delegate`). Mismatches between these are a common silent failure. |

## Quick mental cheat-sheet

- A **Bundle** (file) → composes with others via **Includes** → **Prepare** → produces a **Mount Plan** (dict) → instantiated as a **Session** by the kernel.
- Inside the session: **Provider** talks to the LLM, **Tools** act, **Orchestrator** loops, **ContextManager** remembers, **Hooks** observe, **Capabilities** pass cross-cutting state.
- **Agents** are bundles with a different frontmatter; **Behaviors** are reusable bundle fragments; **Recipes** are YAML workflows run by a specific tool.
- `amplifier-core` = kernel, `amplifier-foundation` = composition + reference content, `amplifier` = the CLI app you run.
