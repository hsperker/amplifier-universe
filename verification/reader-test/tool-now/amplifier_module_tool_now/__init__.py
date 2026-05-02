"""amplifier-module-tool-now — exposes a single Tool (`now`) that returns the
current UTC time as ISO-8601.

The package's `mount` symbol is what the kernel loads via the
`amplifier.modules` entry point declared in `pyproject.toml`.
(Study guide: Chapter 1 §1.2 "Mount and mount points", Chapter 4 §4.8.)
"""

from .tool import NowTool, mount

__all__ = ["NowTool", "mount"]
