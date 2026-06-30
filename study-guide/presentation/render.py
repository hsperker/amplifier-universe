"""Render each slide of amplifier-5min.html to a PNG.

Run from this directory:

    pip install playwright
    python render.py                # writes screenshots/slide-{1..7}.png

The script picks up a Chromium binary from $PLAYWRIGHT_BROWSERS_PATH (set
automatically by `playwright install`). On the managed remote environment
where this guide was authored, that env var points at /opt/pw-browsers and
no separate install is needed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("playwright is required: pip install playwright")

HERE = Path(__file__).resolve().parent
HTML = HERE / "amplifier-5min.html"
OUT = HERE / "screenshots"
OUT.mkdir(exist_ok=True)


def _wrap_for_file_url(raw: str) -> str:
    """The artifact harness wraps content in <html><head>...; do the same locally."""
    return (
        '<!doctype html><html><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'{raw}</html>'
    )


def _find_chromium() -> str | None:
    """Find a Chromium binary; rely on Playwright defaults if not found."""
    root = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
    if not root.exists():
        return None
    for candidate in sorted(root.glob("chromium-*/chrome-linux/chrome")):
        if candidate.is_file():
            return str(candidate)
    return None


def main() -> None:
    wrapped = HTML.with_suffix(".wrapped.html")
    wrapped.write_text(_wrap_for_file_url(HTML.read_text()))

    chromium = _find_chromium()
    with sync_playwright() as p:
        launch_kwargs = {"executable_path": chromium} if chromium else {}
        browser = p.chromium.launch(**launch_kwargs)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()
        page.goto(f"file://{wrapped}")
        page.wait_for_selector(".slide.active")

        for i in range(1, 8):
            if i > 1:
                page.keyboard.press("ArrowRight")
                page.wait_for_timeout(120)
            path = OUT / f"slide-{i}.png"
            page.screenshot(path=str(path), full_page=False)
            print(f"wrote {path.relative_to(HERE)}")

        browser.close()

    wrapped.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
