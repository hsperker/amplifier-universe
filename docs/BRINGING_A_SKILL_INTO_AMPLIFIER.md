# How To Bring an Agent Skill (with MCP and a Python Script) into Amplifier

This guide walks through taking an [agentskills.io](https://agentskills.io) skill that
references an MCP server and ships a Python script, and wiring it into Amplifier.

> **Status: documented, not yet verified end to end.** Every step here is grounded
> in the Amplifier source files listed under Source References, but the full flow
> (skill loaded, MCP tools called, Python script executed) has not been run and
> observed in a live session. Treat it as an accurate reading of the mechanisms,
> and confirm against your own setup before relying on it.

## Before You Start: One Skill Is Actually Three Things

The single most important thing to understand is that Amplifier does **not** treat
"a skill that references MCP and brings a script" as one installable package. There
is no combined manifest. Instead you decompose your package into the three
mechanisms Amplifier already provides, then tie them together with instructions.

| Your piece | Amplifier mechanism | How it is wired |
|---|---|---|
| The `SKILL.md` skill | `tool-skills` `skills:` config | Point at a directory or git URL containing `*/SKILL.md` |
| The MCP reference | `tool-mcp` plus `.amplifier/mcp.json` | MCP servers mount as tools; the skill only *names* them |
| The Python script | A companion file run via the `bash` tool | The skill body says `python ${SKILL_DIR}/script.py` |

A skill is knowledge plus companion files plus instructions. It cannot itself
install an MCP server or register a tool. Those are separate, module level
concerns. The skill's job is to tie them together by referencing them.

## Prerequisites

Make sure the bundle you run includes these three modules. The standard
`foundation` bundle already provides all of them:

* `tool-skills` (from `amplifier-bundle-skills`) so skills can be discovered and loaded.
* `tool-mcp` (from `amplifier-module-tool-mcp`) so MCP servers can be mounted as tools.
* `tool-bash` (from `amplifier-module-tool-bash`) so the agent can run your Python script.

## Step 1: Lay Out the Skill as a Directory

A skill is just a directory that contains a `SKILL.md` file. Place your Python
script alongside it as a companion file:

```
my-skill/
  SKILL.md            # required: YAML frontmatter plus markdown body
  do_thing.py         # your Python script (a companion file)
  examples/           # optional companion files
    sample.json
```

## Step 2: Write the SKILL.md

Use the standard Agent Skills frontmatter. The `description` is injected into
context on every turn, so keep it tight and say *when* to use the skill.

```markdown
---
name: my-skill
description: "What this skill does and WHEN to use it. This line is shown every turn, so keep it short and specific."
version: 1.0.0
---

# My Skill

When the user asks for X:

1. Use the `your-mcp-server` MCP tools to fetch Y.
2. Run the bundled script:

       python ${SKILL_DIR}/do_thing.py --input Y

3. Summarize the result for the user.
```

Notes on the body:

* Reference the MCP tools **by name**. The skill does not start the MCP server.
  It assumes the server is already mounted (see Step 4) and the tools are callable.
* `${SKILL_DIR}` is the documented variable that resolves to the skill's directory
  at load time. Use it for every path to a companion file.

### Optional frontmatter you may want

| Key | Effect |
|---|---|
| `user-invocable: true` | Registers the skill as a `/my-skill` slash command. |
| `auto-load: true` | Loads the skill body at session startup. |
| `disable-model-invocation: true` | Hides it from the per turn visibility list (use for slash command only skills to save tokens). |
| `context: fork` | Loading the skill spawns an isolated subagent whose instructions are the skill body. |

## Step 3: Decide How the Python Script Runs

This is the part people trip on. A script inside a skill is **not** automatically
a callable tool. There are two ways to execute it.

### Option A: The agent runs it via the bash tool (recommended)

Your skill body instructs the agent to call the `bash` tool with
`python ${SKILL_DIR}/do_thing.py`. This is a normal tool call.

* Works for both local and remote (git sourced) skills.
* Requires `tool-bash` to be mounted (the foundation bundle provides it).
* The agent decides when to run it, based on your instructions.

### Option B: Run the script at load time via shell preprocessing

Put a preprocessing directive in the body so its standard output is injected when
the skill loads:

```markdown
Current data snapshot:

!`python ${SKILL_DIR}/do_thing.py --report`
```

Important caveat: this shell preprocessing is **blocked for untrusted (remote)
skills** for security reasons. It only runs for local, trusted skills. If your
skill is loaded from a git URL, use Option A.

### When you need a real tool instead

If the script must be an LLM callable tool with its own input schema (not just
something the agent shells out to), that is a different and heavier mechanism. You
wrap it as an Amplifier tool module with a `mount()` function and a
`pyproject.toml` entry point under `[project.entry-points."amplifier.modules"]`.
Do this only if you genuinely need a first class tool. For most cases, Option A is
simpler and sufficient.

## Step 4: Wire Up the MCP Server

The skill only references MCP tools by name. You mount the server independently.

1. Confirm the `tool-mcp` bundle is included (the foundation bundle includes it).
2. Create `.amplifier/mcp.json` in your project:

```json
{
  "mcpServers": {
    "your-mcp-server": {
      "url": "https://example.com/mcp"
    }
  }
}
```

Now the MCP server's tools mount as regular tools, and your skill's instruction to
"use the `your-mcp-server` tools" resolves against them.

## Step 5: Register the Skill into Your Bundle

Add your skill's source to the `tool-skills` `skills:` list. This is exactly how
the foundation bundle registers its own skills. The discovery step globs
`*/SKILL.md` under each source, so each entry points at a directory that *contains*
skill directories.

```yaml
- module: tool-skills
  source: git+https://github.com/microsoft/amplifier-bundle-skills@main#subdirectory=modules/tool-skills
  config:
    skills:
      # Existing foundation skills
      - "git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=skills"
      # Your skills, local path
      - "/abs/path/to/my-skill-collection"
      # Your skills, remote git URL
      - "git+https://github.com/you/your-repo@main#subdirectory=skills"
```

Once registered, a visibility hook surfaces the skill's `name` and `description`
on every turn, and the agent loads the full body on demand by calling `load_skill`.

## Step 6: Verify

1. Start a session with your bundle.
2. Ask the agent to `load_skill(list=true)` (or just check that the skill appears
   in the visibility list). Your skill should be listed by name.
3. Trigger the workflow described in your skill body and confirm:
   * The MCP tools are callable (server mounted from `mcp.json`).
   * The Python script runs (agent shells out via the bash tool, or load time
     preprocessing injected its output).

## Packaging It So It Feels Like One Install

There is no single manifest that bundles "skill plus MCP plus script" as one unit.
If you want it to feel like one installable package, the cleanest approach is:

1. Put the skill directory **and** the Python script in one git repo, under a
   `skills/` folder.
2. Include a sample `.amplifier/mcp.json` snippet in that repo's README.
3. Document the install as two small edits:
   * Add one entry to `tool-skills` `config.skills` (your git URL).
   * Add the MCP server block to `.amplifier/mcp.json`.

That keeps the three mechanisms cleanly separated, which is what Amplifier wants,
while giving users a single repo to clone and a short, copy and paste install.

## Quick Reference Checklist

* [ ] Skill directory created with `SKILL.md` and the Python script inside it.
* [ ] `SKILL.md` frontmatter has `name`, `description`, `version`.
* [ ] Skill body references MCP tools by name and runs the script via `${SKILL_DIR}`.
* [ ] Python execution path chosen: bash tool (Option A) or load time preprocessing (Option B, local only).
* [ ] `.amplifier/mcp.json` created with the MCP server block.
* [ ] Skill source added to `tool-skills` `config.skills`.
* [ ] `tool-skills`, `tool-mcp`, and `tool-bash` all present in the bundle.
* [ ] Verified: skill is visible, MCP tools callable, script runs.

## Source References

* Skills mechanism: `amplifier-foundation/context/understanding-mechanisms/mechanisms/skills.md`
* Example `SKILL.md`: `amplifier-foundation/skills/bundle-to-dot/SKILL.md`
* Skill registration pattern: `amplifier-foundation/behaviors/agents.yaml`
* Skill discovery glob (`*/SKILL.md`): `amplifier-foundation/recipes/bundle-behavioral-model.yaml`
* MCP configuration and bundle inclusion: `amplifier-foundation/bundle.md`
