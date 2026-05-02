"""Probe B: composition merge rules.

Verify Chapter 2 §2.3 merge rules:
- tools merge by module ID (new module appended; same module deep-merges config)
- instruction is replaced wholesale
- providers same-module-id with different configs deep-merge (no duplication)
"""
import asyncio
import json
import sys

from amplifier_foundation import Bundle


def show(label, b):
    print(f"--- {label} ---")
    print("name:", b.name)
    print("instruction:", repr(b.instruction))
    print("providers:")
    print(json.dumps(b.providers, indent=2, default=str))
    print("tools:")
    print(json.dumps(b.tools, indent=2, default=str))
    print()


async def main():
    # Base = probe-a
    base = Bundle(
        name="probe-a",
        version="0.0.1",
        instruction="You are a probe-a session.",
        session={
            "orchestrator": {"module": "loop-basic"},
            "context": {"module": "context-simple"},
        },
        providers=[{"module": "provider-stub", "config": {"latency_ms": 10}}],
        tools=[],
    )

    # B2: ADD a tool
    b2 = Bundle(
        name="add-tool",
        version="0.0.1",
        tools=[{"module": "tool-noop", "config": {"flag": True}}],
    )

    # B3: REPLACE instruction
    b3 = Bundle(
        name="replace-instr",
        version="0.0.1",
        instruction="REPLACED instruction body.",
    )

    # B4: SAME provider id with different config
    b4 = Bundle(
        name="prov-overlay",
        version="0.0.1",
        providers=[
            {"module": "provider-stub", "config": {"latency_ms": 250, "extra": "x"}}
        ],
    )

    print("============ STEP 1: base + b2 (ADD tool) ============")
    r1 = base.compose(b2)
    show("base.compose(b2)", r1)
    assert any(t.get("module") == "tool-noop" for t in r1.tools), "tool-noop missing!"
    print("OK: tool-noop appended.\n")

    print("============ STEP 2: r1 + b3 (REPLACE instruction) ============")
    r2 = r1.compose(b3)
    show("r1.compose(b3)", r2)
    assert r2.instruction == "REPLACED instruction body.", f"unexpected instruction: {r2.instruction!r}"
    print("OK: instruction replaced.\n")

    print("============ STEP 3: r2 + b4 (SAME provider module, diff config) ============")
    r3 = r2.compose(b4)
    show("r2.compose(b4)", r3)
    stub_entries = [p for p in r3.providers if p.get("module") == "provider-stub"]
    print("provider-stub entries count:", len(stub_entries))
    assert len(stub_entries) == 1, f"expected 1 entry, got {len(stub_entries)}: {stub_entries}"
    cfg = stub_entries[0].get("config", {})
    print("merged config:", cfg)
    # Chapter 2 says scalars: later wins. latency_ms=250. extra='x'.
    assert cfg.get("latency_ms") == 250, f"latency_ms should be 250, got {cfg.get('latency_ms')}"
    assert cfg.get("extra") == "x", f"extra should be 'x', got {cfg.get('extra')}"
    print("OK: configs deep-merged (no duplicate entry).\n")

    print("============ STEP 4: ordering + 'later wins' for instruction ============")
    # Compose b3 then a "no instruction" bundle. Should keep r3's because empty instruction is no-op.
    b5 = Bundle(name="no-instr", instruction=None)
    r4 = r3.compose(b5)
    show("r3.compose(b5 with None instr)", r4)
    print("instruction unchanged:", r4.instruction == r3.instruction)
    print()

    # Empty-string instruction should also be no-op per chapter pitfall:
    b6 = Bundle(name="empty-instr", instruction="")
    r5 = r3.compose(b6)
    print("compose with empty-string instruction:")
    print("instruction unchanged:", r5.instruction == r3.instruction)
    print("instruction value:", repr(r5.instruction))


asyncio.run(main())
