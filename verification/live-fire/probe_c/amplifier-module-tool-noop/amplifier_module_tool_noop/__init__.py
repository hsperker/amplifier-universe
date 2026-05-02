"""Minimal no-op tool module for entry-point verification."""
from __future__ import annotations

from typing import Any

from amplifier_core.models import ToolResult


class NoopTool:
    """A trivial Tool implementation."""

    @property
    def name(self) -> str:
        return "noop"

    @property
    def description(self) -> str:
        return "Returns {ok: True} regardless of input."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "additionalProperties": True}

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        return ToolResult(success=True, output={"ok": True}, error=None)


async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> None:
    """Mount the noop tool. Entry-point conformant signature.

    The Mount Plan dispatcher calls mount(coordinator, config). We register
    the tool at the 'tools' mount point under the name 'noop'.
    """
    tool = NoopTool()
    await coordinator.mount("tools", tool, name="noop")
