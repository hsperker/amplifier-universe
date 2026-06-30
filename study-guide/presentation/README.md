# Presentation — Amplifier in 5 minutes

A seven-slide teaching deck that mirrors the study guide chapters in
compressed form. Intended for a 5-minute technical walk-through of
`amplifier-core` and `amplifier-foundation` for someone who already
knows what an agent is and wants the mental model fast.

## Files

- `amplifier-5min.html` — the deck (single self-contained HTML, no external
  resources). Open it in a browser; navigate with arrow keys, PageUp/Down,
  Space, or the on-screen buttons.
- `render.py` — produces PNG screenshots of each slide into
  `screenshots/` for previews, design review, or embedding in other docs.

## Rendering screenshots

```bash
pip install playwright
python render.py
# writes screenshots/slide-{1..7}.png
```

The script picks up Chromium from `$PLAYWRIGHT_BROWSERS_PATH` if set, or
falls back to Playwright's defaults.

## Scope

This is a teaching aid built from the study guide. It is not a sales pitch,
a competitive comparison, or a roadmap. If a slide ever disagrees with the
chapter it summarizes, the chapter wins — file an issue.

## Slides at a glance

1. Title.
2. The whole skeleton in one picture (Bundle → Mount Plan → Session → Coordinator).
3. Session lifecycle (`__init__`, `initialize`, `execute`, `cleanup`).
4. The five module protocols (Provider, Tool, Orchestrator, ContextManager, Hook).
5. The orchestrator loop in pseudocode.
6. Bundles and Hooks — the two layering primitives.
7. Take-home summary and where to read more.
