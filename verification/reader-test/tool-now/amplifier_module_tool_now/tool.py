"""The `now` Tool: returns the current UTC time as ISO-8601.

Implements the kernel's Tool protocol structurally
(Study guide Chapter 1 §1.3): properties `name`, `description`,
`input_schema`; coroutine `execute(input) -> ToolResult`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# Canonical kernel imports per Chapter 1 §1.3. We fall back to a tiny
# in-process shim so this module's self-test (`tests/test_tool_now.py`)
# can run before `amplifier-core` is installed in the environment.
# In a real deployment the kernel-provided ToolResult is always present —
# Chapter 1 §1.2 makes the kernel a hard runtime dependency.
try:  # pragma: no cover - exercised only when amplifier-core is installed
    from amplifier_core.models import ToolResult  # type: ignore
except Exception:  # pragma: no cover - test-time fallback
    from dataclasses import dataclass, field

    @dataclass
    class ToolResult:  # type: ignore[no-redef]
        """Local fallback mirroring `amplifier_core.models.ToolResult`.

        Field names and defaults match the schema documented in
        Study guide Chapter 1 §1.3 ("Tool"):
            success: bool = True
            output:  Any | None = None
            error:   dict | None = None
        """

        success: bool = True
        output: Any | None = None
        error: dict[str, Any] | None = None


class NowTool:
    """Returns the current UTC time as ISO-8601.

    Satisfies the structural Tool protocol (Chapter 1 §1.3).
    """

    @property
    def name(self) -> str:
        return "now"

    @property
    def description(self) -> str:
        return "Returns the current UTC time as ISO-8601."

    @property
    def input_schema(self) -> dict[str, Any]:
        # No inputs. Default `{}` would also be valid per the protocol,
        # but an explicit object schema is friendlier to LLM tool callers.
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        # Pitfall guidance from Chapter 1 §1.3: never crash the kernel —
        # wrap the body and translate failures into a ToolResult.
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            return ToolResult(success=True, output={"now": now_iso})
        except Exception as exc:  # pragma: no cover - defensive
            return ToolResult(
                success=False,
                error={"message": str(exc), "type": type(exc).__name__},
            )


async def mount(coordinator: Any, config: dict[str, Any]) -> None:
    """Module entry point.

    Contract from Chapter 1 §1.2 ("Mount and mount points"):
      - free function (no `self`),
      - kernel calls it once per module with `(coordinator, config)`,
      - return value is interpreted as cleanup (callable) or `None`.
    This tool has nothing to clean up, so we return `None`.
    """
    tool = NowTool()
    await coordinator.mount("tools", tool, name=tool.name)
    return None
