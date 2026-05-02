# Chapter 4 — The CLI App and the Ecosystem

`amplifier-core` is the kernel (Chapter 1). `amplifier-foundation` is the composition library and the default `foundation` bundle (Chapter 2). This chapter covers the third piece of the reference stack: the end-user CLI application, distributed via the `amplifier` repo and implemented in `amplifier-app-cli`. The CLI is one possible interface — the README is explicit that web, voice, daemon, and IDE interfaces will follow — but it is the interface most readers will install first, and it sets the conventions that other interfaces inherit. After the CLI, this chapter zooms out to the rest of the ecosystem: the `amplifier-bundle-*`, `amplifier-module-*`, and `amplifier-app-*` repo families, the entry-point mechanism that lets a Python package advertise a mountable module, and how to find what the community has already built.

## Concepts covered

- The default `foundation` bundle and what it ships
- `amplifier provider use ...` and provider scope (local / project / global)
- `amplifier bundle add | use | list | current | update`
- Sessions: `amplifier continue`, `amplifier session list`, `session show`, `session resume`
- Plan mode (`/think`, `/do`) and chat slash commands
- The log viewer (`amplifier-log-viewer`)
- Repo naming: `amplifier-bundle-*`, `amplifier-module-*`, `amplifier-app-*`
- Module entry points (`[project.entry-points."amplifier.modules"]`)
- Where the catalog lives and what a community repo looks like

---

## 4.1 First contact: install, init, run

**What it does.** Three commands take a fresh machine to a working chat:

```bash
# 1. UV — Python toolchain
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Amplifier — installs the CLI as a uv tool
uv tool install git+https://github.com/microsoft/amplifier

# 3. First-run wizard (provider + model + bundle)
amplifier init
```

The `amplifier` package itself is a thin wrapper; `uv tool install` resolves it and exposes the `amplifier` executable, which is implemented in `amplifier-app-cli`. Once installed, three usage shapes exist:

```bash
amplifier run "Explain async/await in Python"   # single-shot
amplifier                                        # interactive chat (default)
amplifier run --mode chat                        # explicit chat
```

`amplifier init` is optional. If you skip it, the first invocation that needs a provider runs the same wizard. The wizard writes credentials to `~/.amplifier/keys.env` and resolved settings to `~/.amplifier/settings.yaml`.

**Why it exists.** The `uv tool install` route avoids virtualenv ceremony — the CLI lives in its own isolated environment, on PATH, updateable in place. The wizard converts the four-axis config matrix (provider, bundle, module, source) into a guided flow so a new user does not need to read the configuration docs before sending their first prompt.

**Pitfalls.**
- **Native Windows shells are not supported.** Use WSL on Windows. The README and onboarding both flag this.
- **Re-running `amplifier init` does not wipe your existing config** — it edits in place. For a clean reinstall, see `USER_ONBOARDING.md` "Clean Reinstall (Recovery)": `rm -rf ~/.amplifier`, `uv cache clean`, `uv tool uninstall amplifier`, reinstall.

**Related.** `amplifier --install-completion` adds tab completion to bash/zsh/fish. Configuration files live at `~/.amplifier/settings.yaml`, `.amplifier/settings.yaml` (project), `.amplifier/settings.local.yaml` (local override).

---

## 4.2 Providers

A provider is the AI service the agent talks to. The CLI ships first-party support for Anthropic, OpenAI, Azure OpenAI, and Ollama; additional providers (Gemini, vLLM, Bedrock, GitHub Copilot, etc.) are available as runtime modules listed in `MODULES.md`.

### `amplifier provider use`

```bash
# Interactive — prompts for model and where to save
amplifier provider use openai

# Explicit
amplifier provider use anthropic --model claude-opus-4-6
amplifier provider use openai --model gpt-5.5
amplifier provider use ollama --model llama3
amplifier provider use azure-openai --deployment gpt-5.5 --use-azure-cli

# Inspect
amplifier provider current
amplifier provider list
```

**Per-command override.** Switching providers permanently is a session-level decision. To try a provider for a single prompt, use `--provider`:

```bash
amplifier run --provider openai "Write a haiku"
```

### Where credentials live

Credentials and settings are stored in three tiers, in precedence order:

| Scope     | Flag        | File                                | Audience              |
| --------- | ----------- | ----------------------------------- | --------------------- |
| Local     | `--local`   | `.amplifier/settings.local.yaml`    | Just you, gitignored  |
| Project   | `--project` | `.amplifier/settings.yaml`          | Team, committed       |
| Global    | `--global`  | `~/.amplifier/settings.yaml`        | All your projects     |

API keys live in `~/.amplifier/keys.env` (set by the wizard) and can also be supplied via environment variables — `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_KEY`, `AZURE_USE_DEFAULT_CREDENTIAL`, `OLLAMA_HOST`. When env vars are set, the wizard offers them as defaults.

### Pitfalls

- **Azure: deployment name vs model name.** Azure OpenAI requires you to pass the *deployment name* (the resource you provisioned in your Azure subscription), not the underlying model name like `gpt-4o`. The wizard explicitly warns about this. If you paste a model name, the API will return an HTTP 404 with a confusing message.
- **Azure auth has two paths.** `--use-azure-cli` uses `DefaultAzureCredential`, which works with `az login` locally and managed identity in Azure-hosted environments. The alternative is an API key. Pick one — they do not stack.
- **Scope flags are consequential.** `--local` is invisible to teammates; `--project` is committed. If you `amplifier provider use anthropic --project` you have just put your team on Anthropic. Use `--local` for personal preferences.
- **`amplifier provider current` shows the resolution chain**, not just the active provider. Read it when settings appear to ignore your changes.

**Related.** Bundles can declare their own provider preferences (Chapter 2 §2.4). A bundle's choice can be overridden by `provider use` at any scope.

---

## 4.3 Bundles in the CLI

A bundle (Chapter 2) is the unit of capability composition. The CLI has four verbs for managing them.

### `amplifier bundle add`

Installs a bundle into the local registry from a git source. The bundle name is derived from the bundle's own metadata, not from the URL.

```bash
amplifier bundle add git+https://github.com/microsoft/amplifier-bundle-recipes@main
amplifier bundle add git+https://github.com/microsoft/amplifier-bundle-design-intelligence@main
```

Once added, the bundle is referenced by its declared name (`recipes`, `design-intelligence`) — not by its URL.

### `amplifier bundle use`

Sets the active bundle. Same scope flags as `provider use`.

```bash
amplifier bundle use foundation        # default
amplifier bundle use recipes
amplifier bundle use my-team-bundle --project
```

### `amplifier bundle list` and `current`

```bash
amplifier bundle list      # all bundles in the registry
amplifier bundle current   # the active one (with scope it came from)
```

### `amplifier bundle update`

Refreshes installed bundles to the latest commit on their tracked branch. Tags and SHAs are immutable and never moved.

```bash
amplifier bundle update --check     # show what would change
amplifier bundle update             # update with confirmation
amplifier bundle refresh --mutable-only   # only branches, skip pinned versions
```

The same idea applies to modules: `amplifier module refresh`, `amplifier module check-updates`. `amplifier update` is the umbrella command that updates the CLI, modules, and bundles together.

### Per-command bundle override

```bash
amplifier run --bundle recipes "Generate a release-notes recipe"
```

### What `foundation` ships

`foundation` is the default bundle and what `amplifier init` configures unless you ask otherwise. From `amplifier-foundation/bundle.md`, it pulls together:

- **Orchestrator:** `loop-streaming` with extended thinking enabled.
- **Context manager:** `context-simple` (300k token budget, auto-compact at 80%).
- **Tools:** `tool-filesystem`, `tool-bash`, `tool-web`, `tool-search`, plus a `delegate` tool for sub-agent dispatch.
- **Agents (foundation namespace):** `bug-hunter`, `explorer`, `file-ops`, `git-ops`, `integration-specialist`, `modular-builder`, `post-task-cleanup`, `security-guardian`, `test-coverage`, `web-research`, `zen-architect`.
- **Behaviors:** sessions, status-context, redaction, todo-reminder, streaming-UI, agents.
- **Included external bundles:** recipes, design-intelligence, python-dev, shadow, skills, browser-tester, superpowers, hook-shell, MCP, filesystem apply-patch, routing-matrix.

This is heavier than the "minimal" bundle described in some older docs — `foundation` v2 is a development-ready environment in a single bundle. The lighter `minimal.yaml`, `with-anthropic.yaml`, and `with-openai.yaml` reference bundles in `amplifier-foundation/bundles/` exist for embedded apps and tests.

The README's older table mentions `dev`, `recipes`, `full` as separate bundles. In practice today, `foundation` covers most development use; `recipes` and `design-intelligence` are added by URL when you want their dedicated agents.

### Pitfalls

- **`amplifier bundle add` is *not* `amplifier bundle use`.** Adding installs; using activates. Many first-run sessions look broken because the user added a bundle and never switched to it.
- **A bundle can change your provider.** If a bundle's YAML declares a provider preference and you run `amplifier bundle use <name>`, your effective provider may change. Run `amplifier provider current` after switching bundles when in doubt.
- **`@main` is mutable.** Bundles pinned to a branch can quietly change underneath you on `bundle update`. Pin to a tag (`@v1.2.0`) or SHA in production.

**Related.** Bundle authoring lives in Chapter 3. Bundle composition mechanics live in Chapter 2.

---

## 4.4 Sessions and persistence

Every interaction is automatically persisted to disk under `~/.amplifier/projects/<project-slug>/sessions/<session-id>/`. Each session directory contains:

- `transcript.jsonl` — the message history.
- `events.jsonl` — every tool call, hook fire, approval, etc.
- `metadata.json` — bundle, provider, timestamps.

The project slug is derived from the current working directory: `/home/user/repos/myapp` becomes `~/.amplifier/projects/-home-user-repos-myapp/`.

### Listing sessions

```bash
amplifier session list                       # current project only (default)
amplifier session list --all-projects        # everything you've ever run
amplifier session list --project /path/to/p  # a specific project
```

### Inspecting

```bash
amplifier session show <session-id>
amplifier session show <session-id> --detailed   # full transcript
```

### Resuming

```bash
amplifier continue                           # most recent, interactive
amplifier continue "follow-up question"      # most recent, single-shot
amplifier session resume <session-id>        # specific session, interactive
amplifier run --resume <session-id> "prompt" # specific session, single-shot
amplifier session resume <id> --bundle full  # resume with a different bundle
```

### Maintenance

```bash
amplifier session delete <session-id>
amplifier session cleanup
```

### Project scoping is a feature *and* a surprise

`amplifier session list` defaults to the current directory's slug. Move to a different project, run `session list`, and you see different sessions — by design, so daily work stays organized. The surprise: `cd /tmp; amplifier session list` will look empty even if you have hundreds of sessions elsewhere. Use `--all-projects` when something is missing, or `cd` back to the original project.

The slug is path-derived. If you rename or move a project directory, its old sessions stay associated with the old path. They are still on disk under the old slug, reachable with `--project /old/path`, but `cd /new/path; amplifier session list` will show nothing until you run a new session there.

### Pitfalls

- **`amplifier continue` resolves "most recent" within the current project.** From a different directory, it picks the most recent session in *that* project.
- **Resuming with a different bundle is allowed but not always sensible.** Tools that existed in the original session may be absent in the new bundle; transcript references can become stale. The session ID provides continuity (Chapter 2's `PreparedBundle.create_session(session_id=...)` pattern), but the configuration around it can change.

**Related.** Hooks like `hooks-logging` write to `events.jsonl` in this directory; that is what the log viewer (§4.6) consumes.

---

## 4.5 Plan mode and chat affordances

Chat mode (`amplifier` with no subcommand) accepts slash commands as well as prose. The two most distinctive are `/think` and `/do`.

### `/think` and `/do`

```
> /think
[plan mode on — read-only tools only]

> Analyze the failure modes in src/auth/

[agent investigates without modifying anything]

> /do
[plan mode off — modifications allowed]
```

`/think` enables a read-only "plan mode" in which the agent uses inspection tools (filesystem read, search, web) but cannot write, edit, or run shell commands that mutate state. `/do` exits plan mode. Use this pattern when you want the agent to think out loud before touching anything — review the plan, then `/do` and let it execute.

### The full slash command set

From `USER_ONBOARDING.md` and `USER_GUIDE.md`:

| Command   | Purpose                                                |
| --------- | ------------------------------------------------------ |
| `/help`   | List all available slash commands                      |
| `/tools`  | List tools mounted in this session                     |
| `/agents` | List agents available to delegate to                   |
| `/status` | Show session ID, provider, bundle, token usage         |
| `/config` | Show resolved configuration                            |
| `/think`  | Enter plan mode (read-only)                            |
| `/do`     | Exit plan mode                                         |
| `/clear`  | Clear conversation context (does not delete the session) |
| `/save`   | Save the conversation transcript                        |

`exit` or `Ctrl+C` quits chat. `Ctrl+C` mid-execution interrupts the current turn but keeps the session alive.

### `@mentions`

Inside chat or single-shot prompts, `@path/to/file.md` injects file contents while keeping the literal `@path/to/file.md` as a reference marker the agent can use to cite. See `MENTION_PROCESSING.md` in the amplifier repo for the full grammar.

**Related.** `tool-slash-command` (a runtime module) lets bundles add their own slash commands as Markdown files.

---

## 4.6 Debugging: the log viewer

`amplifier-log-viewer` is a separate web-based application that reads the `events.jsonl` files emitted by `hooks-logging` and renders them as an interactive timeline. Installed and launched separately:

```bash
uv tool install git+https://github.com/microsoft/amplifier-app-log-viewer@main
amplifier-log-viewer
```

It lives under the `amplifier-app-*` naming convention (§4.7) and has its own repo at `microsoft/amplifier-app-log-viewer`. The CLI emits the events; the viewer is one of several possible consumers — anything that can parse JSONL can build its own dashboard.

For sessions where you want to read raw events directly:

```bash
less ~/.amplifier/projects/<slug>/sessions/<session-id>/events.jsonl
```

**Related.** Hooks taxonomy (Chapter 1). Session storage layout (§4.4).

---

## 4.7 Repo naming conventions

Amplifier uses three naming conventions to communicate, at a glance, what kind of artifact a repository contains. The conventions map directly to the architectural roles in `REPOSITORY_RULES.md`.

### `amplifier-bundle-*` — composable configurations

A bundle repo packages a `bundle.md` plus optional behaviors, agents, recipes, and skills. It is a *configuration* artifact, not a Python package; users install it via `amplifier bundle add git+...`.

Examples from `MODULES.md`:

- `amplifier-bundle-recipes` — multi-step orchestration
- `amplifier-bundle-design-intelligence` — 7 design agents
- `amplifier-bundle-python-dev` — ruff/pyright + Python expert agent
- `amplifier-bundle-skills` — Anthropic-format skills
- `amplifier-bundle-notify` — desktop and ntfy.sh push notifications
- Community: `amplifier-bundle-deepwiki`, `amplifier-bundle-perplexity`, `amplifier-bundle-memory`

### `amplifier-module-*` — runtime modules

A module repo is a Python package that mounts into the kernel via the entry-point protocol (§4.8). It implements one of the kernel contracts: provider, tool, hook, orchestrator, or context manager. Users do not normally install modules directly; bundles list them by `module:` reference and the foundation resolver fetches them.

Examples:

- Providers: `amplifier-module-provider-anthropic`, `-openai`, `-azure-openai`, `-gemini`, `-vllm`, `-ollama`
- Tools: `amplifier-module-tool-filesystem`, `-bash`, `-web`, `-search`, `-task`, `-mcp`
- Hooks: `amplifier-module-hooks-logging`, `-redaction`, `-approval`, `-streaming-ui`
- Orchestrators: `amplifier-module-loop-basic`, `-loop-streaming`, `-loop-events`

### `amplifier-app-*` — end-user applications

An app repo is a runnable program that consumes the foundation library to drive sessions for a specific use case. The CLI itself is `amplifier-app-cli`. The log viewer is `amplifier-app-log-viewer`. Voice and chat plugins for the daemon use the same convention.

Microsoft-published examples:

- `amplifier-app-cli` — the CLI you installed in §4.1
- `amplifier-app-log-viewer` — the log dashboard
- `amplifier-app-benchmarks` — evaluation harness

Community examples (`MODULES.md`): `amplifier-app-transcribe`, `amplifier-app-blog-creator`, `amplifier-app-voice`, `amplifier-app-tool-generator`, `amplifier-app-session-analyzer`.

### Two umbrella repos that do not follow the prefix

A few important repos predate or sit above the prefix scheme:

- **`amplifier`** — the entry-point repo you cloned in §4.1. Installs `amplifier-app-cli` as its executable.
- **`amplifier-core`** — the kernel.
- **`amplifier-foundation`** — the composition library and default bundle.
- **`amplifierd`** — a localhost HTTP/SSE daemon that exposes core + foundation over REST.

### Decision tree for choosing a repo type

If you are publishing something:

1. **Does it provide a runnable command?** (CLI, web app, daemon plugin, benchmark harness)
   → `amplifier-app-<name>`. Examples: a transcription tool, a custom chat UI.
2. **Does it implement a kernel contract** (Provider, Tool, Hook, Orchestrator, ContextManager) and need to mount via entry points?
   → `amplifier-module-<contract>-<name>`. Example: `amplifier-module-tool-jupyter`.
3. **Does it package a configuration** — agents, behaviors, system prompts, recipes, skills — for users to opt into via `bundle add`?
   → `amplifier-bundle-<name>`. Example: `amplifier-bundle-rust-dev`.

If your repo would *both* implement a tool *and* package agents, you have two artifacts. Publish the tool as `amplifier-module-tool-<name>` and the agents as `amplifier-bundle-<name>`, with the bundle declaring the module as a dependency. This is the pattern used by `amplifier-bundle-recipes` and friends.

### Pitfalls

- **Module repos often live alongside their bundles.** `amplifier-bundle-recipes` references modules from its own and other authors. Do not assume that everything inside an `amplifier-bundle-*` repo is itself a bundle — `behaviors/`, `recipes/`, and `agents/` subdirectories are common.
- **Community repos use the same prefixes.** `MODULES.md` clearly separates Microsoft-published from community-published artifacts, and prefixes a security warning to each community section: community code runs with full access to your filesystem and credentials. Treat the prefix as a hint about role, not provenance.

**Related.** `REPOSITORY_RULES.md` (the canonical reference). The dependency-based awareness rule explains why naming alone is not enough — repos can only reference what they depend on.

---

## 4.8 Module entry points

A module is a Python package whose import-time work is to expose a single function: `mount(coordinator, config)`. The `amplifier-foundation` resolver discovers this function via Python's standard entry-point mechanism, declared in the module's `pyproject.toml`.

### The exact stanza

From `amplifier-foundation/modules/tool-delegate/pyproject.toml`:

```toml
[project]
name = "amplifier-module-tool-delegate"
version = "0.1.0"
dependencies = ["amplifier-core>=1.2.1"]

[project.entry-points."amplifier.modules"]
tool-delegate = "amplifier_module_tool_delegate:mount"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["amplifier_module_tool_delegate"]
```

The two pieces that matter for discovery:

- **The group: `amplifier.modules`.** This is the well-known group name foundation scans. Any package that registers an entry point under this group is a candidate module.
- **The key: `tool-delegate`.** This is the *module ID* — what bundles reference. It must match the ID used in bundle YAML (`module: tool-delegate`).
- **The value: `amplifier_module_tool_delegate:mount`.** Importable path to the `mount` function.

Note the convention: `name` uses dashes (`amplifier-module-tool-delegate`), the import path uses underscores (`amplifier_module_tool_delegate`), and the entry-point key drops the `amplifier-module-` prefix (`tool-delegate`). All three are derived from the same logical name.

### Why the dependency line matters

```toml
dependencies = ["amplifier-core>=1.2.1"]
```

Modules depend only on `amplifier-core`. They do not depend on `amplifier-foundation` or any peer module — that is the kernel's "modules unaware of peers" rule from `REPOSITORY_RULES.md`. Some modules omit even the `amplifier-core` dependency on the assumption that the host environment provides it; both patterns appear in practice.

### Discovery flow

When the CLI starts a session:

1. The active **bundle** (`foundation` by default) declares modules by ID and source: `module: tool-delegate, source: git+https://...`.
2. **`amplifier-foundation`** resolves the source — it might `uv pip install` from git, use an already-cached version, or honor a local source override (`amplifier source add`).
3. Once installed, foundation reads the package's entry points under the `amplifier.modules` group and finds the `mount` function.
4. The **kernel coordinator** calls `mount(coordinator, config)`, which registers the module's contributions (a tool, a hook, a provider) on the appropriate mount points.

This is the same flow whether the module lives on PyPI, on GitHub, or in a local checkout pointed at by `amplifier source add tool-bash ~/dev/tool-bash --local`.

### Publishing your own module

For the system to discover your module, three things must be true:

1. The package builds and installs (any standard Python build backend works; foundation modules use `hatchling`).
2. `pyproject.toml` declares an entry point under `amplifier.modules` whose key is the module ID and whose value resolves to a `mount` function.
3. A bundle somewhere — yours or someone else's — references that module ID.

Once those are satisfied, `amplifier bundle add` of any bundle that lists your module will resolve it correctly. There is no central registry to register with; the entry-point mechanism is the registry.

### Pitfalls

- **The module ID and the package name are not the same string.** The ID is the entry-point key, not the package name. Mismatches cause silent "module not found" errors.
- **Module type prefix matters by convention only.** The kernel does not enforce that `tool-foo` registers a tool — it would happily mount whatever `mount()` does. The prefix is a contract with users, not the kernel.
- **`amplifier source show <id>`** is the diagnostic command when a module is not behaving as expected — it shows where the module is being resolved from across all scopes.

**Related.** Mount Plan and the `mount(coordinator, config)` signature are kernel concerns (Chapter 1). Bundle YAML's `module:` and `source:` fields are composition concerns (Chapter 2).

---

## 4.9 The ecosystem at a glance

The catalog of who-built-what lives in **`amplifier/docs/MODULES.md`**. It is the single document that lists:

- **Core infrastructure:** `amplifier-core`.
- **Applications:** Microsoft-built (`amplifier-app-cli`, `amplifier-app-log-viewer`, `amplifier-app-benchmarks`, `amplifierd`, `amplifier-chat`, `amplifier-voice`).
- **Libraries:** `amplifier-foundation`.
- **Bundles:** ~30 Microsoft-published (`recipes`, `design-intelligence`, `python-dev`, `notify`, `skills`, `superpowers`, ...) plus a community section.
- **Runtime modules:** providers, tools, context managers, hooks, orchestrators — Microsoft-published and community.
- **Community apps and bundles** in their own clearly labelled sections, each prefixed with a security warning.

**`REPOSITORY_RULES.md`** is the companion document that defines what each repo type can and cannot reference. The two-line summary: documentation lives in exactly one place, and a repo can only reference another repo it actually depends on. When you are unsure whether something belongs in your bundle's README, foundation's docs, or the kernel's specs, the decision tree in `REPOSITORY_RULES.md` answers it.

**For new authors:**

- Bundle authoring guide: `amplifier-foundation/docs/BUNDLE_GUIDE.md`.
- Agent authoring guide: `amplifier-foundation/docs/AGENT_AUTHORING.md`.
- Module development: `amplifier/docs/MODULE_DEVELOPMENT.md`.
- Embedding Amplifier in your own application: `amplifier-foundation/docs/APPLICATION_INTEGRATION_GUIDE.md`.

**Submitting to the catalog.** `MODULES.md` invites PRs to add new entries. There is no separate index server; the Markdown file is the index.

---

## 4.10 Self-check

1. You ran `amplifier bundle add git+https://github.com/microsoft/amplifier-bundle-recipes@main` and the new agents are still not showing up. What did you most likely forget?

2. Your teammate set Anthropic as the project provider, but your machine keeps using OpenAI. Which command shows you why, and which file is most likely overriding?

3. You want to try a single prompt with the `recipes` bundle without changing your default. Write the command.

4. You are in `/home/user/projectA`. You ran a session there yesterday and now `amplifier session list` shows nothing. Give two reasons this can happen.

5. You see a repo named `amplifier-bundle-frontdoor`. Without opening it, what kind of artifact is it, and which CLI command would install it?

6. A Python package wants to be discoverable as the `tool-jupyter` module. What is the exact `pyproject.toml` stanza?

7. The Azure wizard asks for a deployment name. Why is pasting `gpt-4o` here a bug, and what should you paste instead?

8. The agent is about to refactor a directory and you want to see its plan first. Which two slash commands frame this workflow?

---

### Answers (sketched)

1. `bundle add` installs; `bundle use recipes` (or `--bundle recipes` per command) activates it. Adding without using is a common first-run mistake.
2. `amplifier provider current` prints the resolution chain. A `.amplifier/settings.local.yaml` in your working directory takes precedence over the project file your teammate committed.
3. `amplifier run --bundle recipes "your prompt"`.
4. (a) The session was run from a different working directory and is therefore under a different project slug — try `amplifier session list --all-projects`. (b) The project directory was moved or renamed; old sessions are still on disk under the old slug and reachable with `--project /old/path`.
5. It is a *bundle*. Install with `amplifier bundle add git+https://github.com/<owner>/amplifier-bundle-frontdoor@main`, then `amplifier bundle use frontdoor`. (Note: review community bundles before installing — they execute arbitrary code with your credentials.)
6. ```toml
   [project.entry-points."amplifier.modules"]
   tool-jupyter = "amplifier_module_tool_jupyter:mount"
   ```
7. Azure routes by deployment name (the Azure resource you provisioned), not by model name. Pasting a model name returns 404. Paste the deployment string from the Azure portal.
8. `/think` to enter read-only plan mode while the agent investigates and proposes; `/do` to leave plan mode and let the proposal execute.
