# amplifier-universe

A personal learning workspace for the Amplifier ecosystem. The three Amplifier
repositories are vendored as submodules; everything else here is reference
material built around them.

## Layout

```
amplifier-universe/
├── amplifier-core/         # submodule — the Rust kernel + PyO3 bindings
├── amplifier-foundation/   # submodule — the bundle composition library
├── amplifier/              # submodule — the CLI reference application
├── GLOSSARY.md             # single-page glossary of every term in the system
├── study-guide/            # four-chapter walkthrough of the ecosystem
└── verification/           # executable proof that the guide is accurate
```

The three submodules track `main` (configured via `branch = main` in
`.gitmodules`). To pull the latest:

```bash
git submodule update --remote --merge
```

After that, commit the updated SHAs if you want collaborators to pick up the
same versions.

## Where to start

1. **`GLOSSARY.md`** — read once to recognize the vocabulary.
2. **`study-guide/`** — four chapters in dependency order:
   - Chapter 1, the kernel layer (`amplifier-core`)
   - Chapter 2, the composition layer (`amplifier-foundation`)
   - Chapter 3, authoring artifacts (agents, behaviors, recipes, skills)
   - Chapter 4, the CLI app and the wider ecosystem (`amplifier`)

   Each chapter ends with a self-check. The guide is text-only; no install
   required.

3. **`verification/`** — only relevant if you want to confirm the guide is
   true.
   - `verification/live-fire/` — scripts that install
     `amplifier_foundation` locally and exercise four claims from the guide
     (compose pipeline, merge rules, entry-point + mount, capability
     disambiguation). All four pass.
   - `verification/reader-test/` — a complete `tool-now` module built using
     only the study-guide chapters as a reference, demonstrating that a
     reader can ship a working tool from the guide alone.

## How this was built

The study guide and verification work were built using a fan-out / fan-in
pattern: parallel research agents producing per-chapter files; auditors
producing focused findings; targeted apply agents making surgical edits.
The trail is in the commit log. `study-guide/audit-findings/` keeps the
audit reports as a historical record of what was added and why.

## Status

Submodules pinned at the SHAs current at the time of the last
`git submodule update --remote`. The Amplifier project is in early preview;
submodule contents will drift. When something in the guide disagrees with
the source, the source wins — file an issue or open a PR against the
relevant chapter.
