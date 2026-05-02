# Chapter 2 — The Composition Layer

`amplifier-foundation` is the bridge between human-friendly Markdown files and the kernel's Mount Plan. A Mount Plan (Chapter 1) is the dictionary the kernel ingests; a **Bundle** is a composable, shareable, version-controllable artifact that *produces* a Mount Plan. Foundation adds two things on top of the kernel: a file format (YAML frontmatter + Markdown body) and a composition algebra (`includes:` + `compose()`). It does **not** add a new runtime — `bundle.to_mount_plan()` returns the same dict shape Chapter 1 described.

## Concepts covered

- **Bundle** and its ten sections (`bundle`, `includes`, `session`, `providers`, `tools`, `hooks`, `agents`, `context`, `instruction`, `spawn`)
- **Compose** (`base.compose(overlay)`) and per-section merge rules
- **Includes** (`includes:`)
- **Prepare** / **PreparedBundle**
- **Root bundle** vs **Nested bundle** (`is_root`)
- **Namespace** (from `bundle.name`)
- **@Mention** (`@namespace:path`)
- **Thin bundle pattern**
- **Source URI** (local path, `git+https://…@ref#subdirectory=…`)
- **BundleRegistry**

---

## 2.1 From Mount Plan to Bundle

A kernel Session needs a Mount Plan. Hand-writing Mount Plans in Python works, but they aren't shareable, diffable, or layerable. Bundles solve those three problems and nothing else.

The end-to-end pipeline:

```
Source URI ──► load_bundle() ──► Bundle ──► compose(overlay) ──► Bundle
                                                                    │
                                                         to_mount_plan() │ (or prepare())
                                                                    ▼
                                                           Mount Plan / PreparedBundle
                                                                    │
                                                         create_session() │
                                                                    ▼
                                                            AmplifierSession
```

Two key separations to keep in mind throughout this chapter:

1. **Mount plans are required; bundles are optional.** AmplifierSession accepts a Mount Plan dict directly. Bundles exist for sharing and remixing.
2. **A Bundle is data, a PreparedBundle is runnable.** Loading a bundle does not download modules or install dependencies — that happens in `prepare()`.

A complete tiny example, end-to-end:

```python
from amplifier_foundation import load_bundle

foundation = await load_bundle("git+https://github.com/microsoft/amplifier-foundation@main")
provider   = await load_bundle("./providers/anthropic.yaml")
composed   = foundation.compose(provider)        # Bundle + Bundle = Bundle
prepared   = await composed.prepare()            # Downloads modules, returns PreparedBundle
async with await prepared.create_session() as session:
    print(await session.execute("Hello!"))
```

---

## 2.2 Bundle anatomy

A Bundle is a Markdown file with YAML frontmatter, or a YAML-only file. Every bundle has a name and a version; everything else is optional.

```markdown
---
bundle:
  name: my-bundle
  version: 1.0.0
  description: What this bundle provides

includes:
  - bundle: foundation
  - bundle: my-bundle:behaviors/x

session:
  orchestrator: {module: loop-streaming, source: git+https://...}
  context:      {module: context-simple, source: git+https://...}

providers:
  - module: provider-anthropic
    source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
    config: {default_model: claude-sonnet-4-5}

tools:
  - module: tool-filesystem
    source: git+https://...

hooks:
  - module: hooks-streaming-ui
    source: git+https://...

agents:
  include:
    - my-bundle:bug-hunter

context:
  include:
    - my-bundle:context/instructions.md

spawn:
  exclude_tools: [tool-task]
---

# System Instructions

Body becomes the system instruction. Reference docs with @mentions:
@my-bundle:context/instructions.md
```

### Section reference

The frontmatter has ten recognized sections. Nine populate the Bundle dataclass directly; `includes:` is consumed by the loader.

| Section       | Type                    | Goes to Mount Plan? | Purpose |
|---------------|-------------------------|---------------------|---------|
| `bundle`      | metadata (name/version) | No                  | Identifies the bundle; `name` becomes the namespace. |
| `includes`    | list of source refs     | No (resolved first) | Bundles to layer in *before* this one. |
| `session`     | dict                    | Yes                 | Orchestrator + context-manager modules (the "five protocols" two slots). |
| `providers`   | list of module specs    | Yes                 | LLM backends. |
| `tools`       | list of module specs    | Yes                 | Agent-callable capabilities. |
| `hooks`       | list of module specs    | Yes                 | Observability and control. |
| `agents`      | dict (or `include:` list) | Yes               | Sub-agent configurations for delegation. |
| `context`     | dict (or `include:` list) | No (loaded separately) | Files to inject into the system prompt. |
| `instruction` | Markdown body           | No (injected later) | The system prompt text. |
| `spawn`       | dict                    | Yes                 | Tool-inheritance policy for spawned sub-sessions. |

Three of these deserve explicit treatment:

**`includes:`** is *not* merged — it is *resolved*. When a bundle is loaded, each entry in `includes:` is loaded as its own bundle and composed into the result *before* this bundle's own sections are applied. By the time you call `compose()` on a loaded bundle, `includes` has already been consumed. (See §2.3 for what "before" means with respect to merge order, and §2.4 for how `includes:` items reach the loader.)

**`instruction:`** is the Markdown body of `bundle.md`, not a YAML key. `load_bundle()` runs `parse_frontmatter()` and assigns the body to `Bundle.instruction`. Composition replaces it wholesale (see §2.3). If you keep instructions in a separate file, prefer `@mentions` from a *thin* body (§2.6).

**`spawn:`** declares what spawned sub-agents inherit. Two shapes:

```yaml
spawn:
  exclude_tools: [tool-task]      # Allow everything except these
# OR
spawn:
  tools: [tool-filesystem, tool-bash]   # Allowlist
```

A common pattern is `exclude_tools: [tool-task]` so spawned agents cannot themselves spawn — see Chapter 3 §spawn for the full discussion.

The remaining sections (`session`, `providers`, `tools`, `hooks`, `agents`, `context`) carry the same shape as their Mount Plan counterparts from Chapter 1. The difference is what `compose()` does when two bundles both declare them.

---

## 2.3 Composition and merge rules

`Bundle.compose(*others)` returns a *new* Bundle merging `self` with each subsequent bundle. **Order matters: later wins.** The base call form is `base.compose(overlay)` — read it as "apply overlay on top of base."

```python
result = base.compose(overlay)        # overlay overrides base
result = base.compose(o1, o2, o3)     # equivalent to ((base + o1) + o2) + o3
```

The merge rules are per-section:

| Section         | Rule                  | Effect |
|-----------------|-----------------------|--------|
| `session`       | **Deep merge**        | Nested dicts merged recursively; later wins for scalars. |
| `spawn`         | **Deep merge**        | Same as `session`. |
| `providers`     | **Merge by module ID**| Same `module:` key → configs deep-merged; new IDs appended. |
| `tools`         | **Merge by module ID**| Same as providers. |
| `hooks`         | **Merge by module ID**| Same as providers. |
| `agents`        | **Replace by name**   | `result.agents.update(other.agents)` — same agent name = later wins. |
| `context`       | **Accumulate**        | Each bundle's entries are added under namespace-prefixed keys. No collision. |
| `instruction`   | **Replace**           | If `other.instruction` is non-empty, it replaces. |
| `bundle.name`/`version`/`description` | **Later wins** | The composed bundle adopts the overlay's metadata if set. |

The "merge by module ID" rule is the one beginners get wrong. It does not mean "list union." It means: scan the existing list for an entry with the same `module:` value; if found, deep-merge `config` into the existing one; if not, append.

### Worked example

Base:

```python
base = Bundle(
    name="base",
    session={
        "orchestrator": {"module": "loop-basic"},
        "context":      {"module": "context-simple", "config": {"max_tokens": 100000}},
    },
    providers=[{"module": "provider-mock", "config": {"debug": False}}],
    tools=[{"module": "tool-filesystem"}, {"module": "tool-bash"}],
    instruction="Base instructions.",
)
```

Overlay:

```python
overlay = Bundle(
    name="overlay",
    session={
        "context": {"config": {"max_tokens": 200000, "auto_compact": True}},
    },
    providers=[
        {"module": "provider-mock",      "config": {"debug": True}},                  # update
        {"module": "provider-anthropic", "config": {"default_model": "claude-sonnet-4-5"}},  # add
    ],
    tools=[{"module": "tool-web"}],            # add
    instruction="Overlay instructions.",       # replace
)
```

`base.compose(overlay)`:

| Field                       | Result |
|-----------------------------|--------|
| `session.orchestrator`      | `{"module": "loop-basic"}` (preserved from base — overlay didn't touch it) |
| `session.context`           | `{"module": "context-simple", "config": {"max_tokens": 200000, "auto_compact": True}}` (deep-merged) |
| `providers[0]` (provider-mock)     | `{"module": "provider-mock", "config": {"debug": True}}` (config deep-merged) |
| `providers[1]` (provider-anthropic) | appended |
| `tools`                     | `[tool-filesystem, tool-bash, tool-web]` (filesystem/bash preserved, web appended) |
| `instruction`               | `"Overlay instructions."` (replaced) |

### Pitfalls

- **Wrong order.** `overlay.compose(base)` makes *base* the overlay. The caller is the base; arguments are layered on top.
- **Empty strings count as "not set."** Composition only replaces `instruction` and `description` when the overlay's value is non-empty; `version` is replaced only if the overlay's `version` is truthy.
- **`includes:` does not appear in merge rules** because it is resolved at load time, not at compose time. The bundles named in `includes:` have already been composed into the bundle you are now composing.
- **Same module, different sources.** Merge-by-ID only looks at `module:`. Two entries with the same `module:` but different `source:` will deep-merge — the later `source:` wins. This is almost never what you want; if you need two distinct providers of the same module, give them different module names.

---

## 2.4 Includes, namespaces, and @mentions

`includes:` is how a bundle declares "first, load these, then me." The loader resolves each include into a Bundle, composes them into a result in declared order, then composes *this* bundle on top.

```yaml
includes:
  - bundle: foundation                                   # registry name
  - bundle: ./bundles/local-overlay.md                   # local path
  - bundle: git+https://github.com/org/bundle@main       # git URL
  - bundle: my-bundle:behaviors/foo                      # namespace:path
```

So a bundle with three includes effectively becomes:

```
included[0].compose(included[1]).compose(included[2]).compose(self)
```

This means **the bundle that declares the `includes:` always wins last** — it is the overlay on top of everything it includes.

### Namespace

When a bundle loads, its `bundle.name` becomes a **namespace** registered in the BundleRegistry. The namespace is what makes `@mention` resolution and `namespace:path` includes work. Critically:

- The namespace is always `bundle.name` from YAML frontmatter.
- It is **never** derived from the directory name, file name, or git repo URL.

A bundle living at `https://github.com/microsoft/amplifier-bundle-recipes` whose frontmatter says `name: recipes` registers the namespace `recipes`, not `amplifier-bundle-recipes`.

### Root bundle vs nested bundle

When the registry loads a bundle, it asks: "is there a `bundle.md` or `bundle.yaml` *above* this file in the directory tree?"

| Term            | Definition                                                                                                                                | `is_root` |
|-----------------|-------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| **Root bundle** | A `/bundle.md` or `/bundle.yaml` at the root of a repo or directory tree. Establishes the namespace and root path for resolution.         | `True`    |
| **Nested bundle** | Any bundle reached via `#subdirectory=` or `namespace:path`, located underneath a root bundle. Shares the root's namespace.            | `False`   |

The practical implication: `behaviors/recipes.yaml` inside `amplifier-bundle-recipes` is a *nested* bundle. When loaded, it does **not** register a fresh `recipes-behavior` namespace at the registry root — it shares the `recipes` namespace established by the repo's `/bundle.md`. Path lookups from inside it resolve relative to its own location (`behaviors/`), not the repo root.

The cleanest mental model is the structural-vs-conventional distinction:

- **Structural** = how the loader sees it (`is_root=True/False`).
- **Conventional** = how authors organize a repo (root-bundle vs standalone-bundle vs behavior-bundle).

A file at `/bundles/with-anthropic.yaml` is **structurally nested** (there is a root `bundle.md` above it), but **conventionally a "standalone bundle"** (it is meant to be loaded and used directly). These two classifications are independent.

### @Mention resolution

In a Markdown body (or a context file), `@namespace:path` injects the file at `<namespace's base_path>/<path>` inline at instruction-loading time.

```markdown
See @foundation:context/shared/common-system-base.md for the shared system base.
```

The resolution flow:

1. `compose()` records each contributing bundle's `base_path` under its `name` in `self.source_base_paths`.
2. `PreparedBundle` exposes a mention resolver that, on encountering `@namespace:path`, looks up `source_base_paths[namespace]` and reads `<base_path>/<path>` from disk.
3. The file content is loaded and prepended to the instruction as a `<context_file>` block.

**Worked example.** Suppose foundation's repo lives at `/cache/amplifier-foundation/` after a git fetch, and your bundle.md says:

```markdown
@foundation:context/shared/common-system-base.md
```

The resolver:
1. Looks up `"foundation"` in `source_base_paths` → `/cache/amplifier-foundation/`.
2. Joins with the path → `/cache/amplifier-foundation/context/shared/common-system-base.md`.
3. Reads the file. (Failure to read raises a clear error pointing to the path.)

### Two syntaxes — do not confuse them

There are two reference syntaxes and they have different semantics. Mixing them is the single most common source of "context isn't loading" bugs.

| Where you write it             | Syntax                  | Composition behavior                                |
|--------------------------------|-------------------------|-----------------------------------------------------|
| Markdown body                  | `@namespace:path` (with `@`) | **Replaces** with file content; stays bound to *this* instruction. |
| YAML `context.include` / `agents.include` | `namespace:path` (no `@`, called a *soft reference*) | **Accumulates** during compose; propagates to including bundles. |

A behavior YAML uses `context.include: [recipes:context/recipe-instructions.md]` because it *wants* its context to flow up to anyone who includes the behavior. A root `bundle.md` uses `@my-bundle:context/instructions.md` in its body because the body is the final instruction and gets *replaced* during compose — `context.include` from a root bundle would propagate further than intended.

### Pitfalls

- **`@` in YAML.** `context.include: ["@foo:bar.md"]` silently fails — the `@` prefix is markdown-only.
- **Namespace = repo name.** Including `amplifier-bundle-recipes:recipe-author` will not resolve. It's `recipes:recipe-author`.
- **Subdirectory in path.** When loaded via `#subdirectory=cli-tool-builder`, the bundle root *is* `cli-tool-builder/`. Use `cli-tool-builder:context/x.md`, not `cli-tool-builder:cli-tool-builder/context/x.md`.
- **Missing `.yaml` extension on behavior includes.** Use `my-bundle:behaviors/foo` — the loader appends `.yaml`. Writing `my-bundle:behaviors/foo.yaml` works only sometimes depending on the resolver path.

---

## 2.5 Source URIs and prepare()

A **Source URI** is what `load_bundle()` accepts. There are four formats:

| Format            | Example                                                            | When to use                       |
|-------------------|--------------------------------------------------------------------|-----------------------------------|
| Local file        | `./bundle.md`, `/abs/path/bundle.md`, `file:///abs/path/`          | Authoring, testing, app-bundled config. |
| Local directory   | `/path/to/bundle/`                                                 | Resolved by finding `bundle.md` inside. |
| Git HTTPS         | `git+https://github.com/microsoft/amplifier-foundation@main`       | The default for shared bundles.   |
| Git + subdirectory| `git+https://github.com/org/repo@main#subdirectory=behaviors/x.yaml` | Loading a specific bundle file out of a multi-bundle repo. |

The `@ref` part is a git ref (branch, tag, or commit SHA). The `#subdirectory=path` fragment is a *path inside the cloned repo*, pointing either at a directory (loader looks for `bundle.md`/`bundle.yaml`) or directly at a YAML/Markdown file.

`parse_uri()` is the canonical parser:

```python
from amplifier_foundation import parse_uri
parse_uri("git+https://github.com/org/repo@main#subdirectory=bundles/dev")
# ParsedURI(scheme="git+https", host="github.com", path="/org/repo", ref="main", subpath="bundles/dev")
```

The `@ref` choice has reproducibility consequences — the **mutable vs immutable refs** distinction: `@main` is *mutable* (moves on every push to that branch), `@v1.2.0` is *semi-stable* (a tag, usually pinned but technically reassignable), and a full SHA is *immutable*. Pin to a tag or SHA in production; reserve `@main` for development.

### prepare() and PreparedBundle

A `Bundle` is a configuration record. It does not import any modules, install any dependencies, or contact any networks. **`prepare()` is what transforms configuration into something runnable.**

```python
prepared: PreparedBundle = await bundle.prepare()
```

Internally `prepare()` does, in order:

1. **Bundle-package install.** If the bundle root has a `pyproject.toml`, `activate_bundle_package()` installs it editable so its modules can import shared code. Repeats for every namespace in `source_base_paths` that has its own root package. (See BUNDLE_GUIDE.md §Root Python Package — most bundles don't need this.)
2. **Module activation.** Walks the Mount Plan (`session.orchestrator`, `session.context`, every `providers/tools/hooks` entry, plus modules referenced by `agents`) and activates each — cloning git sources, installing the module's `pyproject.toml` with `--no-sources`, and recording the path on disk.
3. **Resolver construction.** Builds a `BundleModuleResolver` that maps `module_id → activated path`. This resolver implements the kernel's `ModuleSourceResolver` protocol (Chapter 1 §protocols).
4. **Returns `PreparedBundle`.** Holds `mount_plan`, `resolver`, the original `bundle`, and the list of bundle-package source roots that need to be on `sys.path`.

`source_resolver` is the optional `prepare()` callback that lets the app layer override how module sources are fetched (e.g. swap remote URLs for local mirrors).

`PreparedBundle.create_session()` is the turn-key call:

```python
async with await prepared.create_session(session_cwd=Path.cwd()) as session:
    response = await session.execute("...")
```

It constructs an `AmplifierSession` from `prepared.mount_plan`, mounts the resolver, registers session capabilities (notably `session.working_dir` from `session_cwd`), and returns the session. Everything from here is kernel territory (Chapter 1).

`PreparedBundle.spawn()` is the analog for spawning a sub-session — typically called by the `tool-task`/`tool-delegate` capability (Chapter 3 §spawn).

### BundleRegistry

`BundleRegistry` owns the load-side state. It does three things:

1. **Maps registered names to source URIs** (`registry.register({"foundation": "git+https://..."})` → `await registry.load("foundation")`).
2. **Caches loaded bundles** under a configurable home directory (default `~/.amplifier`).
3. **Tracks structural metadata** for each loaded bundle: `name`, `local_path`, `is_root`, `root_name`. This is what powers `@namespace:path` lookups and root-vs-nested classification.

`load_bundle(uri)` is a thin wrapper around a default registry instance. For multi-bundle apps that need to swap caches, override registries, or pin URIs by name, instantiate `BundleRegistry` directly:

```python
from pathlib import Path
from amplifier_foundation import BundleRegistry

registry = BundleRegistry(home=Path("~/.myapp/cache").expanduser())
registry.register({
    "foundation": "git+https://github.com/microsoft/amplifier-foundation@main",
    "my-base":    "./bundles/base.md",
})
bundle = await registry.load("my-base")
```

Apps that need to surface available updates use `registry.get_state(name)` and `UpdateInfo` — see `registry.py` for details.

### Pitfalls

- **`prepare()` is expensive.** Cold-cache prepares clone repos and run `uv pip install` for every module. The pattern is "prepare once, execute many" — keep `PreparedBundle` alive across multiple sessions if possible.
- **Caches are not refreshed automatically.** Registry caches by URI. To pick up upstream changes, you must invalidate the cache (delete the cloned repo) or pin to a SHA and bump it.
- **`source_resolver` is the override seam.** Apps that need to redirect a module's `source:` (e.g., a local fork) pass a `source_resolver` callback to `prepare()`. The bundle does not know it's being overridden.
- **Module dependencies install with `--no-sources`.** Any `[tool.uv.sources]` overrides in a module's `pyproject.toml` are silently stripped during activation. If your modules need shared code, use the root-package pattern (BUNDLE_GUIDE.md §Root Python Package), not `[tool.uv.sources]`.

---

## 2.6 The thin bundle pattern

When your bundle includes foundation, you should declare **only what foundation does not**. This is the **thin bundle pattern**, and it is the strong recommendation for every capability bundle in the ecosystem.

The reason is mechanical, not stylistic. Suppose your bundle redeclares `tool-filesystem`. Now there are two definitions: yours and foundation's. Composition merge-by-module-ID will deep-merge them, your `source:` will replace foundation's, and any future foundation update to that tool's config silently stops applying. You have not added a feature — you have created a maintenance liability.

The exemplar is `amplifier-bundle-recipes`'s `bundle.md`:

```markdown
---
bundle:
  name: recipes
  version: 1.0.0
  description: Multi-step AI agent orchestration for repeatable workflows

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: recipes:behaviors/recipes
---

# Recipe System

@recipes:context/recipe-instructions.md

---

@foundation:context/shared/common-system-base.md
```

That is the entire bundle. Tools, providers, hooks, session config, and the bulk of the system instruction all come from the two includes. The bundle's actual value lives in `behaviors/recipes.yaml`, which packages the tool, agents, and consolidated context into a *behavior* — a reusable capability bundle that any other bundle can include.

A behavior is structurally just a nested bundle (a YAML in `behaviors/`) that declares a small subset of sections — usually `tools`, `agents.include`, and `context.include`:

```yaml
# behaviors/recipes.yaml
bundle:
  name: recipes-behavior
  version: 1.0.0

tools:
  - module: tool-recipes
    source: git+https://github.com/microsoft/amplifier-bundle-recipes@main#subdirectory=modules/tool-recipes

agents:
  include:
    - recipes:recipe-author
    - recipes:result-validator

context:
  include:
    - recipes:context/recipe-instructions.md
```

The full anatomy of behaviors, agents (the markdown files in `agents/`), and recipes (Chapter 3) is out of scope here. For composition, the only thing that matters is: a behavior is a bundle, and including it composes its `tools/agents/context` into yours.

### Pitfalls

- **Redeclaring the orchestrator.** Foundation's `session.orchestrator: loop-streaming` is the obvious thing to "set" — and the wrong thing to override. Trust the include.
- **Inline instructions.** A 500-line system prompt inside `bundle.md` cannot be reused by behaviors and grows unmaintainable. Move it to `context/instructions.md` and `@mention` it.
- **Behavior in a root bundle.** If your bundle is a "behavior" (one capability others compose onto theirs), the bundle file should be a `.yaml` in `behaviors/`, not a root `bundle.md`. Putting it at the root makes it a root bundle and its namespace primary — likely not what you want.

---

## 2.7 Putting it together

Here is the minimum custom bundle. It includes foundation, adds one tool config (a writeable-paths restriction), and runs a prompt.

`./my-bundle/bundle.md`:

```markdown
---
bundle:
  name: my-app
  version: 1.0.0
  description: Foundation with a constrained filesystem tool

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main

tools:
  - module: tool-filesystem
    config:
      allowed_write_paths:
        - /home/user/myproject
        - ~/.amplifier
---

You are a focused assistant for /home/user/myproject.

@foundation:context/shared/common-system-base.md
```

What happens, annotated with the concept names:

```python
import asyncio
from pathlib import Path
from amplifier_foundation import load_bundle

async def main() -> None:
    # 1. Source URI resolution. The local path is parsed by parse_uri();
    #    the file is read; YAML frontmatter is parsed; Markdown body becomes instruction.
    bundle = await load_bundle("./my-bundle/bundle.md")     # Bundle (root, is_root=True)

    # 2. includes: was already resolved by load_bundle().
    #    The foundation bundle was loaded, registered under namespace "foundation",
    #    composed in, and our bundle was overlaid on top. Same logic as compose().
    #
    #    At this point:
    #      bundle.tools includes everything foundation declared, with our
    #      tool-filesystem config deep-merged onto foundation's tool-filesystem entry.

    # 3. prepare(): downloads modules, installs deps, builds module resolver.
    #    Returns a PreparedBundle.
    prepared = await bundle.prepare()

    # 4. Mount plan + kernel session creation.
    #    create_session() reads prepared.mount_plan, mounts the resolver,
    #    registers session.working_dir capability, and starts the orchestrator.
    async with await prepared.create_session(session_cwd=Path.cwd()) as session:
        print(await session.execute("List the files in the current directory."))

asyncio.run(main())
```

Three things to notice:

- **You wrote no Mount Plan.** The Mount Plan is `prepared.mount_plan` — derived from compose(includes + your bundle).
- **`@foundation:context/shared/common-system-base.md`** resolves because foundation's `bundle.name` registered the `foundation` namespace, and its base_path was recorded in `source_base_paths` during composition.
- **The kernel sees a normal Mount Plan.** Everything you learned in Chapter 1 still applies — bundles are a layer, not a replacement.

For the runtime details after `create_session()` (orchestrator loop, hook events, capability registration), see Chapter 1 §Sessions. For agents/behaviors/recipes as authored artifacts, see Chapter 3. For the `amplifier` CLI which wraps this whole pipeline behind a one-liner, see Chapter 4.

---

## 2.8 Self-check

1. A bundle has `includes: [foundation, my-bundle:behaviors/x]` and declares its own `tools: [{module: tool-foo}]`. Foundation declares `tool-bash`. Behavior `x` declares `tool-baz`. After loading, what is the order of `result.tools`, and is `tool-baz` before or after `tool-foo`?

2. You write `@my-bundle:context/x.md` in your bundle's body. Foundation also declares `bundle.name: foundation`. At resolution time, the resolver looks up `"my-bundle"` where, exactly, and what determines the on-disk root it uses?

3. Two bundles each declare a `tool-filesystem` entry with different `allowed_write_paths` arrays. Predict the result of `base.compose(overlay)`. Is `allowed_write_paths` concatenated, replaced, or deep-merged?

4. You move your `behaviors/foo.yaml` to `bundles/foo.yaml` and update includes accordingly. Which is now structurally a root bundle, which is nested, and what is the namespace of `bundles/foo.yaml`?

5. Why does `context.include` in a behavior YAML propagate context to the including bundle, while `@mentions` in a root `bundle.md` body do not propagate to bundles that include yours?

6. What does `prepare()` do that `to_mount_plan()` does not?

7. Given `git+https://github.com/microsoft/amplifier-bundle-recipes@main#subdirectory=behaviors/recipes.yaml`, what is the namespace registered when this bundle loads, and why is it not `recipes-behavior` despite `bundle.name: recipes-behavior` in that YAML?

8. You replace `await bundle.prepare()` with `bundle.to_mount_plan()` and pass the dict to `AmplifierSession` directly. What breaks, and why?

---

### Hints / answers

1. `result.tools = [tool-bash, tool-baz, tool-foo]`. `includes:` is resolved first in declaration order (foundation, then behavior), then *this* bundle is composed last.

2. The composed bundle's `source_base_paths["my-bundle"]`. The base_path was set when your bundle's `bundle.name` got recorded during composition (or load, for the topmost bundle).

3. Replaced. Merge-by-module-ID deep-merges the `config` dict, but inside a `dict.update()`-style merge, list values are replaced wholesale, not concatenated. The overlay's `allowed_write_paths` wins.

4. The repo's `/bundle.md` is the root. `bundles/foo.yaml` is structurally nested (`is_root=False`). Its namespace is *not* `foo`; it shares the root bundle's namespace (whatever its `bundle.name` says).

5. `context.include` items accumulate during `compose()` — every bundle in the chain contributes. `@mentions` live inside the `instruction` string, and `instruction` is **replaced** during compose, so the @mention dies with whichever instruction loses.

6. `prepare()` activates modules: clones git sources, runs `uv pip install`, and builds a `BundleModuleResolver` mapping module IDs to local paths. `to_mount_plan()` only emits the configuration dict.

7. `recipes` (the namespace registered by the repo's root `/bundle.md`). The behavior YAML is a nested bundle and shares the root's namespace. Its own `bundle.name: recipes-behavior` is metadata, not a registered namespace.

8. Module sources never get resolved. The kernel will try to find each module via its module-source resolver, and without `prepared.resolver` mounted, it has no map from module ID to local path. Every module `mount()` fails to import.
