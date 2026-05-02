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

## 3. Module protocols (the five contracts)

These are the structural-typing protocols every module implements. They are *the* core public API.

| Protocol | Responsibility | Key methods |
|---|---|---|
| **Provider** | LLM backend | `complete()`, `parse_tool_calls()`, `list_models()`, `get_info()` |
| **Tool** | Agent capability | `execute(input) → ToolResult`; has `name`, `description` |
| **Orchestrator** | The execution loop strategy | `execute()` |
| **ContextManager** | Conversation memory | `add_message()`, `get_messages()`, `compact()` |
| **Hook** | Observability/control | `__call__(event, data) → HookResult` |

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

## 6. CLI / app layer (`amplifier`)

| Term | What it means |
|---|---|
| **`foundation` bundle** | The default bundle — providers, filesystem/bash/web/search tools, 14 agents, standard behaviors. |
| **Provider switching** | `amplifier provider use <name>` — runtime swap of LLM backend. |
| **Bundle add/use/list** | Registry operations on the user's installed bundles. |
| **Session persistence** | Sessions auto-saved per project. `amplifier continue`, `amplifier session resume <id>`. |
| **Plan mode (`/think` / `/do`)** | Chat toggle between read-only planning and execution. |
| **Log viewer** | Separate dev tool (`amplifier-log-viewer`) for debugging session logs. |

## 7. Repo / packaging vocab

| Term | What it means |
|---|---|
| **`amplifier-bundle-*`** | Naming convention for bundle repos (e.g. `amplifier-bundle-recipes`). |
| **`amplifier-module-*`** | Naming convention for single-module repos. |
| **`amplifier-app-*`** | Naming convention for application repos (e.g. `amplifier-app-cli`). |
| **Entry point** | `[project.entry-points."amplifier.modules"]` in `pyproject.toml` — how a Python package advertises its `mount()` function. |
| **Ecosystem** | Umbrella term for all the above + community repos listed in `amplifier/docs/MODULES.md`. |

## Quick mental cheat-sheet

- A **Bundle** (file) → composes with others via **Includes** → **Prepare** → produces a **Mount Plan** (dict) → instantiated as a **Session** by the kernel.
- Inside the session: **Provider** talks to the LLM, **Tools** act, **Orchestrator** loops, **ContextManager** remembers, **Hooks** observe, **Capabilities** pass cross-cutting state.
- **Agents** are bundles with a different frontmatter; **Behaviors** are reusable bundle fragments; **Recipes** are YAML workflows run by a specific tool.
- `amplifier-core` = kernel, `amplifier-foundation` = composition + reference content, `amplifier` = the CLI app you run.
