# Audit findings — amplifier (CLI app)

## Summary
Chapter 4 covers the user-facing CLI surface well (init, providers, bundles, sessions, plan mode, log viewer, repo conventions, entry points). The biggest gap is the **developer-side install/runtime mechanics** that live almost entirely in `LOCAL_DEVELOPMENT.md`, `MODULE_DEVELOPMENT.md`, and `context/development-hygiene.md`: the cache directory, the 6-layer module resolution order, the `amplifier reset` and `amplifier module dev` command families. A few minor factual rough edges around bundle/refresh nomenclature and clean-reinstall guidance.

## A. New terms worth promoting to the glossary

1. **Cache directory (`~/.amplifier/cache/`)** — where the actually-running module/library code lives as editable installs / egg-links. Section 6 of glossary discusses session paths but never mentions cache. (`amplifier/context/development-hygiene.md:22-40`.)
2. **Module resolution order (six layers)** — env var → `.amplifier/modules/<id>/` workspace → project `settings.yaml` → user `settings.yaml` → bundle `source:` → installed package. "First match wins." (`amplifier/docs/LOCAL_DEVELOPMENT.md:127-138`; `context/development-hygiene.md:124-130`.)
3. **Workspace convention (`.amplifier/modules/<id>/`)** — zero-config auto-discovered module dev directory. (`amplifier/docs/MODULE_DEVELOPMENT.md:75-108, 337-341`.)
4. **`amplifier reset`** — safe replacement for `rm -rf ~/.amplifier`; uninstalls + reinstalls so site-packages egg-links don't dangle. (`context/development-hygiene.md:56-80`.)
5. **`AMPLIFIER_MODULE_<ID>` env var** — highest-priority per-process source override. (`amplifier/docs/LOCAL_DEVELOPMENT.md:117-123`.)
6. **`amplifier module dev` subcommand family** — `init`, `link`, `list`, `status`, `test`, `create`; the dev-mode CLI surface (`amplifier/docs/MODULE_DEVELOPMENT.md:130-177`).

## B. Chapter 4 gaps

1. **No mention of `~/.amplifier/cache/` or the editable-install model.** Chapter 4 implies `uv tool install` puts the CLI in an isolated venv; it does, but the *running code* is the cache. Affects every "why is my change not seen?" troubleshooting flow.
2. **6-layer module resolution order is missing.** §4.8 covers entry-point discovery but not the override precedence — yet the chapter assumes readers can use `amplifier source add ... --local`. (`LOCAL_DEVELOPMENT.md:127-138`.)
3. **Clean-reinstall guidance in §4.1 is unsafe.** The pitfall recommends `rm -rf ~/.amplifier; uv tool uninstall amplifier; reinstall`. `development-hygiene.md:42-54` explicitly flags this as DANGEROUS (breaks the egg-link graph) and prescribes `amplifier reset` instead. See §C.
4. **`amplifier module dev …` workflow is absent** — the canonical way to develop modules (workspace init, link, status). Currently a reader who wants to develop a module is sent to §4.8 (publishing) with no on-ramp.
5. **Recipes-from-CLI invocation pattern omitted.** `recipes-usage.md:18` is explicit: "There is no `amplifier recipes` CLI command. Recipes are invoked via the `recipes` tool" — `amplifier tool invoke recipes operation=execute recipe_path=…`. Useful pointer for §4.3's recipes paragraph.
6. **Shadow environments unmentioned.** `development-hygiene.md:132-156` documents shadow-bundle isolated-test environments as the recommended pattern for testing local module changes; complements the source-override story in §4.8.

## C. Factual errors in Chapter 4

1. **§4.1 "Clean Reinstall" advice (line 48) recommends `rm -rf ~/.amplifier`.** This breaks the CLI because `~/.amplifier/cache/` holds editable-install targets that `~/.local/share/uv/tools/amplifier/.../site-packages/*.egg-link` point to. The supported path is `amplifier reset` (interactive) or `amplifier reset --full -y`. (`amplifier/context/development-hygiene.md:42-80`.)
2. **§4.3 mixes `bundle update` and `bundle refresh` as if synonymous.** Both are documented (`USER_GUIDE.md:364-371` uses `bundle refresh`; `MODULES.md:96-99` uses `bundle update`). The chapter shows `bundle update --check` and `bundle refresh --mutable-only` in the same block without flagging that they are sibling commands rather than one workflow.
3. **§4.6 omits the log-viewer port (`http://localhost:8180`)** documented in `TESTING_GUIDE.md:572`. Minor, but readers will look for it.

## D. Worth-citing references

1. `amplifier/context/development-hygiene.md` — the canonical "how the install actually works" doc; should be cited in §4.1 and §4.4.
2. `amplifier/docs/LOCAL_DEVELOPMENT.md` — 6-layer resolution, override scenarios; pair with §4.8.
3. `amplifier/docs/MODULE_DEVELOPMENT.md` — the `module dev` command family and workspace convention; the missing on-ramp for §4.8.
4. `amplifier/docs/TESTING_GUIDE.md` §"LLM Provider Debugging" (lines 540-576) — DEBUG event taxonomy (`llm:request:debug`, `llm:response:debug`) and log-viewer launch.
5. `amplifier/context/recipes-usage.md` — explains the `tool invoke recipes` pattern and the absence of an `amplifier recipes` command.

## E. Out of scope but noteworthy

- `amplifier/docs/DEVELOPER.md` self-describes as "more aspirational and forward looking than accurate today" (line 5) — Chapter 4 cites it as if authoritative; downgrade or caveat. Better current path: `MODULE_DEVELOPMENT.md`.
- `bundle.md` confirms `amplifier`'s namespace is **`amplifier`** (already reflected); the `@amplifier:context/...` mention pattern is worth showing in Chapter 3 alongside other namespace examples.
- ROADMAP.md is genuinely aspirational ("multi-Amplifier modes," metacognitive recipes for non-developers, mount-based context sharing) — none of it is shipping today; do not promote.
