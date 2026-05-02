# Chapter 3 — Authoring Artifacts

Bundles are the container; this chapter teaches what you put inside one. Chapter 1 explained how the kernel mounts modules and Chapter 2 explained how `compose()`, `includes`, namespaces, and `@mentions` glue partial bundles into a complete mount plan. Here you learn the *content* a bundle ships: agents, behaviors, instructions and context, recipes, and skills. By the end of this chapter you should be able to read any agent file in `amplifier-foundation/agents/` and explain every frontmatter field, decide whether a new capability should be an agent, a behavior, a recipe, or a skill, and write a small but well-formed example of each.

## Concepts covered

- **Instruction** — the markdown body of a bundle, used as a system prompt
- **Context** files and the **Context sink** pattern
- **Agent** — a bundle whose frontmatter key is `meta:` instead of `bundle:`
- **`model_role`** — declarative model selection on agents
- **`provider_preferences`** — the escape hatch for pinning concrete models
- **Behavior** — a reusable capability YAML; bundle-behavior vs policy-behavior
- **Spawn** — the frontmatter section that controls tool inheritance for child agents
- **Recipe** — a YAML workflow shipped by `amplifier-bundle-recipes`, executed by the recipes tool
- **Skill** — a capability shipped by `amplifier-bundle-skills`, distinct from a tool

## 3.1 Authoring inside a bundle

A bundle ships some combination of two things: **kernel modules** (providers, tools, hooks, orchestrators, context managers — covered in Chapter 1) and **authoring artifacts** (agents, behaviors, instructions, context files, recipes, skills). Modules are Python; authoring artifacts are markdown and YAML. This chapter is about the second category.

Authoring artifacts follow a consistent directory convention. Open `/home/user/amplifier-universe/amplifier-foundation/` and you will see this layout:

```
amplifier-foundation/
├── bundle.md                  # Root bundle (Chapter 2)
├── behaviors/                 # *.yaml — reusable capability packages
│   ├── agents.yaml
│   ├── foundation-expert.yaml
│   ├── redaction.yaml
│   └── sessions.yaml
├── agents/                    # *.md  — agent definitions (each is a bundle)
│   ├── bug-hunter.md
│   ├── explorer.md
│   ├── foundation-expert.md
│   └── zen-architect.md
├── context/                   # *.md  — shared instructions and knowledge
│   ├── IMPLEMENTATION_PHILOSOPHY.md
│   ├── MODULAR_DESIGN_PHILOSOPHY.md
│   ├── bundle-awareness.md
│   ├── agents/
│   └── shared/
│       ├── common-agent-base.md
│       └── common-system-base.md
├── recipes/                   # *.yaml — workflows executed by tool-recipes
└── docs/                      # Documentation (read by experts via @mentions)
```

These are *conventions*, not enforced rules. The kernel does not care where files live — the URI resolver does. But foundation, every published Amplifier bundle, and every example in `BUNDLE_GUIDE.md` follow this layout, and anything you author should too. The reason: tooling and recipes assume it (e.g. `validate-agents` walks `agents/`; the agent loader auto-searches the `agents/` directory when it sees `agents.include: - my-bundle:my-agent`).

The thin-bundle pattern from Chapter 2 (`bundle.md` does almost nothing except `includes:` a behavior) only works because authoring artifacts have a stable home. Once you internalize the directory map, an unfamiliar bundle takes seconds to navigate.

## 3.2 Instructions and context

Two things turn a bundle from "configuration" into "an agent that can do something": the **instruction** (what the LLM is told) and the **context** files it can reference. They are two halves of the same problem — getting the right text into the LLM's prompt without bloating every session.

### Instruction: the markdown body

Every bundle file is a markdown file with YAML frontmatter. The text **after** the closing `---` is the **instruction** — the system prompt for sessions that mount this bundle. From `BUNDLE_GUIDE.md`:

> Markdown instructions: replace entirely (later wins)

This is the one place where Chapter 2's "merge" rule does not apply. When two bundles compose, the **later** instruction body wins. If you want to inherit the parent's instruction text, reference it explicitly with an `@mention`. The canonical pattern (from `amplifier-bundle-recipes/bundle.md`) is:

```markdown
---
bundle:
  name: recipes
  version: 1.0.0
includes:
  - bundle: foundation
  - bundle: recipes:behaviors/recipes
---

# Recipe System

@recipes:context/recipe-instructions.md

---

@foundation:context/shared/common-system-base.md
```

The body has three parts: a one-line title, an `@mention` to the bundle's own consolidated instructions, and a final `@mention` to foundation's shared base instructions. The two `@mentions` are *eager* — both files load into the system prompt at session start.

### Context files

A **context file** is just a markdown file referenced from a bundle. There are two ways to wire one in, and they have different composition semantics (see Chapter 2 for the merge rules). In short:

- `context.include` in YAML — **accumulates** across composed bundles, useful for behaviors that want to inject context into any bundle that uses them.
- `@mention` in markdown — content is **prepended** to *that specific instruction*, replaced entirely if the instruction is overridden by composition.

Use `context.include` in `behaviors/*.yaml`. Use `@mentions` in `bundle.md` and in `agents/*.md`.

### The Context sink pattern

Heavy documentation is a tax on every session that loads it. A 4,600-token `MODULES.md` referenced eagerly from `bundle.md` consumes those tokens whether or not the user ever asks about modules. Long sessions run out of context window faster, sub-agent spawns inherit the bloat, and the LLM gets distracted by knowledge it does not need.

The fix is the **context sink pattern**: heavy documentation lives inside an *expert agent*, not in always-loaded context. The root session gets a thin awareness pointer (~25–40 lines) that says "this domain exists, delegate to `foundation:foundation-expert` for it." When the user actually asks about it, the agent spawns, the heavy docs load into the *agent's* sub-session, and the parent stays lean.

You can see this pattern in foundation. `behaviors/foundation-expert.yaml` is six lines:

```yaml
bundle:
  name: foundation-expert-behavior
  version: 1.0.0
  description: Expert consultant for bundle composition, patterns, and building AI applications

agents:
  include:
    - foundation:foundation-expert

context:
  include:
    # Thin awareness pointer - just enough to know the domain exists and to delegate
    # Heavy documentation lives in the agent file (context sink pattern)
    - foundation:context/bundle-awareness.md
```

`context/bundle-awareness.md` is ~50 lines that say "delegate to foundation-expert." `agents/foundation-expert.md` is the heavy file: it `@mention`s `foundation:docs/`, `foundation:examples/`, the philosophy directory, and the shared agent base — content the parent session never sees unless the agent is spawned.

The doc puts the rule sharply: *"Anti-Pattern: Heavy Context in Behaviors. Heavy docs in behavior context (loads for everyone). Thin pointer in behavior, heavy docs in agent."* When you author a new behavior, ask: *if no one ever delegates to my agent, does my context still earn its tokens?* If not, move it inside the agent.

**Related**: 3.3 Agents (where heavy `@mentions` go); Chapter 2 §2.3 (composition merge rules).

## 3.3 Agents

> **Key insight from `AGENT_AUTHORING.md`:** *Agents ARE bundles.* Same file format. Same `load_bundle()` call. The only difference is that the frontmatter root key is `meta:` rather than `bundle:`, and the required fields are `name` and `description` instead of `name` and `version`.

An **Agent** is a bundle scoped to run as a sub-session for a focused task. A coordinator (or the `tool-task` / `tool-delegate` tool) spawns it, the agent burns its own context window doing work, and only its final response returns to the parent. Because it is a bundle, everything you learned in Chapter 2 applies: it has frontmatter, an instruction body, can declare its own `tools:` and `provider_preferences:`, and supports `@mentions`.

### Why agents exist

Three problems they solve:

1. **Token efficiency.** Heavy domain knowledge lives inside the agent, not the parent session. (See 3.2, the context sink pattern.)
2. **Focused capability.** A debugging agent declares a `coding` model and surgical tools (`tool-filesystem`, `tool-bash`, `tool-lsp`); a fast batch worker declares a `fast` model and `tool-filesystem` only. The parent stays general.
3. **Discoverability through delegation.** When the parent has many agents available, it picks one based on the agent's `description`. A clear description routes the right work to the right agent automatically.

### How to recognize one

- Lives in `agents/*.md` within a bundle.
- Frontmatter starts with `meta:` (not `bundle:`).
- Required `meta` fields: `name` (string, lowercase-hyphen) and `description` (string, multi-line).
- Common optional fields: `model_role`, `provider_preferences`, `tools`.
- The markdown body is the agent's system instruction.
- Almost always ends with `@foundation:context/shared/common-agent-base.md`.

### The `meta.description` field is your agent's advertisement

This is the single most important field in agent authoring. From `AGENT_AUTHORING.md`:

> **The `meta.description` field is the ONLY discovery mechanism for agents.** When the task tool presents available agents to the LLM, this description is all it sees to decide which agent to use. Poor descriptions cause delegation failures. One-liner descriptions are unacceptable.

A good description answers four questions:

- **WHY** — the value proposition.
- **WHEN** — explicit activation triggers (use the keywords *MUST*, *REQUIRED*, *ALWAYS*, *PROACTIVELY*, *Use when…*).
- **WHAT** — domain and taxonomy terms (the doc recommends a literal `**Authoritative on:** term1, term2, ...` line).
- **HOW** — at least one `<example>` block with `<commentary>` explaining why the agent fits.

### A worked example

This is `bug-hunter.md` from `/home/user/amplifier-universe/amplifier-foundation/agents/bug-hunter.md`, condensed to show the structural pieces:

```markdown
---
meta:
  name: bug-hunter
  description: "Specialized debugging expert focused on finding and fixing bugs systematically.
    Use PROACTIVELY. It MUST BE USED when user has reported or you are encountering errors,
    unexpected behavior, or test failures. Examples:
    <example>user: 'The synthesis pipeline is throwing a KeyError somewhere'
    assistant: 'I'll use the bug-hunter agent to systematically track down and fix this KeyError.'
    <commentary>The bug-hunter uses hypothesis-driven debugging to efficiently locate and resolve issues.</commentary></example>
    <example>user: 'Tests are failing after the recent changes'
    assistant: 'Let me use the bug-hunter agent to investigate and fix the test failures.'
    <commentary>Perfect for methodical debugging without adding unnecessary complexity.</commentary></example>"

model_role: [coding, general]

provider_preferences:
  - provider: anthropic
    model: claude-sonnet-*
  - provider: openai
    model: gpt-5.[0-9]-codex

tools:
  - module: tool-filesystem
    source: git+https://github.com/microsoft/amplifier-module-tool-filesystem@main
  - module: tool-search
    source: git+https://github.com/microsoft/amplifier-module-tool-search@main
  - module: tool-bash
    source: git+https://github.com/microsoft/amplifier-module-tool-bash@main
  - module: tool-lsp
    source: git+https://github.com/microsoft/amplifier-bundle-lsp@main#subdirectory=modules/tool-lsp
---

You are a specialized debugging expert focused on systematically finding and fixing bugs.
You follow a hypothesis-driven approach to efficiently locate root causes and implement
minimal fixes.

## Operating Principles
1. Hypothesis-driven investigation — list candidate causes before testing.
2. Minimal-change fixes — fix the root cause, not symptoms.
3. Always add a regression test.

## Workflow
1. Reproduce the bug deterministically.
2. Narrow the failure point with grep, LSP `incomingCalls`, and `hover`.
3. Form and test hypotheses one at a time.
4. Apply the smallest fix that works; add a test.

## Output Contract

Your response MUST include:
- A `Root Cause` section with the exact location (file:line) and the failing condition.
- A `Fix Applied` section showing before/after code.
- A `Verification` checklist (issue resolved, no side effects, regression test added).
- A `Prevention Recommendations` section with concrete suggestions.

---

@foundation:context/IMPLEMENTATION_PHILOSOPHY.md

@foundation:context/shared/common-agent-base.md
```

Read this top-down. The frontmatter says *what* the agent is and *what it needs*. The instruction body says *how it works*: a one-line role, operating principles, a workflow, and a non-negotiable **Output Contract**. The trailing `@mention`s pull in shared philosophy and the agent base so behavior stays consistent across all foundation agents.

### The recommended instruction structure

From `AGENT_AUTHORING.md`:

```markdown
# Agent Name
[One-line role description]

**Execution model:** You run as a one-shot sub-session. Work with what
you're given and return complete results.

## Operating Principles
1. ...

## Workflow
1. ...

## Output Contract
Your response MUST include:
- ...

---

@foundation:context/shared/common-agent-base.md
```

The **Execution model** sentence is load-bearing: it tells the agent it cannot ask follow-up questions, only return a complete answer. The **Output Contract** is what callers rely on — without it, parent sessions cannot consume the agent's results reliably.

### Common mistakes

`AGENT_AUTHORING.md` lists five recurring mistakes; treat this as a checklist before shipping any agent:

1. **Vague description.** *"Helps with code stuff."* Callers cannot match user requests to the agent. Add WHEN, WHAT, and an `<example>` block.
2. **Missing `@foundation:context/shared/common-agent-base.md`.** Without it, the agent will not honor the shared tone, security, and tool-use guidance the rest of the ecosystem assumes.
3. **No output contract.** Callers do not know what to expect back. Define the response shape.
4. **Treating agents as different from bundles.** They are not. Use the same `@mention`, `tools:`, and composition patterns from Chapter 2.
5. **Heavy docs in always-loaded context.** Put heavy `@mentions` inside the agent file, not in `behavior.context.include`. (See 3.2.)

### Audit your description

The doc proposes an explicit checklist for `meta.description` — every shippable agent should pass it:

- [ ] More than 100 words (not a one-liner)
- [ ] Has explicit trigger conditions (*MUST*, *PROACTIVELY*, *Use when…*)
- [ ] Lists domain terms (`**Authoritative on:** ...`)
- [ ] Includes at least one `<example>` block with `<commentary>`
- [ ] States the value proposition

The `validate-agents` recipe (`amplifier-foundation/recipes/validate-agents.yaml`) automates this audit and codifies the explicit thresholds: description ≥ 100 chars, at least one of `MUST/ALWAYS/REQUIRED/PROACTIVELY/DO NOT`, at least one `<example>`, and an explicit `tools:` section.

**Related**: 3.4 Model selection; 3.6 Spawn; Chapter 4 (CLI commands for spawning agents).

## 3.4 Model selection: `model_role` and `provider_preferences`

Two frontmatter fields control which model an agent runs on. They exist because hardcoding a model name in an agent file ages badly: the model gets deprecated, you have a different provider in production, or you want different routing for an evaluation harness. The fields let an agent declare *what kind* of work it does and let the routing matrix and app config decide the rest.

### `model_role` — declarative

This is the preferred field. The agent says "I do *this kind* of work" and the active routing matrix maps that role to a concrete provider+model. Two forms:

```yaml
# String shorthand — single role
meta:
  name: my-agent
  description: "..."
  model_role: coding
```

```yaml
# List form — fallback chain. Try first, then second, then third.
meta:
  name: my-agent
  description: "..."
  model_role: [vision, coding, general]
```

The list form falls back through roles when the active routing matrix or installed providers do not cover an earlier choice. Available roles (from `AGENT_AUTHORING.md`): `coding`, `ui-coding`, `security-audit`, `reasoning`, `critique`, `creative`, `writing`, `research`, `vision`, `image-gen`, `critical-ops`, `fast`, `general`. Every routing matrix must define `general` and `fast`; other roles are optional and the fallback chain skips undefined ones.

Choose roles by *intent*, not by *which model you want today*:

- `bug-hunter.md` uses `[coding, general]` — debug work, fall back to general if no coding model is installed.
- `file-ops.md` uses `fast` — bulk file ops do not need a frontier model.
- `zen-architect.md` uses `[reasoning, general]` — deep architectural analysis.
- `foundation-expert.md` uses `general` — broad consultation.

### `provider_preferences` — the escape hatch

When you must pin a specific provider+model (or, more commonly, *a small set of acceptable choices in priority order*), use `provider_preferences`. It accepts a list of `{provider, model}` entries and is tried in order. Models support glob patterns (`fnmatch`) so you can pin a family without pinning a specific revision:

```yaml
provider_preferences:
  - provider: anthropic
    model: claude-sonnet-*
  - provider: openai
    model: gpt-5.[0-9]-codex
  - provider: google
    model: gemini-*-pro
```

`bug-hunter.md` uses both fields: `model_role: [coding, general]` for routing, plus a `provider_preferences` chain that prefers Sonnet, then GPT-5 Codex, then Gemini Pro, then GitHub-Copilot fallbacks. **When both are present, `provider_preferences` takes priority** over `model_role` — the routing matrix only kicks in if every preference misses.

### Rule of thumb

Default to `model_role` alone. Reach for `provider_preferences` only when you have a concrete, time-bounded reason: a model that genuinely outperforms the role default for this task, or a fallback chain you need across heterogeneous deployments. Hardcoding `claude-opus-4-6` directly in an agent is technically supported and almost always wrong — the agent stops working when that model is sunset, deprecated, or simply unavailable in someone else's deployment.

**Related**: 3.3 Agents; Chapter 1 (provider modules and how the kernel selects them).

## 3.5 Behaviors and the thin bundle pattern

A **Behavior** is a YAML file that packages a coherent capability — usually some combination of agents, context files, tools, and hooks — into a single unit that any bundle can `include`. It is the primary unit of *reuse* in the ecosystem. When `BUNDLE_GUIDE.md` says "package your value in `behaviors/`," this is what it means.

### Why behaviors exist

A capability rarely consists of one thing. The "agents" capability in foundation needs the `tool-delegate` module, two context files (`delegation-instructions.md`, `multi-agent-patterns.md`), and configuration on the tool. Without behaviors, every bundle that wanted agent-delegation would have to redeclare all four pieces. With behaviors, the bundle says one line: `- bundle: foundation:behaviors/agents`.

Behaviors enable the **thin bundle pattern** — most bundles you write should be ~14 lines of YAML that `include` foundation and one or two behaviors and reference a consolidated instructions file. Bundles get fat when authors put their capability *inline* instead of packaging it as a behavior; thin bundles stay thin because their value is delegated to behaviors.

### How to recognize one

- Lives in `behaviors/*.yaml` (filename = behavior name; `.yaml` is omitted from include paths).
- Top-level key is `bundle:` (not `meta:`) — yes, behaviors are also bundles.
- Has at least one of: `tools`, `agents.include`, `context.include`, `hooks`, `includes`.
- Does **not** have a markdown body. Pure YAML.

### A worked example

`amplifier-foundation/behaviors/agents.yaml` is the canonical "complete" behavior — it ships a tool, configures it, declares the agents the tool can spawn, and adds delegation instructions:

```yaml
bundle:
  name: behavior-agents
  version: 2.0.0
  description: |
    Agent orchestration capability with enhanced delegate tool.

    Features:
    - Two-parameter context inheritance (depth + scope)
    - Session resume (use full session_id from delegate calls)
    - Fixed tool inheritance (agent declarations honored)
    - Multi-agent collaboration patterns

tools:
  # New delegate tool with enhanced features
  - module: tool-delegate
    source: git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=modules/tool-delegate
    config:
      features:
        self_delegation:
          enabled: true
        session_resume:
          enabled: true
        context_inheritance:
          enabled: true
          max_turns: 10
      settings:
        exclude_tools: [tool-delegate]  # Spawned agents cannot further delegate by default
        exclude_hooks: []

  - module: tool-skills
    source: git+https://github.com/microsoft/amplifier-bundle-skills@main#subdirectory=modules/tool-skills
    config:
      skills:
        - "git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=skills"

context:
  include:
    - foundation:context/agents/delegation-instructions.md
    - foundation:context/agents/multi-agent-patterns.md
```

Read it section by section:

- **`bundle:`** — name, version, description. The `name` (`behavior-agents`) is what the bundle becomes after composition; the `description` is what apps and `validate-bundle` show humans.
- **`tools:`** — the modules this behavior mounts when included. Each entry is a kernel tool module (Chapter 1) with a `source` URI (Chapter 2) and tool-specific `config`. Note `exclude_tools: [tool-delegate]` — that controls what spawned agents *cannot* re-spawn (see 3.6).
- **`context.include`** — context files that inject into the system prompt of any bundle that includes this behavior. They use the *bare* `namespace:path` syntax — no `@` prefix in YAML.

A simpler behavior makes the minimal shape obvious. `behaviors/foundation-expert.yaml` (full file):

```yaml
bundle:
  name: foundation-expert-behavior
  version: 1.0.0
  description: Expert consultant for bundle composition, patterns, and building AI applications

agents:
  include:
    - foundation:foundation-expert

context:
  include:
    - foundation:context/bundle-awareness.md
```

That is a complete, useful behavior: register one agent, inject one thin awareness pointer. Forty lines of agent file plus three lines of behavior YAML give every bundle that includes this behavior a delegated bundle-composition expert.

### Authoring a new behavior

When you build a new capability, ask: *does this provide value to bundles other than mine?* If yes, package it as a behavior:

1. Create `behaviors/my-capability.yaml`.
2. Declare `bundle.name`, `bundle.version`, `bundle.description`.
3. List the modules you mount in `tools:` / `hooks:`. Use `source:` URIs (Chapter 2).
4. List the agents you provide via `agents.include`. *Do not* include the `agents/` directory in the path — the loader auto-searches it. Write `my-bundle:my-agent`, not `my-bundle:agents/my-agent`.
5. List context files via `context.include` — but keep them **thin** (3.2). Heavy docs go in agents.
6. Reference the behavior from your root `bundle.md`: `- bundle: my-bundle:behaviors/my-capability` (no `.yaml` suffix, no `@`).

### Bundle behaviors vs policy behaviors

This distinction is small but important. From `POLICY_BEHAVIORS.md`:

| Aspect | Bundle Behaviors | Policy Behaviors |
|--------|------------------|------------------|
| Included by | Bundle `includes:` | App composes at runtime |
| Applies to | All sessions (incl. sub-agents, recipe steps) | **Root sessions only** |
| Examples | Logging, redaction, agents, tools | Notifications, cost alerts, session limits |
| Configured in | Bundle YAML | App `settings.yaml` (under `config:`) |

A **bundle behavior** is what we have been describing — declared in a bundle, applies wherever that bundle composes. `behaviors/agents.yaml` is a bundle behavior: every sub-agent should inherit delegation instructions.

A **policy behavior** is structurally identical (a YAML file with `tools`/`hooks`/etc.) but is *not* included by any bundle. Instead, the *app* (the CLI or service that hosts Amplifier) composes it into the mount plan at runtime, only for root sessions, based on user configuration in `settings.yaml`.

The motivating example is notifications. If you put desktop-notification hooks into a bundle, every sub-agent spawn fires a notification; the user gets spammed. A policy behavior solves this two ways: (1) the app gates composition on `parent_id is None`, so only the root session gets the hook; (2) the user controls whether to enable it at all via `settings.yaml`:

```yaml
# ~/.amplifier/settings.yaml
config:
  notifications:
    desktop:
      enabled: true
      suppress_if_focused: true
    push:
      enabled: true
      service: ntfy
      topic: "my-amplifier-alerts"
```

The principle from `KERNEL_PHILOSOPHY.md`: *Mechanism, not policy. The kernel exposes capabilities and stable contracts. Decisions about behavior belong outside the kernel.* Bundles provide mechanism (the hook system, the event flow); apps provide policy (which hooks fire, when, for whom).

**Authoring rule.** If your behavior should run in every sub-agent and recipe step, it is a bundle behavior — include it from your root `bundle.md`. If it should only run at the user-facing root, document it as a policy behavior, do *not* include it from a bundle, and check `parent_id` in the hook implementation:

```python
async def handle_event(self, event: str, data: dict) -> HookResult:
    if data.get("parent_id"):                  # sub-session — skip
        return HookResult(action="continue")
    # ... root-only logic
```

**Related**: Chapter 2 (composition merge rules); 3.6 Spawn (which depends on tool config in behaviors).

## 3.6 Spawn: tool inheritance for child agents

When an agent is spawned (via `tool-task` or the newer `tool-delegate`), what tools does the child see? The default is "everything the parent had." That is rarely what you want. **Spawn** configuration controls the inheritance policy.

### Why it exists

Two real problems force this control:

1. **Runaway delegation.** If `tool-task` itself is inherited, child agents can spawn grandchild agents, which can spawn great-grandchildren, indefinitely. You almost always want a single layer of delegation, not a tree.
2. **Capability scoping.** A `bug-hunter` should not have a `tool-publish-to-pypi` if the parent has one. A spawned agent narrows the parent's surface area, both for safety and to keep the agent focused.

### How to configure it

Two equivalent locations. The newer pattern is on the delegate/task tool's `config:` block (this is the one `BUNDLE_GUIDE.md` and `PATTERNS.md` recommend):

```yaml
# In a behavior YAML or bundle.md
tools:
  - module: tool-task
    source: git+https://github.com/microsoft/amplifier-module-tool-task@main
    config:
      exclude_tools: [tool-task]      # Inherit everything EXCEPT these
      # or, equivalently, an allowlist:
      # inherit_tools: [tool-filesystem, tool-bash]   # Inherit ONLY these
```

The older pattern is a top-level `spawn:` section on the bundle (still supported and deep-merged like the others — see Chapter 2):

```yaml
spawn:
  exclude_tools: [tool-task]
  # or
  # tools: [tool-a, tool-b]
```

The two forms target the same concept. Prefer the tool-config form because the design rationale (`PATTERNS.md`) is clean: "tool inheritance config belongs in tool-task's config section because the task tool is the module that consumes this config; without `tool-task` mounted, this config is meaningless."

### The common pattern

Almost every coordinator wants the same setup: agents inherit working tools but cannot themselves delegate further. From `behaviors/agents.yaml`:

```yaml
tools:
  - module: tool-delegate
    config:
      settings:
        exclude_tools: [tool-delegate]
        exclude_hooks: []
```

The child agent inherits `tool-filesystem`, `tool-bash`, `tool-search`, etc., but does **not** inherit `tool-delegate`. It does the work itself rather than spawning a sub-sub-agent.

### Per-agent tool overrides

Agents can also declare their own `tools:` block (you saw this in `bug-hunter.md` in 3.3). When an agent is spawned, the inheritance policy combines with the agent's own declarations: the agent's declared tools are mounted, plus whatever the parent's spawn policy allows. If you want an agent to have a *narrower* tool surface than the parent, declare its tools explicitly and rely on the inheritance policy to pass through nothing extra.

**Related**: Chapter 2 (composition); 3.3 Agents (per-agent `tools:` declarations); Chapter 4 §4.5 (plan mode).

## 3.7 Recipes

A **Recipe** is a YAML workflow — a declarative, parameterized, multi-step pipeline that executes against an Amplifier session. Recipes are *not* a kernel concept and they are *not* part of foundation. They are a capability shipped by the external `amplifier-bundle-recipes` bundle (along with `tool-recipes`, the tool that executes them, and supporting agents like `recipe-author` and `result-validator`). When you `include` `recipes:behaviors/recipes`, your bundle gains the ability to run, author, and validate recipes.

### Why recipes exist

Some workflows are repeatable enough to deserve codification. "Audit a repo for compliance," "Validate every bundle in a repo," "Generate documentation across an ecosystem" — each is a sequence of bash steps, agent invocations, and conditional branches that ought to live as a versioned artifact, not as a one-off prompt. Recipes give you that artifact: a YAML file you can check in, version, parameterize, and rerun deterministically.

### How to recognize one

- Lives in `recipes/*.yaml` within a bundle that includes the recipes behavior.
- Top-level keys (not `bundle:` — recipes are not bundles): `name`, `description`, `version`, `author`, `tags`, `recursion`, `context`, `steps`.
- Each `steps` entry has an `id`, a step `type` (or `agent` for agent invocations), and step-specific fields.

### Recipe shape, by example

This skeleton is from `amplifier/recipes/repo-audit.yaml` — pared down to show structure, with full step bodies removed.

```yaml
name: "repo-audit"
description: "Audit a single Amplifier ecosystem repository for compliance with Microsoft standards."
version: "1.4.0"
author: "Amplifier Team"
tags: ["audit", "compliance", "github", "amplifier"]

recursion:
  max_depth: 2
  max_total_steps: 50

context:
  repo_owner: "microsoft"
  repo_name: ""
  create_fix_pr: "false"
  dry_run: "false"
  working_dir: "./ai_working/repo-audit"
  reference_repo: "microsoft/amplifier-core"

steps:
  - id: "setup"
    type: "bash"
    command: |
      mkdir -p "{{working_dir}}/{{repo_name}}"
      mkdir -p "{{working_dir}}/reference"
    output: "setup_result"
    timeout: 30
    on_error: "fail"

  - id: "fetch-repo-info"
    type: "bash"
    command: |
      gh repo view "{{repo_owner}}/{{repo_name}}" --json name,owner,description ...
    output: "repo_info_raw"
    timeout: 60
    retry:
      max_attempts: 3
      backoff: "exponential"
      initial_delay: 5
    on_error: "continue"

  - id: "compare-boilerplate"
    type: "bash"
    parse_json: true
    command: |
      ...
    output: "boilerplate_check"

  - id: "fix-readme-content"
    condition: "{{create_fix_pr}} == 'true' or {{dry_run}} == 'true'"
    agent: "foundation:modular-builder"
    prompt: |
      Fix the README.md file for {{repo_owner}}/{{repo_name}} ...
      Audit results: {{readme_check}}
    output: "readme_fix_result"
    timeout: 300
    on_error: "continue"

  - id: "generate-report"
    agent: "foundation:zen-architect"
    mode: "ANALYZE"
    prompt: |
      Generate a comprehensive audit report:
      {{boilerplate_check}}
      {{readme_check}}
      ...
    output: "audit_report_content"
    timeout: 300
    on_error: "fail"

  - id: "write-report"
    type: "bash"
    command: |
      cat << 'EOF' > "{{working_dir}}/{{repo_name}}/audit-report.md"
      {{audit_report_content}}
      EOF
    output: "report_write_result"
```

Walk the structure top-down:

- **Header** (`name`, `description`, `version`, `author`, `tags`) — metadata. `version` matters: the recipe tool keys session reuse and validation against it.
- **`recursion:`** — guards. `max_depth` limits recipe-calling-recipe nesting; `max_total_steps` is a global cap. Without these, a buggy recipe can loop forever.
- **`context:`** — input parameters and defaults. Callers override them at invocation time:
  ```bash
  amplifier recipes execute repo-audit.yaml \
    --context '{"repo_name": "amplifier-core", "create_fix_pr": "true"}'
  ```
  Note that booleans are typically passed as strings (`"true"` / `"false"`) so they can be referenced in `{{...}}` template conditions without surprises.
- **`steps:`** — the linear pipeline. Each step has an `id` (referenced by later steps and in error messages), a step type, and `output:` which names the variable later steps interpolate.

### Step types you will see

The shape of step types the local recipes use:

| Step type | Purpose | Key fields |
|-----------|---------|------------|
| `type: bash` | Run shell commands; capture stdout. | `command`, `output`, `timeout`, `retry`, `on_error`, `parse_json`, `condition` |
| `agent: foundation:zen-architect` | Spawn an Amplifier agent with a prompt. | `prompt`, `mode`, `output`, `timeout`, `on_error`, `condition` |
| `type: recipe` | Invoke another recipe as a sub-pipeline. | `recipe`, `context`, `output` |

Step features that recur:

- **`{{var}}` templating** — interpolates from the `context:` block and from any earlier step's `output`.
- **`condition:`** — string expression evaluated at step time; the step is skipped if it evaluates falsy. Used heavily for "only do this in dry-run."
- **`on_error: fail | continue`** — fail aborts the recipe; continue lets the pipeline carry on with the failed output captured as-is.
- **`retry:`** — declarative retry with backoff strategy; useful for flaky network calls (`gh api`, `curl`).
- **`parse_json: true`** — declares the step's stdout is JSON; downstream `{{step.output.field}}` references can dereference fields cleanly.
- **`output_exit_code:`** — for bash steps, captures the process exit code as a separate variable.

### Authoring a recipe

The `recipes:recipe-author` agent (in the recipes bundle) is the right tool for this — it is conversational and knows the schema. When writing one by hand, a useful order:

1. State the **goal** in `description`.
2. Define `context:` parameters and sensible defaults.
3. Set `recursion` caps. (Be honest: how deep can this legitimately go?)
4. Sketch `steps:` linearly. Each step does one thing; outputs flow to the next.
5. For LLM steps (`agent: ...`), write the `prompt:` so the agent has everything it needs from prior `{{outputs}}`.
6. Add `condition:` for branches; add `retry:` and `on_error: continue` only where genuinely needed.

Treat `repo-audit.yaml` as the reference for naming, comment headers (`# === STEP N: ...`), and the bash-then-agent-then-bash pattern (use bash for IO and parsing, agents only for content generation, then bash again to write the LLM output to a file deterministically).

**Related**: 3.5 Behaviors (the recipes bundle ships a behavior); Chapter 4 (`amplifier recipes execute`).

## 3.8 Skills

A **Skill** is a packaged capability shipped by `amplifier-bundle-skills` and discovered by `tool-skills`. Foundation registers its own `skills/` directory with the skills tool (you can see this in `behaviors/agents.yaml` — `tool-skills.config.skills` lists the skills source). The agent is told "skill X exists and can be loaded on demand"; when needed, the agent invokes the tool to fetch the skill's content into its context window.

### Why skills are not tools

This is the easy point of confusion. A **Tool** is a Python module that the LLM invokes via the function-calling protocol; it executes code (read a file, run bash, hit an API) and returns a result. A **Skill** is *content* — a markdown bundle of instructions, examples, and patterns — that the LLM loads on demand. Tools change state and return data; skills change context and return knowledge.

The shorthand: a tool *does* something; a skill *teaches* the LLM to do something better. They commonly work together — `creating-amplifier-modules` is a skill that teaches the LLM how to use `tool-filesystem` and `tool-bash` to build a new tool module.

### How to recognize one

Skills are bundle-shipped, not in this repo, so you will recognize them in two ways:

- **Behavior YAML registers them.** Look for `tool-skills` in a behavior's `tools:` block, with a `config.skills:` list pointing at one or more skill source URIs (git URLs, paths, or namespace references).
- **Soft references in agent instructions.** Heavy expert agents like `foundation-expert.md` will say `Load skill creating-amplifier-modules` or `@foundation:skills/bundle-to-dot/SKILL.md` — those are pointers, not eager loads.

The authoring of new skills lives outside the local repos (in `amplifier-bundle-skills`); treat skills here at the level the docs describe — concept, role, shape — and use the shipped skills as content.

**Related**: 3.5 Behaviors (skills are wired in via tool-skills config); Chapter 1 (tools as kernel modules — the contrast).

## 3.9 Choosing the right artifact

When you have a new capability to add, the question is which artifact to author. Use this decision order:

1. **Will any LLM session need to do this work via a function call?** If yes, you need a **Tool** module (Chapter 1) — code that runs and returns a result. Tools are the only artifact that *executes* in the LLM's tool-call loop.
2. **Is this a focused, reusable role with its own model and tool set?** If yes, write an **Agent**. Examples: a debugger, a code reviewer, a domain expert. Agents make sense when the work is non-trivial enough to warrant its own description, instructions, and tool surface.
3. **Are you shipping a coherent capability — agents, context, possibly tools and hooks — that other bundles should reuse?** If yes, package it as a **Behavior**. This is almost always the right answer for any non-trivial new capability you want to share.
4. **Is the workflow a deterministic, parameterized pipeline of bash + agent invocations?** If yes, write a **Recipe**. Recipes shine for repeatable, multi-step work like audits, validations, and generation pipelines.
5. **Is it instructional content the LLM should be able to load on demand?** If yes, author a **Skill** (in `amplifier-bundle-skills` or your own bundle, registered via `tool-skills`).

A quick comparison:

| Artifact | Lives in | Purpose | Executed by |
|----------|----------|---------|-------------|
| Tool (module) | `modules/tool-*` (Python) | Do something — IO, computation, side effects | The LLM's tool-call loop |
| Agent | `agents/*.md` | Run a focused sub-session with its own role | `tool-task` / `tool-delegate` |
| Behavior | `behaviors/*.yaml` | Bundle a capability for reuse across bundles | Composed via `includes` |
| Recipe | `recipes/*.yaml` | Run a deterministic multi-step workflow | `tool-recipes` |
| Skill | external skills bundle | Provide on-demand instructional content | `tool-skills` |

A practical heuristic: **if you find yourself writing the same agent-spawning prompt twice, it should be a recipe.** **If you find yourself copying the same `tool-x` + `agents.include` + `context.include` block into two bundles, it should be a behavior.** **If you find yourself with a 500-line context file that loads in every session, the heavy half belongs inside an agent (3.2).**

## 3.10 Self-check

Try answering these without scrolling back. They cover authoring decisions and frontmatter literacy.

1. You see a markdown file under `agents/` whose frontmatter starts with `meta: { name: foo, description: "..." }` and ends with `@foundation:context/shared/common-agent-base.md`. Why does the file start with `meta:` instead of `bundle:`, and what are the two effects of that final `@mention`?

2. A teammate writes an agent description that reads, in full: *"Helps with code review."* Apply the `AGENT_AUTHORING.md` checklist. Name three concrete items the description is missing, and explain why a sparse description causes "delegation failures."

3. You are writing a behavior that adds three new agents and registers a heavy ~600-line `DOMAIN_GUIDE.md`. Where should the heavy doc live — in `behavior.context.include`, in a `@mention` inside one of the agents, or in `@foundation:context/`? Justify the choice using the context-sink pattern.

4. Read this fragment and explain what each field does:

   ```yaml
   meta:
     name: my-agent
     description: "..."
     model_role: [coding, general]
     provider_preferences:
       - provider: anthropic
         model: claude-sonnet-*
   ```

   Which field wins if the routing matrix has a `coding` role mapped to `openai`?

5. The `tool-delegate` block in `behaviors/agents.yaml` has `exclude_tools: [tool-delegate]`. What does this configuration prevent, and why is the default to exclude rather than include?

6. A user wants notifications on every Amplifier run. Should the notifications hook be added to a bundle behavior (in `behaviors/notifications.yaml` and included from `bundle.md`) or shipped as a policy behavior (composed by the app from `settings.yaml`)? Cite the rule from `POLICY_BEHAVIORS.md` that decides.

7. You want to codify a five-step workflow that audits every repo in a list, generates a report per repo, and emails a summary. Should this be an agent or a recipe? What concrete features of the recipe schema (from `repo-audit.yaml`) make it the better fit?

8. Tools and skills both let the LLM "do something it could not do before." Give a one-sentence definition of each that makes the distinction unambiguous, and name one shipped example of each from foundation's directories.

---

If you can answer all eight, you have what you need to author a small but well-formed agent and behavior, and to read any artifact in `amplifier-foundation/agents/` or `amplifier-foundation/behaviors/` and explain its parts. Chapter 4 picks up where this leaves off: the CLI commands that run, validate, and inspect the artifacts you have learned to write.
