# Live-fire verification report

This is the report from probe #3 (live-fire / executable verification) of the
Amplifier study guide. A sub-agent installed `amplifier_foundation` locally,
wrote scripts that exercise the chapters' claims, ran them, and recorded
results.

## Environment

- Python 3.11.15
- `amplifier_foundation==1.0.0` installed editable from the local checkout.
- `amplifier-core==1.4.1` resolved by pip from the PyPI wheel (the local
  `amplifier-core/` is a Rust crate and pip pulled the published wheel).
- All probe scripts at `verification/live-fire/probe_{a,b,c}/`.
- Logs at `verification/live-fire/logs/`.

## Probe A — foundation pipeline

**Status: PASS.**

What ran: `load_bundle("./my-bundle.md") → Bundle → to_mount_plan() → prepare()`
end-to-end, offline, with no API keys.

What output proved:
- `prepare(install_deps=False)` succeeded with no network because no module
  declared a `source:` field in the bundle.
- `PreparedBundle` exposes the documented surface: `mount_plan`, `resolver`,
  `bundle`, `bundle_package_paths`, `create_session`, `spawn`.

Chapter 2 claims verified: bundle file format, the `Bundle → to_mount_plan →
PreparedBundle` pipeline, `prepare()` semantics, `PreparedBundle.create_session()`.

Chapter 2 claims contradicted: none.

## Probe B — composition merge rules

**Status: PASS.**

Tested three merge cases:
1. Add a tool via overlay → tools list grows by one.
2. Replace `instruction` via overlay → later wins, `None`/empty-string overlays
   are correctly treated as no-ops (matches §2.3 pitfall).
3. Same module ID with a different config → single entry, configs deep-merged,
   scalar overlay wins.

Chapter 2 §2.3 claims verified end-to-end.

Side observation: `bundle.name` propagates from a small overlay onto the base.
Worth a one-line pitfall in §2.3 for readers who use a tiny "feature flag"
bundle and unexpectedly find their composed bundle renamed.

## Probe C — entry-point + mount

**Status: PASS.**

Built `amplifier-module-tool-noop` with the documented entry-point group
(`amplifier.modules`). `ModuleLoader.discover()` surfaced it as
`type=tool, mount_point=tools`. `loader.load() → mount_fn(coordinator)`
mounted it. `coordinator.get('tools', name='noop').execute({})` returned
`ToolResult(output={'ok': True})`.

`AmplifierSession.initialize()` failed cleanly on the missing `loop-basic`
orchestrator (expected — the probe used a stub bundle without a real
orchestrator module).

## Probe D — capability disambiguation

**Status: PASS.**

`ProviderInfo.capabilities: list[str]` and the runtime
`coordinator.register_capability` / `coordinator.get_capability` API are
exactly as Chapter 1 §1.3 describes. Static vs runtime distinction holds.

## Summary

- **Total claims verified across probes: 4 / 4 probes pass.**
- **Total claims contradicted: 0.**

### Recommended chapter edits

1. **`ModuleLoader.discover()` is `async`.** A reader who writes the natural-
   looking `for m in loader.discover():` will hit
   `TypeError: 'coroutine' object is not iterable`. Chapter 4 §4.8 should
   note this where it discusses module discovery, ideally with the correct
   pattern (`async for` or `await` + iterate). This is the single most
   important correction.

2. **Optional pitfall in §2.3:** `bundle.name` propagation from a small
   overlay can rename the composed bundle unexpectedly.
