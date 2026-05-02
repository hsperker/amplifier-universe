"""Probe A: validate Bundle -> compose -> prepare -> Mount Plan pipeline."""
import asyncio
import json
import os
import sys
from pathlib import Path

from amplifier_foundation import load_bundle, Bundle


async def main():
    here = Path(__file__).parent
    src = str(here / "my-bundle.md")
    print(f"Loading: {src}")
    b = await load_bundle(src)

    print("\n=== Bundle (after load_bundle) ===")
    print("type:", type(b).__name__)
    print("name:", getattr(b, "name", None))
    print("version:", getattr(b, "version", None))
    print("description:", getattr(b, "description", None))
    print("instruction:", repr(getattr(b, "instruction", None)))
    print("session:", getattr(b, "session", None))
    print("providers:", getattr(b, "providers", None))
    print("tools:", getattr(b, "tools", None))
    print("hooks:", getattr(b, "hooks", None))
    print("agents:", getattr(b, "agents", None))
    print("context:", getattr(b, "context", None))
    print("includes:", getattr(b, "includes", None))
    print("base_path:", getattr(b, "base_path", None))
    print("source_base_paths:", getattr(b, "source_base_paths", None))
    print("dataclass keys:", list(b.__dict__.keys()))

    print("\n=== to_mount_plan() ===")
    has_to_mount = hasattr(b, "to_mount_plan")
    print("has to_mount_plan:", has_to_mount)
    if has_to_mount:
        plan = b.to_mount_plan()
        print("Mount Plan keys:", sorted(plan.keys()))
        print("Mount Plan JSON:")
        print(json.dumps(plan, indent=2, default=str))
    else:
        plan = None

    print("\n=== prepare() ===")
    try:
        prepared = await b.prepare(install_deps=False)
        print("PreparedBundle type:", type(prepared).__name__)
        print("PreparedBundle attrs:", [a for a in dir(prepared) if not a.startswith("_")])
        print("mount_plan:", getattr(prepared, "mount_plan", None))
        print("resolver:", getattr(prepared, "resolver", None))
    except Exception as e:
        print("prepare() FAILED with:", type(e).__name__, str(e)[:600])


asyncio.run(main())
