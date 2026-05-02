# Friction log — building `tool-now` from the study guide alone

Format: `[CH? §?]  <what I needed>  <what was missing>  <how I resolved it>  <category>`

Categories:
- **chapter-silent** — guide didn't address it, real gap
- **chapter-misleading** — guide said X, source says Y
- **chapter-correct-but-buried** — info exists but I had to hunt
- **false-alarm** — I worried about something the guide actually covered

---

1. `[Ch1 §1.3]` Tool import path for `ToolResult`. Guide gives `from amplifier_core.models import ToolResult` with full schema, but doesn't mention what to do when writing a self-test in an environment where `amplifier-core` isn't installed yet. Resolved by writing a try/except shim that mirrors the documented schema. **chapter-silent** (minor — it's a test-time concern, not a runtime concern).

2. `[Ch1 §1.2]` Cleanup return convention. Guide says "a callable becomes the cleanup; `None` means no cleanup; non-callables are silently ignored." Clear. Returned `None`. **false-alarm** — I checked twice because I expected ambiguity; the guide is precise.

3. `[Ch1 §1.2]` Whether `mount()` must be `async`. Guide's example uses `async def mount(coordinator, config)` and the kernel calls it. Doesn't *explicitly* say "it must be async," but every example is async. I went with async; it would be a real chapter-silent gap if a sync `mount` is also valid (or invalid). **chapter-correct-but-buried** — implied by every example, never stated as a rule.

4. `[Ch4 §4.8]` `pyproject.toml` exact stanza. Guide reproduces a complete real-world `pyproject.toml` from `tool-delegate` including `name`, `version`, `dependencies`, `[project.entry-points."amplifier.modules"]`, `[build-system]`, and `[tool.hatch.build.targets.wheel]`. Copied the shape directly. **false-alarm** — exemplary coverage.

5. `[Ch2 §2.6]` Thin bundle template. Guide shows `amplifier-bundle-recipes/bundle.md` as the canonical thin bundle — could lift the structure straight from there. **false-alarm** — exemplary coverage.

6. `[Ch2 §2.5]` Local `source:` URI for an unpublished module. Guide lists `Local file`, `Local directory`, `Git HTTPS`, `Git + subdirectory`. The local-directory form (`/path/to/bundle/`) is for *bundles*; the guide doesn't separately demonstrate `source:` URIs pointing to local module repos in a `tools:` block. I extrapolated `file:///abs/path/to/module-repo` from the bundle local-file form. **chapter-correct-but-buried** — the URI grammar is shown for bundles; transferring it to module `source:` is straightforward but not spelled out.

7. `[Ch1 §1.3]` `input_schema` default. Guide's protocol shows `def input_schema(self) -> dict: return {}` with comment "default {} for compat." So `{}` is acceptable. I used a populated empty-object schema for friendliness; both are valid. **false-alarm**.

8. `[Ch1 §1.2 / Ch1 §1.3]` What a "stub coordinator" needs to implement for a self-test. Guide describes the `ModuleCoordinator` shape (mount, get, register_capability, hooks, cancellation, etc.) but doesn't show a stub-coordinator pattern for testing modules in isolation. I wrote one based on the documented method signature (`async def mount(self, mount_point, module, name=None) -> None`). Worked first try. **chapter-silent** — testing patterns aren't covered, but the published surface is precise enough that a stub falls out of the spec.

9. `[Ch1 §1.3 + Ch4 §4.8]` Module ID vs package name vs import path mapping. Glossary §7 spells the rule out completely; Ch4 §4.8 reinforces it with `tool-delegate` ↔ `amplifier-module-tool-delegate` ↔ `amplifier_module_tool_delegate`. **false-alarm** — explicitly addressed in two places, including a callout that mismatches are the most common silent failure.

10. `[Ch2 §2.6]` Whether the bundle file needs a `session:`/`providers:` section when it `includes: foundation`. Implicitly answered by `recipes/bundle.md` (it doesn't), but the answer is "no, foundation supplies them — that's the point of the thin pattern." **chapter-correct-but-buried** — example does the work, no prose statement.

11. `[Ch2 §2.4]` `@foundation:context/shared/common-system-base.md` in a bundle body. Guide explicitly says foundation registers the `foundation` namespace and that `@mention` resolves through `source_base_paths`. Used directly. **false-alarm**.

12. `[Ch1 §1.2]` `cleanup` "no-op" cases. Guide says `None` is OK; I noted in a comment that I considered a no-op `lambda: None` for symmetry but the guide's preferred shape for "nothing to clean up" is `None`. **false-alarm**.

13. `[Ch4 §4.8]` `requires-python` choice. Guide doesn't say. I picked `>=3.11` to match modern type-syntax (`dict | None`) used in the guide's own snippets. **chapter-silent** — minor.

14. `[Ch4 §4.8]` `dependencies = ["amplifier-core>=1.2.1"]` exact pin. Guide reproduces the same line from `tool-delegate`'s `pyproject.toml` and notes "some modules omit even the `amplifier-core` dependency on the assumption that the host environment provides it." Copied the more conservative form. **false-alarm**.

15. `[Ch1 §1.3]` `ToolResult.output` type. Guide says "typically str or dict." Output spec for this task is `{"now": "<iso>"}`, a dict. **false-alarm**.

---

## Tallies

- **chapter-silent**: 3  (testing-without-amplifier-core, stub-coordinator pattern, requires-python choice)
- **chapter-misleading**: 0
- **chapter-correct-but-buried**: 3  (sync vs async mount, local module `source:` URI form, "no session/providers needed" only shown by example)
- **false-alarm**: 9

Total: 15 entries.

## Subjective verdict

The chapters are tightly scoped to *the running system* (kernel + composition + authoring + CLI) and almost everything I needed for the *artifact* itself was either named, defined, or shown by a worked example with the right shape. Where I had to extrapolate, the extrapolation was always small and the documented surface was precise enough that the extrapolation was unambiguous. The single real gap is the absence of any "how to test a module in isolation" pattern — there is no stub-coordinator example, and a real test environment usually doesn't have the kernel installed. The guide assumes the kernel is always present, which is fine for end-to-end docs but leaves module authors to invent their own unit-test pattern.

The single most important gap: **no testing/scaffolding chapter for module authors.** The guide tells you how to *write* a module, *publish* a module, and *run* a module inside a session, but not how to *test* one in an isolated test process. Chapter 4 §4.10 mentions `amplifier module dev test <module-id>` exists but doesn't show what a test file looks like.

The single most surprising correctness issue: **none.** The chapter-shown shape of `ToolResult`, the `mount()` signature, the entry-point stanza, and the thin-bundle pattern all matched what I needed exactly. I did not have to consult source code at any point. (The fallback `try/except` import for `ToolResult` is a test-environment convenience, not a correctness fix.)
