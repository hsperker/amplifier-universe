# Chapter 1 — The Kernel Layer

The kernel is `amplifier-core`: a Rust crate plus its PyO3 Python bindings that does as little as possible. It loads modules, wires them into a session, dispatches lifecycle events, and otherwise stays out of the way. Everything that smells like a product decision — which model, which loop, what to log, where to write — lives outside the kernel as a swappable module. This chapter teaches the kernel's vocabulary so the rest of the system makes sense: when you read `Chapter 2` on bundles or `Chapter 3` on agents, the names and types here will already be familiar.

## Concepts covered

- Kernel
- Mechanism vs Policy
- Userspace
- PyO3 bridge / `RUST_AVAILABLE` flag
- Ruthless simplicity / text-first
- `AmplifierSession`
- Coordinator (`ModuleCoordinator`)
- Mount Plan
- Mount / mount points
- Module / Module ID
- Cancellation Token
- Capability (runtime, on coordinator)
- Session forking (`parent_id`)
- Hook (runtime concept) / HookResult / Event
- Provider, Tool, Orchestrator, ContextManager, HookHandler protocols

---

## 1.1 The kernel mindset

### Kernel

The kernel is the small, stable center of Amplifier — `amplifier-core`. Its responsibilities are exactly five: module discovery and loading, lifecycle coordination, the hook/event system, session management, and the stable contracts other code depends on. Everything else is pushed out.

It exists for the same reason a Linux kernel exists: every consumer in the ecosystem flows through it, so a bug or breaking change here breaks everything downstream. Holding the surface tiny and the semantics boring is what lets the edges (modules, bundles, apps) move quickly. The kernel is implemented in Rust (`crates/amplifier-core/`) and exposed to Python via PyO3; from a Python user's perspective it looks like an ordinary package.

You recognize the kernel by what it does *not* contain: no provider list, no orchestration strategy, no logging destination, no config-file format, no CLI. If a file under `python/amplifier_core/` mentions a specific LLM vendor or a specific log path, that's a smell — the kernel takes those things as inputs.

### Mechanism vs Policy

The kernel provides **mechanisms**; modules provide **policies**. A mechanism is a capability that admits many uses (e.g. "load a module," "emit an event," "register a hook"). A policy is a decision (e.g. "use Anthropic," "redact API keys before logging," "deny writes to `/etc`").

This split exists because policies are where reasonable teams disagree. If the kernel bakes a policy in, two teams who disagree must each fork the kernel; if the kernel exposes a mechanism, both teams write modules and live side by side. The litmus test from `docs/DESIGN_PHILOSOPHY.md` is one sentence: **"Could two teams want different behavior? If yes, it's policy — push it to a module."** Apply that test before adding anything to the kernel.

The split is enforceable. The kernel's anti-patterns list explicitly bans provider selection, orchestration strategy, output format choice, logging destination, and default resolution from kernel code. When in doubt, prototype as a module first; only extract to the kernel after at least two independent modules need the same primitive (the "two-implementation rule").

### Userspace

In Amplifier, "userspace" is everything outside the kernel: Providers, Tools, Orchestrators, ContextManagers, Hooks — and the Bundles and Apps built on top of them. The Linux analogy is exact. Modules implement protocols (the "studs"), are loaded into a running session, and can be unloaded or replaced. Userspace innovation is fast and parallel; kernel evolution is slow and additive.

Practical consequence: when you want new behavior, you almost always want a module. The chapters that follow (`Chapter 2` on bundles/composition, `Chapter 3` on agents/behaviors/recipes, `Chapter 4` on the CLI) all describe userspace.

### PyO3 bridge and `RUST_AVAILABLE`

Amplifier's kernel logic lives in Rust. The PyO3 bridge in `bindings/python/` exposes the Rust types to Python under the same names Python consumers always used. The `RUST_AVAILABLE` flag (on `amplifier_core._engine`) reports whether the compiled Rust extension loaded.

The bridge has one rule: existing Python imports, signatures, and return types must keep working unchanged. After the switchover, top-level imports return Rust-backed types:

```python
from amplifier_core import AmplifierSession   # → RustSession (PyO3 wrapper)
from amplifier_core import ModuleCoordinator  # → RustCoordinator
from amplifier_core import HookRegistry       # → RustHookRegistry
from amplifier_core import CancellationToken  # → RustCancellationToken
from amplifier_core import RUST_AVAILABLE     # bool
```

Submodule imports (e.g. `from amplifier_core.coordinator import ModuleCoordinator`) currently re-export the same Rust-backed types under the old paths for compatibility. The Pythonic API surface — `async with`, `await`, dicts, Pydantic models — is identical regardless of where the implementation lives. Data crosses the boundary as JSON: Rust uses `#[serde(rename_all = "snake_case")]`; Python uses `Literal[...]` strings and Pydantic `BaseModel`s with matching field names. See `CONTRACTS.md` for the full type-mapping table.

You do not need to know Rust to write modules. You do need to know that the boundary exists, because: (1) error types may be richer on the Rust side than the Python catch-all suggests, (2) some Python-only utilities (`ModuleLoader`, `ApprovalSystem`, `DisplaySystem`, the validation framework) still live in `python/amplifier_core/` and are *not* mirrored in Rust, and (3) the `Rust*`-prefixed names (`RustSession`, etc.) remain available as explicit aliases.

### Ruthless simplicity / text-first

"Ruthless simplicity" is the operating principle: as simple as possible but no simpler; every abstraction must justify its existence; code you don't write has no bugs. In kernel work, that translates to a high bar for additions and a strong preference for deletion. Releases are deliberately small and boring.

"Text-first" means representations are human-readable and inspectable. Mount Plans are plain dicts. Hook events carry JSON-serializable data. The unified observability stream is JSONL. There is no hidden state, no magic globals, no opaque binary blob between modules and the kernel. If you cannot diff it, the kernel doesn't want it.

**Related**: Mount Plan (§1.2), the five module protocols (§1.3), `Chapter 2` on how Bundles compile to Mount Plans.

---

## 1.2 Runtime objects

A session walks through three phases: **construction → `initialize()` → `execute()` → `cleanup()`**. The objects in this section are introduced as they appear along that path.

### Session (`AmplifierSession`)

A session is one execution context: a session ID, a Mount Plan, a coordinator, mounted modules, and the conversation state they hold. Its purpose is to bound a unit of work — usually one user request, possibly many turns — so that resources, cancellation, and lineage have somewhere to live.

You recognize it by `from amplifier_core import AmplifierSession` (Rust-backed) or `from amplifier_core.session import AmplifierSession` (the Python class in `python/amplifier_core/session.py`). The constructor signature:

```python
class AmplifierSession:
    def __init__(
        self,
        config: dict[str, Any],                  # Mount Plan
        loader: ModuleLoader | None = None,
        session_id: str | None = None,           # UUID auto-generated if None
        parent_id: str | None = None,            # set when forking
        approval_system: "ApprovalSystem | None" = None,
        display_system: "DisplaySystem | None" = None,
        is_resumed: bool = False,
    ): ...
```

Three required pieces of `config`: `session.orchestrator`, `session.context`, and at least one provider — runtime validation in `_session_init.py` raises `ValueError` otherwise. The lifecycle is async:

```python
from amplifier_core import AmplifierSession

async with AmplifierSession(config) as session:
    response: str = await session.execute("List files in current directory")
# __aexit__ calls session.cleanup()
```

`initialize()` mounts modules per the plan and emits `session:start` (or `session:resume` if `is_resumed=True`); `execute(prompt)` runs the orchestrator; `cleanup()` runs registered cleanups in reverse mount order and emits `session:end`.

**Pitfalls.** Constructing a session without `session.orchestrator` *or* `session.context` in the config raises immediately — these are not optional. Forgetting `await session.initialize()` (when not using `async with`) will produce a "no orchestrator" `RuntimeError` at `execute()` time.

**Related**: Mount Plan (§1.2), Coordinator (below), session forking (§1.2).

### Coordinator (`ModuleCoordinator`)

The coordinator is the runtime hub injected into every module. It owns mount points, the hook registry, the cancellation token, the capability registry, and the `session_id`/`parent_id` it propagates onto every emitted event. It exists so modules can talk to the session without knowing about each other or about the kernel internals.

You recognize it as the first parameter of every `mount(coordinator, config)` function and as `coordinator` keyword-injected into `Orchestrator.execute()`. It is `RustCoordinator` (PyO3-wrapped Rust) by default; the `_engine.pyi` stub is the most accurate signature reference. The shape that matters to module authors:

```python
class ModuleCoordinator:
    # Properties
    session_id: str
    parent_id: str | None
    hooks: HookRegistry
    cancellation: CancellationToken
    mount_points: dict[str, Any]
    config: dict[str, Any]                  # the Mount Plan

    # Mount/get
    async def mount(self, mount_point: str, module: Any, name: str | None = None) -> None: ...
    async def unmount(self, mount_point: str, name: str | None = None) -> None: ...
    def get(self, mount_point: str, name: str | None = None) -> Any: ...

    # Capabilities (named runtime objects)
    def register_capability(self, name: str, value: Any) -> None: ...
    def get_capability(self, name: str) -> Any: ...

    # Cleanup
    def register_cleanup(self, cleanup_fn: Callable[[], Any]) -> None: ...

    # Contributions (for cross-module discovery)
    def register_contributor(self, channel: str, name: str, callback: Callable[[], Any]) -> None: ...
    async def collect_contributions(self, channel: str) -> list[Any]: ...

    # Cancellation / hook results
    async def request_cancel(self, immediate: bool = False) -> None: ...
    async def process_hook_result(self, result: HookResult, event: str, hook_name: str = "unknown") -> Any: ...
```

**Pitfalls.** Stashing the coordinator in a module-level global is the canonical anti-pattern (`CONTRACTS.md` calls it out): in a multi-session process you'll cross-wire sessions. Either capture the coordinator in a closure inside `mount()`, or use `register_capability` / `get_capability` for session-scoped lookups.

**Related**: Mount points (below), Hook (§1.2), Capability (§1.2).

### Mount Plan

A Mount Plan is the dict the kernel reads to decide what to load. It is the single contract between the application layer (which compiles configs from bundles, user files, env vars, CLI flags) and the kernel (which validates, loads, and mounts).

It exists so the kernel can be agnostic about config sources and merging policy. The kernel sees a finished plan, never the upstream files. The schema lives in `docs/specs/MOUNT_PLAN_SPECIFICATION.md`; the minimum that loads:

```python
{
    "session": {
        "orchestrator": "loop-basic",     # required: orchestrator module ID
        "context":      "context-simple"  # required: context manager module ID
    },
    "providers": [
        {"module": "provider-mock"}        # at least one required
    ],
    # Optional sections:
    # "tools":  [{"module": "tool-filesystem"}, ...]
    # "hooks":  [{"module": "hooks-logging"}, ...]
    # "agents": {"<name>": {<partial mount plan overlay>}}
    # "context": {"config": {...}}
}
```

Each entry under `providers`, `tools`, `hooks` is a dict with a required `module` (the Module ID), an optional `source` (a URI like `git+https://...@ref`, `file:///...`, or a package name), and an optional module-specific `config`. The `agents` section is special: it holds *partial* Mount Plans used as overlays when forking child sessions, and is **not** mounted at session-init time. See `Chapter 3` for how agents use it.

Use `MountPlanValidator` for structural validation before construction:

```python
from amplifier_core.validation import MountPlanValidator
result = MountPlanValidator().validate(mount_plan)
if not result.passed:
    raise SystemExit(result.format_errors())
```

**Pitfalls.** Apps should not hand-roll Mount Plans; the resolution logic (env interpolation like `${ANTHROPIC_API_KEY}`, bundle composition, precedence) lives in the app layer (`Chapter 4`). The kernel reads what it's given.

**Related**: Module (below), session forking (§1.2), `Chapter 2` on Bundles.

### Mount and mount points

A **mount point** is a named slot on the coordinator under which modules of one role live: `"providers"`, `"tools"`, `"hooks"`, `"session"` (which holds the orchestrator and context manager). To **mount** is to attach a module instance under a mount point with an optional name, making it discoverable via `coordinator.get(mount_point, name)`.

This indirection exists so modules don't import each other. An orchestrator asks for `coordinator.get("tools")` and gets a `dict[name, Tool]`; it doesn't care which file produced any given tool. The mount happens inside the module's `mount()` entry-point function:

```python
async def mount(coordinator, config):
    tool = MyTool(config)
    await coordinator.mount("tools", tool, name="my_tool")
    async def cleanup() -> None:
        ...
    return cleanup
```

The `mount()` free function (no `self`) is the contract. The kernel calls it once per module, in phase order (orchestrator → context → providers → tools → hooks). Its return value is interpreted as follows (from `CONTRACTS.md`): a callable becomes the cleanup; `None` means no cleanup; non-callables are silently ignored. Cleanups run in reverse registration order at session teardown.

There's a second optional lifecycle hook, `on_session_ready(coordinator)`, that runs *after every module across all phases has mounted*. Use it when a module needs the fully composed coordinator (e.g. to discover hooks contributed by peers). It is Python-only and its return value is ignored — register cleanups directly via `coordinator.register_cleanup()`.

**Related**: Module ID (below), Coordinator (§1.2).

### Module and Module ID

A **module** is a self-contained "brick" that implements one of the five protocols (§1.3) and exposes a `mount()` entry point. A **Module ID** is the string used in a Mount Plan to identify it (e.g. `"loop-basic"`, `"provider-anthropic"`, `"tool-filesystem"`).

The kernel resolves a Module ID to runnable code in three steps (`docs/specs/MOUNT_PLAN_SPECIFICATION.md`):
1. If the plan entry has `source`, the `ModuleSourceResolver` fetches it (git, filesystem, package).
2. Otherwise, look for a Python entry point under the `amplifier.modules` group that matches the ID.
3. Otherwise, look for a directory named `amplifier-module-<id>` on the filesystem.

A module's `pyproject.toml` declares its entry point:

```toml
[project.entry-points."amplifier.modules"]
my-tool = "amplifier_module_my_tool:mount"
```

Modules can be polyglot. The kernel supports four transports (native Rust, Python via PyO3, gRPC sidecar, WASM in-process); a module's `amplifier.toml` declares which one it is, and the host picks the matching loader. Module authors do not write transport code — they implement the protocol and let the bridge handle the rest.

**Related**: The five protocols (§1.3), `Chapter 2` on packaging.

### Cancellation Token

A cancellation token is a cooperative, two-state cancellation primitive owned by the session and exposed at `coordinator.cancellation`. States: `none` (running), `graceful` (let in-flight tools finish, then stop), `immediate` (synthesize results and stop now).

It exists because async cancellation in Python is famously coarse; long-running tools and LLM calls need a way to be told "user pressed Ctrl-C" without losing observability or producing torn state. The Rust-backed token tracks running tools and propagates to child tokens (forked sessions get linked tokens).

```python
token = coordinator.cancellation
token.is_cancelled            # bool
token.state                   # "none" | "graceful" | "immediate"
token.request_graceful()      # → bool (True if state changed)
token.request_immediate()
token.reset()
token.on_cancel(callback)     # async callback invoked on cancellation
```

Orchestrators are expected to check the token between turns and to translate cancellation into an `execution:end` event with `status="cancelled"` (see `ORCHESTRATOR_CONTRACT.md`). Tools that take >1 s should also check.

**Related**: Coordinator (§1.2), Orchestrator (§1.3).

### Capability (runtime)

A **capability** at runtime is a named value registered on the coordinator that other modules can look up by string. It exists because some cross-module wiring is genuinely dynamic — module B wants the search tool that module A registered, without importing A.

```python
coordinator.register_capability("my_module.search_tool", search_tool)
...
search_tool = coordinator.get_capability("my_module.search_tool")  # may be None
```

Use it sparingly. The canonical use is in `on_session_ready()` after the full mount wave, paired with closure-captured state inside `mount()`. Capability names are conventionally namespaced (`<module>.<thing>`).

> Note: there is also a *static* notion of capability — strings like `tools.streaming` advertised by providers in `ProviderInfo.capabilities` and used for routing. That is different from the runtime registry described here; see `docs/specs/PROVIDER_SPECIFICATION.md` for the static taxonomy.

**Related**: Coordinator (§1.2), `on_session_ready` (§1.2).

### Session forking (`parent_id`)

Forking creates a child session linked to a parent by ID. The kernel mechanism is one parameter — `parent_id` — and one event — `session:fork`. There is nothing else.

```python
child = AmplifierSession(
    config=child_config,                         # app-layer-merged plan
    loader=parent.loader,
    session_id=f"{parent.session_id}-specialist",
    parent_id=parent.session_id,
)
await child.initialize()    # emits session:fork; child events carry parent_id
```

What the kernel guarantees (from `SESSION_FORK_SPECIFICATION.md`): every event the child emits includes its `parent_id`; `session:fork` always fires; parent and child are independent after fork; nesting is allowed. What the kernel does *not* do: merge configs, discover agents, manage child lifecycles, or enforce ID schemes. All of that is app-layer (covered in `Chapter 3` under agents and the `task` tool).

**Pitfalls.** A parent's `on_session_ready` callbacks do **not** re-fire on child mount; the child runs its own independent wave. Don't rely on parent-only initialization to be present in a child unless the child's own modules establish it.

**Related**: Mount Plan (§1.2), `Chapter 3` on agents.

### Hook (runtime), HookResult, Event

Three tightly related concepts; understand them together.

An **Event** is a named lifecycle moment with a JSON-serializable payload. Canonical names live in `crates/amplifier-core/src/events.rs` and Python `amplifier_core.events`; the most common are `execution:start`, `execution:end`, `session:start`, `session:end`, `session:fork`, `llm:request`, `llm:response`, `tool:pre`, `tool:post`, `tool:error`, `context:pre_compact`, `context:post_compact`, `orchestrator:complete`. Use the constants, not string literals.

A **Hook** at runtime is a registered handler for a specific event name. Handlers are async callables `async (event: str, data: dict[str, Any]) -> HookResult`. Registration:

```python
unregister: Callable[[], None] = coordinator.hooks.register(
    event="tool:pre",
    handler=my_handler,
    priority=10,            # lower number = earlier
    name="my_handler",
)
```

A **HookResult** is the model returned by a handler. It controls flow:

```python
class HookResult(BaseModel):
    action: Literal["continue", "deny", "modify", "inject_context", "ask_user"] = "continue"
    data: dict[str, Any] | None = None
    reason: str | None = None
    context_injection: str | None = None
    context_injection_role: Literal["system", "user", "assistant"] = "system"
    ephemeral: bool = False
    approval_prompt: str | None = None
    approval_options: list[str] | None = None
    approval_timeout: float = 300.0
    approval_default: Literal["allow", "deny"] = "deny"
    suppress_output: bool = False
    user_message: str | None = None
    user_message_level: Literal["info", "warning", "error"] = "info"
    append_to_last_tool_result: bool = False
```

**Action precedence** when multiple handlers fire on the same event (highest first): `deny` (1, short-circuits) → `ask_user` (2, blocks for approval) → `inject_context` (3, multiple results merge) → `modify` (4, data chains through) → `continue` (5, default). Blocking actions always beat non-blocking ones, so a security gate cannot be silently bypassed by a context-injecting peer.

The kernel emits standard events; orchestrators emit `execution:*`, `provider:*`, `tool:*`, `orchestrator:complete`; modules may register custom events through the contribution channel `"observability.events"` so dashboards and tooling can discover them. The full reference is `docs/HOOKS_API.md`.

**Pitfalls.** Hook handlers should not throw; the kernel logs but does not re-raise from a handler, and a thrown exception will simply not produce a `HookResult`. Wrap risky logic in `try/except` and return `HookResult(action="continue")` on failure unless blocking is the explicit intent. Also: `suppress_output` only hides the *hook's* own output, not tool output.

**Related**: Hook protocol (§1.3), Coordinator's `process_hook_result` (§1.2), Orchestrator (§1.3).

---

## 1.3 The five module protocols

All five contracts are Python `Protocol` classes with `@runtime_checkable` — modules satisfy them by **structural typing** (duck typing). No base class to inherit, no registry to register with: if your object has the right attributes and methods, it is a Tool (or Provider, or Orchestrator, etc.). Source: `python/amplifier_core/interfaces.py`. The Rust traits in `crates/amplifier-core/src/traits.rs` are the polyglot mirror; for Python authors the Protocols are authoritative.

### Tool

A **Tool** gives an agent a capability — read a file, run a shell command, fetch a URL, spawn a sub-agent. Protocol:

```python
@runtime_checkable
class Tool(Protocol):
    @property
    def name(self) -> str: ...           # snake_case, unique among mounted tools
    @property
    def description(self) -> str: ...    # human-readable; the LLM sees this
    @property
    def input_schema(self) -> dict[str, Any]:
        return {}                        # JSON Schema for params; default {} for compat
    async def execute(self, input: dict[str, Any]) -> ToolResult: ...
```

`ToolResult` (from `amplifier_core.models`):

```python
class ToolResult(BaseModel):
    success: bool = True
    output: Any | None = None             # typically str or dict
    error: dict[str, Any] | None = None   # structured, e.g. {"message": "...", "type": "..."}
```

A complete minimal Tool module:

```python
from amplifier_core.interfaces import Tool
from amplifier_core.models import ToolResult

class EchoTool:
    @property
    def name(self) -> str: return "echo"
    @property
    def description(self) -> str: return "Echo input back as output."
    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        }
    async def execute(self, input: dict) -> ToolResult:
        text = input.get("text")
        if not isinstance(text, str):
            return ToolResult(success=False, error={"message": "text required", "type": "ValueError"})
        return ToolResult(success=True, output=text)

async def mount(coordinator, config):
    tool = EchoTool()
    await coordinator.mount("tools", tool, name=tool.name)
    return None  # no cleanup needed
```

```toml
# pyproject.toml
[project.entry-points."amplifier.modules"]
tool-echo = "amplifier_module_tool_echo:mount"
```

**Pitfalls.** Tools should never crash the kernel — wrap `execute` in `try/except` and return `ToolResult(success=False, error=...)`. The orchestrator translates `success=False` into a tool-result message the LLM can see and react to.

**Related**: Orchestrator (which calls `execute`), Hook (`tool:pre` / `tool:post`).

### Provider

A **Provider** is an LLM backend. It translates between Amplifier's unified message format (`ChatRequest` / `ChatResponse`) and a vendor-specific API.

```python
@runtime_checkable
class Provider(Protocol):
    @property
    def name(self) -> str: ...
    def get_info(self) -> ProviderInfo: ...                    # id, capabilities, defaults
    async def list_models(self) -> list[ModelInfo]: ...        # may be empty
    async def complete(self, request: ChatRequest, **kwargs) -> ChatResponse: ...
    def parse_tool_calls(self, response: ChatResponse) -> list[ToolCall]: ...
```

Why a custom format instead of vendor SDK types directly: the kernel preserves content blocks (`Text`, `Thinking`, `RedactedThinking`, `ToolCall`, `ToolResult`, `Image`, `Reasoning`) across vendors so an orchestrator can swap providers without losing structure. `ThinkingBlock.signature` in particular must round-trip — it's how the Anthropic API verifies extended-thinking continuity. `mount()` may return `None` to gracefully degrade (e.g. missing API key); the session simply runs without that provider.

**Related**: Orchestrator (the only module that calls Providers), `docs/specs/PROVIDER_SPECIFICATION.md` for cost tiers, capabilities taxonomy, and degradation handling.

### Orchestrator

An **Orchestrator** implements the agent execution loop — the strategy that turns a prompt into a final response by calling providers, dispatching tools, and managing context.

```python
@runtime_checkable
class Orchestrator(Protocol):
    async def execute(
        self,
        prompt: str,
        context: ContextManager,
        providers: dict[str, Provider],
        tools: dict[str, Tool],
        hooks: HookRegistry,
        **kwargs: Any,                # kernel injects coordinator=...
    ) -> str: ...
```

The orchestrator is the largest piece of policy in the system. Its required event-emission contract from `ORCHESTRATOR_CONTRACT.md`:

- `execution:start` with `{prompt}` at the very beginning of `execute()`.
- `execution:end` with `{response, status}` on **all** exit paths — success, error, cancellation.
- `orchestrator:complete` with `{orchestrator, turn_count, status}` at the end.
- Standard per-step events: `provider:request`/`provider:response`, `tool:pre`/`tool:post`, `tool:error`.

It must also process `HookResult` actions from emitted events: `deny` aborts the operation, `modify` replaces the data, `inject_context` adds a message to context, `ask_user` requests approval (via the optional approval system). The kernel passes `coordinator=` through `**kwargs`; orchestrators typically use `coordinator.process_hook_result(...)` to centralize this logic.

**Pitfalls.** Don't forget the `execution:end` emission in error paths — it's how observers know a turn ended at all. Also: implement an iteration cap, or runaway tool loops will pin a session forever.

**Related**: ContextManager (asks for messages), Tool (called per turn), Provider (called per turn), Hook (every step emits).

### ContextManager

A **ContextManager** owns memory policy: what messages exist, what to return for an LLM request, and how to compact when budgets are exceeded.

```python
@runtime_checkable
class ContextManager(Protocol):
    async def add_message(self, message: dict[str, Any]) -> None: ...
    async def get_messages_for_request(
        self,
        token_budget: int | None = None,
        provider: Any | None = None,        # used to derive budget dynamically
    ) -> list[dict[str, Any]]: ...
    async def get_messages(self) -> list[dict[str, Any]]: ...      # raw, uncompacted
    async def set_messages(self, messages: list[dict[str, Any]]) -> None: ...
    async def clear(self) -> None: ...
```

The mechanism/policy split is sharp here. The orchestrator is the mechanism that asks for messages before each LLM call; the context manager is the policy that decides whether to truncate, summarize, score-and-keep, or anything else. Two invariants from `CONTEXT_CONTRACT.md`:

1. **Compaction is non-destructive.** `get_messages_for_request()` returns a possibly-compacted *view*; `get_messages()` always returns the full history. Internal state must not be mutated by compaction. This preserves transcripts, enables session resume, and lets observers see what really happened.
2. **Tool pairs stay together.** A `tool_call` (assistant message with `tool_calls`) and its matching `tool` result must never be separated by compaction — splitting them produces vendor API errors.

**Related**: Orchestrator (the only caller), Hook (`context:pre_compact` / `context:post_compact`).

### HookHandler (the protocol)

The **HookHandler** protocol is what makes an object a registerable hook, distinct from the runtime hook concept (an active registration on a specific event). The protocol is one async-callable method:

```python
@runtime_checkable
class HookHandler(Protocol):
    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult: ...
```

A plain `async def` function satisfies the protocol — `__call__` is just how Python spells "callable." Hook *modules* package one or more such handlers and register them in their `mount()`:

```python
async def mount(coordinator, config):
    handlers = [
        coordinator.hooks.register("tool:pre", validate_tool_input, priority=10),
        coordinator.hooks.register("tool:post", run_linter,           priority=20),
    ]
    def cleanup():
        for unregister in handlers:
            unregister()
    return cleanup
```

Register custom event names via the `observability.events` contribution channel so other modules can discover them.

**Related**: HookResult, Event (§1.2), `docs/HOOKS_API.md` for the full action/field reference.

---

## 1.4 Putting it together

Here is the smallest interesting program that exercises every concept in this chapter. Read the inline comments — they map each line to a term.

```python
import asyncio
from amplifier_core import AmplifierSession   # → Rust-backed session via PyO3 bridge

# A Mount Plan: pure mechanism — a dict, no policy decisions baked in.
# Every entry is a Module ID; the kernel will resolve them via entry points
# (or `source` URIs in a real bundle).
config = {
    "session": {
        "orchestrator": "loop-basic",      # Module ID — implements the Orchestrator protocol
        "context":      "context-simple",  # Module ID — implements the ContextManager protocol
    },
    "providers": [
        {"module": "provider-anthropic"}   # implements the Provider protocol
    ],
    "tools": [
        {"module": "tool-filesystem"},     # implements the Tool protocol
        {"module": "tool-bash"},
    ],
    "hooks": [
        {"module": "hooks-logging"},       # implements the HookHandler protocol(s)
    ],
}

async def main():
    # Construction validates the plan structurally and creates the Coordinator.
    # The Coordinator owns the HookRegistry, CancellationToken, mount points,
    # and capability registry. session_id is auto-generated; parent_id is None
    # because this is a top-level session (not a fork).
    async with AmplifierSession(config) as session:
        # Inside __aenter__, initialize() runs:
        #   1. Resolve each Module ID → import the package → call mount(coordinator, config)
        #   2. Each mount() attaches its module under a mount point:
        #        "session" (orchestrator + context), "providers", "tools", "hooks"
        #   3. on_session_ready() callbacks fire (Python-only, after all phases)
        #   4. Emit "session:start" Event
        #
        # execute() runs the orchestrator's loop. Per turn:
        #   provider:request → provider.complete() → provider:response →
        #   for each tool_call: tool:pre → tool.execute() → tool:post
        #   Hooks observe each Event and may return HookResult(action=...) to
        #   deny / modify / inject_context / ask_user.
        response: str = await session.execute("What's in /tmp?")
        print(response)
    # __aexit__ → cleanup() runs each module's returned cleanup callable in
    # reverse mount order, then emits "session:end".

asyncio.run(main())
```

The mechanism/policy split is visible in this snippet: the kernel sees a dict and a prompt, and produces a string. *Which* model, *which* loop, *what* gets logged, *whether* a tool is permitted — all of those are decided by the modules referenced by Module IDs in the config. Swap `"loop-basic"` for `"loop-streaming"` and the agent streams; swap `"hooks-logging"` for `"hooks-logging" + "hooks-redaction"` and secrets are scrubbed. The kernel never changes.

To turn this single session into a fork, an app layer would deep-merge `config` with an agent overlay (from `config["agents"]["<name>"]`), build a child `AmplifierSession(child_config, parent_id=session.session_id, session_id=f"{session.session_id}-child")`, and `await child.initialize()`. The kernel would emit `session:fork` and stamp `parent_id` on every child event — see `Chapter 3` for the policy that drives this.

---

## 1.5 Self-check

Try to answer each question without re-reading. If you can't, note the section and revisit it.

1. State the litmus test that distinguishes a kernel mechanism from a module policy. Give one example of each from the kernel's actual surface.
2. After the Rust switchover, where does `from amplifier_core import AmplifierSession` resolve to, and how would you check at runtime which implementation is active?
3. Walk through the four lifecycle phases of a session (`__init__` → `initialize` → `execute` → `cleanup`) and name one Event emitted in each.
4. A module needs a tool registered by another module. Why is `coordinator.register_capability` / `get_capability` (called from `on_session_ready`) preferred over stashing the coordinator in a module-level global?
5. Two hooks fire on `tool:pre` for the same call: handler A returns `HookResult(action="ask_user", ...)`, handler B returns `HookResult(action="inject_context", ...)`. Which wins, and why is precedence designed this way?
6. What two invariants must a `ContextManager` preserve during compaction, and what breaks if either is violated?
7. The `Orchestrator` protocol receives `**kwargs`. What does the kernel inject into it, and why would an orchestrator care?
8. List everything the kernel does *not* do for session forking. Which layer is responsible for those?
