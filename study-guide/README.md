# Amplifier Study Guide

A four-chapter walkthrough of the Amplifier ecosystem for developers who
have already skimmed `../GLOSSARY.md` and want depth.

## Read in order

1. **[Chapter 0 — How to Use This Guide](parts/00-introduction.md)**
   Audience, threads that run through every chapter, scope.

2. **[Chapter 1 — The Kernel Layer](parts/01-kernel.md)**
   Sessions, Coordinator, Mount Plans, the five module protocols
   (Provider, Tool, Orchestrator, ContextManager, Hook), events,
   forking. The bottom of the stack.

3. **[Chapter 2 — The Composition Layer](parts/02-composition.md)**
   Bundles, `includes:`, `compose()`, merge rules, namespaces,
   `@mentions`, `prepare()` / `PreparedBundle`, source URIs,
   `BundleRegistry`. How human-friendly configuration becomes a
   Mount Plan.

4. **[Chapter 3 — Authoring Artifacts](parts/03-authoring.md)**
   Agents, behaviors (bundle-behaviors vs policy-behaviors),
   context files, instructions, `spawn`, `model_role`,
   `provider_preferences`, recipes, skills. What you put inside a bundle.

5. **[Chapter 4 — The CLI App and the Ecosystem](parts/04-app-and-ecosystem.md)**
   The `amplifier` CLI, the default `foundation` bundle, providers,
   sessions, plan mode, the log viewer, repo naming conventions,
   entry points, the wider community catalog.

## Companion file

- **[../GLOSSARY.md](../GLOSSARY.md)** — single-page reference for every term
  used here. Keep it open while reading.

## Suggested glossary additions

The chapter agents surfaced concepts present in primary sources but not in
the current glossary. Each is a candidate for a future glossary entry:

| Term | Where it surfaced | Why it earns an entry |
|---|---|---|
| `on_session_ready()` | Chapter 1 (kernel CONTRACTS) | Second optional module entry point alongside `mount()`. |
| Contribution channels (`register_contributor` / `collect_contributions`) | Chapter 1 | Cross-module discovery primitive distinct from the capability registry. |
| Static provider capabilities (`ProviderInfo.capabilities`) | Chapter 1 | Distinct from the runtime capability registry — disambiguation needed. |
| Polyglot transports (native / python / grpc / wasm) | Chapter 1 | Four-way module transport split referenced throughout the docs. |
| Two-implementation rule | Chapter 1 | Governance rule for kernel additions; distinct from mechanism vs policy. |
| `source_base_paths` | Chapter 2 | The actual data structure behind @mention resolution. |
| Soft reference (`namespace:path` without `@`) | Chapter 2 + 3 | Token-budget pattern, distinct from `@mentions` and `context.include`. |
| `source_resolver` callback on `prepare()` | Chapter 2 | App-layer override seam between bundle composition and kernel module-source resolution. |
| Output Contract | Chapter 3 | Section of an agent's instruction defining response shape callers can rely on. |
| Thin awareness pointer | Chapter 3 | Named pattern: a 25–40 line context file paired with a context-sink agent. |
| Module ID vs package name vs import path | Chapter 4 | Three derivations of the same logical name; mismatches are a common silent failure. |
| Project slug | Chapter 4 | Path-derived directory under `~/.amplifier/projects/` that drives session scoping. |
| Mutable vs immutable refs | Chapter 4 | `@main` vs `@v1.0.0` vs SHA — material to reproducibility. |

These can be added to `GLOSSARY.md` as a follow-up; the chapters reference
them inline whether or not the glossary entry exists.
