# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright>=1.55", "pillow>=11"]
# ///
"""Capture the README screenshots and the social preview image from the site.

Point it at a running build -- the local preview or the live site:

    cd site
    npm run build
    npx vite preview --port 4317
    # in another shell, from the repo root:
    uv run scripts/capture-screenshots.py http://localhost:4317/claude-cost-optimizer/

Writes docs/assets/screenshots/<page>-<desktop|phone>.webp for the README and
site/public/og-image.png (1200x630, the size X, LinkedIn and Slack crop to;
social scrapers do not accept SVG or WebP reliably, hence PNG). The Repo
Analyzer shot runs a real analysis of this repo through the GitHub API from the
headless browser, so it needs network access and one unauthenticated API
budget (a few calls of GitHub's 60 an hour).

Needs a Chromium for Playwright: `uvx playwright install chromium` once.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "assets" / "screenshots"
OG_IMAGE = ROOT / "site" / "public" / "og-image.png"

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900, "scale": 1},
    # iPhone 15-class width; captured at 2x so text stays sharp, then halved.
    "phone": {"width": 390, "height": 844, "scale": 2},
}
DEMO_REPO = "Sagargupta16/claude-cost-optimizer"
PAGES = {
    "home": "",
    "calculator": "calculator/",
    "analyzer": f"analyzer/?repo={DEMO_REPO}",
}


# What each shot frames, per viewport: a CSS selector scrolled to just below the
# sticky navbar, or None for the top of the page. The analyzer frames its report;
# on a phone the calculator frames the estimate, not the model list above it.
FRAMES = {
    ("analyzer", "desktop"): 'section[aria-label="Grade"]',
    ("analyzer", "phone"): 'section[aria-label="Grade"]',
    ("calculator", "phone"): "h2:has-text('Monthly Estimate')",
}
NAVBAR_CLEARANCE = 80


def settle(page: Page, name: str, viewport: str) -> None:
    """Wait for the page's own content, then let entrance animations finish."""
    page.wait_for_load_state("networkidle")
    if name == "analyzer":
        # ?repo= only fills the input; run the analysis and wait for the report.
        page.get_by_role("button", name="Analyze", exact=True).click()
    top = 0
    frame = FRAMES.get((name, viewport))
    if frame:
        target = page.locator(frame).first
        target.wait_for(timeout=60_000)
        top = page.evaluate(
            f"el => el.getBoundingClientRect().top + window.scrollY - {NAVBAR_CLEARANCE}",
            target.element_handle(),
        )
    # Scroll through once so scroll-triggered reveals have run, then to the framed spot.
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(600)
    page.evaluate(f"window.scrollTo(0, {top})")
    page.wait_for_timeout(1500)


def save_webp(png: bytes, out: Path, scale: int) -> None:
    img = Image.open(io.BytesIO(png)).convert("RGB")
    if scale > 1:
        img = img.resize((img.width // scale, img.height // scale), Image.LANCZOS)
    img.save(out, "WEBP", quality=82, method=6)
    print(
        f"{out.relative_to(ROOT).as_posix()}: {img.width}x{img.height}, {out.stat().st_size / 1024:.0f} KB"
    )


def save_png(png: bytes, out: Path) -> None:
    img = Image.open(io.BytesIO(png)).convert("RGB")
    img.save(out, "PNG", optimize=True)
    print(
        f"{out.relative_to(ROOT).as_posix()}: {img.width}x{img.height}, {out.stat().st_size / 1024:.0f} KB"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "base_url", help="site root, e.g. http://localhost:4317/claude-cost-optimizer/"
    )
    args = parser.parse_args()
    base = args.base_url if args.base_url.endswith("/") else args.base_url + "/"
    SHOTS.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for vp_name, vp in VIEWPORTS.items():
            context = browser.new_context(
                viewport={"width": vp["width"], "height": vp["height"]},
                device_scale_factor=vp["scale"],
                is_mobile=vp_name == "phone",
                has_touch=vp_name == "phone",
                color_scheme="dark",
            )
            page = context.new_page()
            for name, path in PAGES.items():
                page.goto(base + path)
                settle(page, name, vp_name)
                save_webp(
                    page.screenshot(), SHOTS / f"{name}-{vp_name}.webp", vp["scale"]
                )
            context.close()

        context = browser.new_context(
            viewport={"width": 1200, "height": 630}, color_scheme="dark"
        )
        page = context.new_page()
        page.goto(base)
        settle(page, "home", "desktop")
        save_png(page.screenshot(), OG_IMAGE)
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
