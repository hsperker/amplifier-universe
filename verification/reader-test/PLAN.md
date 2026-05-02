# Plan — `tool-now` module + thin bundle

## Naming (per Chapter 4 §4.7, §4.8 and Glossary §7)

- Module ID:        `tool-now`
- Package name:     `amplifier-module-tool-now`
- Import path:      `amplifier_module_tool_now`
- Bundle repo name (conceptual): `amplifier-bundle-now` (a thin bundle that mounts `tool-now`)

## Repo layout (mirrors `amplifier-module-tool-delegate` per Ch4 §4.8)

```
verification/reader-test/tool-now/
├── README.md                                        # one-page docs
├── pyproject.toml                                   # entry-point stanza
├── amplifier_module_tool_now/
│   ├── __init__.py                                  # exposes mount()
│   └── tool.py                                      # NowTool + mount()
├── bundle/
│   └── bundle.md                                    # thin bundle, includes foundation, mounts tool-now
└── tests/
    └── test_tool_now.py                             # mounts under stub coordinator, asserts shape
```

## Contracts I'll implement

### Tool (Chapter 1 §1.3)

- `name = "now"`
- `description = "Returns the current UTC time as ISO-8601."`
- `input_schema = {"type": "object", "properties": {}}`
- `async def execute(input: dict) -> ToolResult`
  - returns `ToolResult(success=True, output={"now": "<iso>"})`

### `mount(coordinator, config)` (Chapter 1 §1.2 "Mount and mount points")

- Build `NowTool()`
- `await coordinator.mount("tools", tool, name=tool.name)`
- Return `None` (no cleanup needed) — or a no-op cleanup callable

### pyproject.toml entry point (Chapter 4 §4.8 — copy the exact stanza)

```toml
[project.entry-points."amplifier.modules"]
tool-now = "amplifier_module_tool_now:mount"
```

## Bundle (Chapter 2 §2.6 "thin bundle pattern")

```markdown
---
bundle:
  name: now
  version: 0.1.0
  description: Adds tool-now (UTC ISO-8601 timestamp) to a session.

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main

tools:
  - module: tool-now
    source: file:///home/user/amplifier-universe/verification/reader-test/tool-now
---

# Now Tool

Adds the `now` tool, which returns the current UTC time as ISO-8601.
```

## Self-test (Chapter 1 §1.3 — exercises `Tool` protocol; no LLM)

- Stub coordinator class that implements `async def mount(mount_point, module, name=None)` and stashes by `(mount_point, name)`.
- Call the package's `mount(coordinator, {})`.
- Assert the registered tool's `name == "now"`, `description` matches, `await tool.execute({})` returns a `ToolResult` with `success=True` and an ISO-8601 `output["now"]`.
- Re-parse with `datetime.fromisoformat` to confirm shape (and that it's UTC).

## Open questions / things I'll have to extrapolate

- The chapters describe `mount()` as an `async def` returning a cleanup callable or `None`. They do not show the exact ToolResult import path I should use *outside the foundation install*; Chapter 1 shows `from amplifier_core.models import ToolResult` and `from amplifier_core.interfaces import Tool` — I'll use those imports and document the runtime assumption in the README.
- Chapters do not show a complete bundle-only repo with module + bundle + tests in the same folder. I'll use the `amplifier-bundle-recipes` shape from Chapter 2 §2.6 for `bundle.md`, and the `amplifier-module-tool-delegate` shape from Chapter 4 §4.8 for the module package.
- Chapters do not show how to write a self-test against a stub coordinator. I'll synthesize one from the Coordinator's stated interface (Ch1 §1.2).
