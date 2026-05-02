"""Probe C: tool entry-point + mount.

Confirm:
1. tool-noop is registered as an `amplifier.modules` entry point.
2. The kernel's loader can discover and load it.
3. Mounting via ModuleCoordinator works (registers under 'tools' mount point).
4. Optional: try Mount Plan with tool-noop (will need a session — likely fails on missing real provider, fine).
"""
import asyncio
import importlib.metadata as md
import sys

from amplifier_core.coordinator import ModuleCoordinator
from amplifier_core.loader import ModuleLoader
from amplifier_core.models import ToolResult


async def main():
    print("=== Step 1: entry-point discovery via importlib.metadata ===")
    eps = md.entry_points(group="amplifier.modules")
    names = sorted({ep.name for ep in eps})
    print("All amplifier.modules entry points:", names)
    assert "tool-noop" in names, "tool-noop not registered!"
    print("OK: tool-noop discovered.\n")

    print("=== Step 2: kernel ModuleLoader.discover() ===")
    loader = ModuleLoader()
    discovered = await loader.discover()
    discovered_ids = sorted(m.id for m in discovered)
    print("Discovered modules:", discovered_ids)
    noop_info = next((m for m in discovered if m.id == "tool-noop"), None)
    assert noop_info is not None, "ModuleLoader.discover() did not surface tool-noop"
    print("tool-noop ModuleInfo:")
    print("  type:", noop_info.type)
    print("  mount_point:", noop_info.mount_point)
    print("  description:", noop_info.description)
    print()

    print("=== Step 3: Load + mount tool-noop via the kernel loader ===")
    coordinator = ModuleCoordinator()
    # Register the 'tools' mount point so loader can mount tools there.
    # Inspect mount_points behavior: try direct mount through loader first.
    try:
        mount_fn = await loader.load("tool-noop", config={}, coordinator=coordinator)
        print("loader.load returned:", type(mount_fn).__name__)
        # Per kernel contract, mount_fn is an async callable taking the coordinator.
        result = await mount_fn(coordinator)
        print("mount_fn result:", result)
    except Exception as e:
        print("loader.load failed:", type(e).__name__, str(e)[:400])
        # Try direct entry-point invocation
        ep = next(ep for ep in md.entry_points(group="amplifier.modules") if ep.name == "tool-noop")
        loaded_fn = ep.load()
        print("Direct ep.load() ->", loaded_fn)
        await loaded_fn(coordinator, {})

    # Verify tool is discoverable via coordinator.get
    print("\n=== Step 4: coordinator.get('tools', name='noop') ===")
    try:
        tool = coordinator.get("tools", name="noop")
        print("coordinator.get returned:", type(tool).__name__)
        out = await tool.execute({})
        print("tool.execute({}) ->", out)
        assert isinstance(out, ToolResult) and out.output == {"ok": True}
        print("OK: end-to-end mount + execute works.")
    except Exception as e:
        print("coordinator.get failed:", type(e).__name__, str(e)[:400])

    print("\n=== Step 5: Try AmplifierSession with a Mount Plan ===")
    from amplifier_foundation import Bundle
    bundle = Bundle(
        name="probe-c",
        session={
            "orchestrator": {"module": "loop-basic"},
            "context": {"module": "context-simple"},
        },
        tools=[{"module": "tool-noop"}],
    )
    plan = bundle.to_mount_plan()
    print("Mount Plan:", plan)

    try:
        from amplifier_core.session import AmplifierSession
    except Exception as e:
        print("AmplifierSession import failed:", e)
        return

    try:
        session = AmplifierSession(config=plan)
        print("AmplifierSession constructed:", type(session).__name__)
        try:
            await session.initialize()
            print("session.initialize() OK")
        except Exception as e:
            print("session.initialize() failed:", type(e).__name__, str(e)[:500])
    except Exception as e:
        print("AmplifierSession() failed:", type(e).__name__, str(e)[:500])


asyncio.run(main())
