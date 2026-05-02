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

The glossary was extended after this guide was written to include a set of terms surfaced during chapter research (`on_session_ready()`, contribution channels, polyglot transports, the two-implementation rule, `source_base_paths`, soft references, `source_resolver`, mutable vs immutable refs, output contract, thin awareness pointer, project slug, module ID vs package name vs import path, and static provider capabilities). All are now first-class entries in `../GLOSSARY.md`.
