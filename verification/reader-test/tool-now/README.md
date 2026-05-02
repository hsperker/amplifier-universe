# amplifier-module-tool-now

A minimal Amplifier **Tool module**: returns the current UTC time as
ISO-8601.

This is an `amplifier-module-*` repo (one module, one Python package — see
the Amplifier study guide Chapter 4 §4.7 for the naming conventions and
§4.8 for the entry-point mechanism).

## What it provides

| Field         | Value                                        |
| ------------- | -------------------------------------------- |
| Module ID     | `tool-now`                                   |
| Package name  | `amplifier-module-tool-now`                  |
| Import path   | `amplifier_module_tool_now`                  |
| Tool name     | `now`                                        |
| Description   | `Returns the current UTC time as ISO-8601.`  |
| Input schema  | `{ "type": "object", "properties": {} }`     |
| Output shape  | `{ "now": "<ISO-8601 string>" }`             |

## Install

The kernel discovers modules via Python entry points (see Chapter 4 §4.8).
There is no central registry — installing the package is what makes the
module visible to any bundle that lists `module: tool-now`.

```bash
# From this directory:
uv pip install .
# or:
pip install .
```

In normal Amplifier usage you do **not** install module packages by hand:
the bundle's `source:` URI and `amplifier-foundation`'s resolver download
and install them on demand (Chapter 2 §2.5, Chapter 4 §4.9).

## Use it from a bundle

A thin bundle that mounts this tool on top of `foundation` is shipped at
[`bundle/bundle.md`](bundle/bundle.md). Run it the way Chapter 2 §2.7 shows:

```python
import asyncio
from pathlib import Path
from amplifier_foundation import load_bundle

async def main() -> None:
    bundle = await load_bundle("./bundle/bundle.md")
    prepared = await bundle.prepare()
    async with await prepared.create_session(session_cwd=Path.cwd()) as session:
        print(await session.execute("What time is it in UTC right now?"))

asyncio.run(main())
```

Or, with the CLI (Chapter 4 §4.3):

```bash
# Add the bundle (from a published git URL once this repo is hosted), then:
amplifier bundle use now
amplifier run "What time is it in UTC right now?"
```

The agent will call the `now` tool and you will see something shaped like:

```json
{ "now": "2026-05-02T17:42:31.123456+00:00" }
```

## Invoke the tool directly (no LLM)

The `tests/test_tool_now.py` file shows how to mount the module under a
stub coordinator and call `execute({})` — this is the same shape any
non-LLM driver (a script, a benchmark harness, a test) would use.

```bash
python tests/test_tool_now.py
```

You should see `OK: now=...` printed and a zero exit code.

## Conventions

This module follows the conventions documented in the Amplifier study guide:

- Repo type per Ch4 §4.7: `amplifier-module-*` (single Python module).
- Entry-point stanza per Ch4 §4.8: registered under `amplifier.modules`,
  key is the module ID (`tool-now`), value points to the `mount` callable.
- Module ID / package name / import path are three names for the same
  module (Glossary §7) — `tool-now`, `amplifier-module-tool-now`,
  `amplifier_module_tool_now`. Mismatches between these are a known silent
  failure mode.
- `mount(coordinator, config)` registers the tool on the `"tools"` mount
  point per Ch1 §1.2; nothing to clean up, so it returns `None`.
- The Tool protocol is satisfied structurally — no base class — per
  Ch1 §1.3.

## Layout

```
tool-now/
├── README.md                                # this file
├── pyproject.toml                           # entry-point stanza
├── amplifier_module_tool_now/
│   ├── __init__.py
│   └── tool.py                              # NowTool + mount()
├── bundle/
│   └── bundle.md                            # thin bundle that mounts tool-now
└── tests/
    └── test_tool_now.py                     # self-test, no LLM required
```
