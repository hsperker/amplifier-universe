"""Self-test for `amplifier-module-tool-now`.

What this exercises
-------------------
- That the package's `mount(coordinator, config)` runs and registers a tool
  under the `"tools"` mount point with the correct name (Chapter 1 §1.2).
- That the registered object satisfies the documented Tool protocol shape
  (Chapter 1 §1.3): properties `name`, `description`, `input_schema`;
  coroutine `execute(input) -> ToolResult`.
- That `await execute({})` returns `success=True` and an `output["now"]`
  string that parses as an ISO-8601 timestamp in UTC.

What it does NOT exercise
-------------------------
- No live LLM, no provider, no orchestrator. We don't even build a Mount
  Plan — we just stub the `coordinator.mount(...)` surface the kernel
  exposes to a module's `mount()` (per Chapter 1 §1.2) and observe what
  the module hands back.

Run as either `pytest tests/test_tool_now.py` or `python tests/test_tool_now.py`.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Make the in-repo package importable without an install step.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from amplifier_module_tool_now import mount  # noqa: E402


class StubCoordinator:
    """Captures `await coordinator.mount("tools", tool, name=...)` calls.

    The kernel's real ModuleCoordinator (Chapter 1 §1.2) has many more
    methods (hooks, capabilities, cancellation, contributions). Our module
    only touches `mount(...)`, so the stub only implements that — which is
    the whole point of the kernel's "modules don't import each other"
    seam.
    """

    def __init__(self) -> None:
        self.mounted: dict[tuple[str, str | None], Any] = {}

    async def mount(self, mount_point: str, module: Any, name: str | None = None) -> None:
        self.mounted[(mount_point, name)] = module


async def _run() -> None:
    coordinator = StubCoordinator()

    # Drive the kernel's job: call mount(coordinator, config).
    cleanup = await mount(coordinator, {})
    assert cleanup is None, "tool-now declares no cleanup; mount() should return None"

    # The module must have registered a tool named "now" on the "tools" point.
    key = ("tools", "now")
    assert key in coordinator.mounted, (
        f"expected a tool registered at {key!r}; got {list(coordinator.mounted)!r}"
    )
    tool = coordinator.mounted[key]

    # Structural Tool protocol (Chapter 1 §1.3).
    assert tool.name == "now"
    assert tool.description == "Returns the current UTC time as ISO-8601."
    schema = tool.input_schema
    assert isinstance(schema, dict) and schema.get("type") == "object"

    # Execute and check the output contract.
    result = await tool.execute({})
    assert result.success is True, f"unexpected error: {result.error!r}"
    assert isinstance(result.output, dict), f"expected dict output, got {result.output!r}"
    assert "now" in result.output, f"expected key 'now', got {list(result.output)!r}"

    iso = result.output["now"]
    assert isinstance(iso, str) and iso, "expected non-empty ISO-8601 string"
    # Round-trip through datetime to confirm it really is ISO-8601.
    parsed = datetime.fromisoformat(iso)
    assert parsed.utcoffset() is not None, f"expected timezone-aware UTC: {iso!r}"
    assert parsed.utcoffset().total_seconds() == 0, f"expected UTC offset 0: {iso!r}"

    print(f"OK: now={iso}")


def test_tool_now() -> None:
    """pytest entry point."""
    asyncio.run(_run())


if __name__ == "__main__":
    asyncio.run(_run())
