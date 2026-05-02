# Chapter 0 — How to Use This Guide

This study guide teaches the Amplifier ecosystem from the ground up. It assumes
you have read `GLOSSARY.md` once and want to move from "I recognize the words"
to "I can read the code, build artifacts, and operate the CLI with confidence."

## Audience

A developer who knows Python, has cloned this repository, and wants to:

- Read any file in `amplifier-core`, `amplifier-foundation`, or `amplifier`
  and understand what role it plays.
- Build their own bundle, agent, behavior, or module.
- Use the `amplifier` CLI productively.
- Recognize ecosystem repositories at a glance.

Prior experience with LLM tooling helps but is not required.

## How to read it

The guide is four chapters, in dependency order. Each chapter assumes the ones
before it. Skipping forward is possible but expensive — terms introduced
earlier are referenced without re-explanation.

| Chapter | Topic | Read first if you want to… |
|---|---|---|
| **1 — The Kernel Layer** | Sessions, Mount Plans, the five module protocols | understand what actually runs at execution time |
| **2 — The Composition Layer** | Bundles, includes, compose, namespaces, @mentions | turn human-friendly config into something the kernel runs |
| **3 — Authoring Artifacts** | Agents, behaviors, context, recipes, skills, spawn, `model_role` | write capability that ships inside a bundle |
| **4 — The CLI App and the Ecosystem** | The `amplifier` command, repo conventions, entry points | install, operate, and publish into the ecosystem |

Each chapter ends with a self-check. Treat the questions as a re-read prompt,
not a quiz: if you cannot answer one, the section that defines it is short
and nearby.

## Two threads that run through every chapter

**Mechanism vs Policy.** The kernel provides capabilities; everything else makes
decisions. The litmus test: *could two teams want different behavior?* If yes,
it belongs in userspace — a bundle, a module, an agent — not the kernel. This
single rule explains most of the architecture.

**Ruthless simplicity, text first.** Bundles are Markdown with YAML frontmatter.
Composition is one primitive (`includes:`). Module protocols are structural —
no inheritance required. When you encounter a feature that seems to add a new
abstraction, ask whether it is a mechanism (likely keep) or a policy
(belongs in a bundle).

You will see both threads called out across all four chapters. They are the
fastest way to predict where a piece of code lives.

## How this guide was built

Each chapter was researched and drafted by a focused sub-agent operating only
on its assigned scope, writing directly to `study-guide/parts/0X-*.md`. This
"fan-out / fan-in" pattern keeps each chapter grounded in primary sources and
prevents one chapter's framing from leaking into another. The result: each
chapter quotes its sources, sticks to its scope, and forwards-references
cleanly.

If you want to extend the guide, follow the same pattern: scope the new
chapter narrowly, point at primary sources, and forward-reference rather
than duplicate.

## What this guide does not cover

- **Rust kernel internals.** Chapter 1 explains the Python boundary and the
  PyO3 bridge. The Rust crates are out of scope; read them when you need to
  modify the kernel itself, not to use it.
- **Specific community bundles.** Chapter 4 points at `amplifier/docs/MODULES.md`
  as the catalog. Each bundle's own README is the authority on its details.
- **Provider-specific quirks** beyond what the CLI surface exposes (e.g.
  Azure deployment-name pitfalls). Read the provider's own bundle docs.
- **The CLI implementation.** It lives in a separate repo
  (`amplifier-app-cli`) not vendored here. Chapter 4 describes the user-facing
  surface only.

## A note on accuracy

These chapters are written against the submodule pins in this repository at
the time of writing. The Amplifier project is in early preview; APIs are
stabilizing. When something here disagrees with the source code, the source
code wins.

If you find drift, the fix is small: update `GLOSSARY.md` first (one term),
then update the affected chapter section. Keep the glossary as the contract
the chapters honor.
