"""Render the README screenshots and hero image with flow-render.

Usage (from the repo root):

    uv run --no-project --with flow-render==0.15.0 python docs/screenshots/render.py

Each ``<shot>.json`` is a flow-render config. A result's ``thumb`` (an emoji
on a two-colour gradient) stands in for a GIF thumbnail so the screenshots
never depend on the Klipy API or an API key.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from base64 import b64encode
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHOTS_DIR = ROOT / "docs" / "screenshots"
ASSETS_DIR = ROOT / ".github" / "assets"
THEMES = ("dark", "light")
HERO = {"shot": "hero", "theme": "dark", "css": ["win11-dark.css", "docs/screenshots/hero.css"]}

THUMB_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{start}"/><stop offset="1" stop-color="{end}"/>
</linearGradient></defs>
<rect width="128" height="128" fill="url(#g)"/>
<text x="64" y="68" font-size="84" text-anchor="middle" dominant-baseline="middle">{emoji}</text>
</svg>"""


def thumb_uri(emoji: str, colors: list) -> str:
    svg = THUMB_SVG.format(start=colors[0], end=colors[1], emoji=emoji)
    return "data:image/svg+xml;base64," + b64encode(svg.encode("utf-8")).decode("ascii")


def flow_render(args, out_path: Path) -> None:
    with tempfile.TemporaryDirectory() as out_dir:
        subprocess.run(["flow-render", *args, "-o", out_dir], check=True, cwd=ROOT)
        (rendered,) = Path(out_dir).glob("*.png")
        shutil.move(str(rendered), out_path)
    print(f"Wrote {out_path}")


def render_config(shot: str, css, out_path: Path, work: Path) -> None:
    config = json.loads((SHOTS_DIR / f"{shot}.json").read_text(encoding="utf-8"))
    config["icon"] = str((SHOTS_DIR / config["icon"]).resolve())
    for result in config["results"]:
        thumb = result.pop("thumb", None)
        if thumb:
            result["icon"] = thumb_uri(thumb["emoji"], thumb["colors"])
        else:
            result["icon"] = str((SHOTS_DIR / result["icon"]).resolve())
    config["css"] = css
    config_path = work / f"{out_path.stem}.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    flow_render(["-c", str(config_path)], out_path)


def main() -> None:
    shots = sorted(path.stem for path in SHOTS_DIR.glob("*.json") if path.stem != HERO["shot"])
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for shot in shots:
            for theme in THEMES:
                render_config(shot, f"win11-{theme}.css", ASSETS_DIR / f"{shot}-{theme}.png", work)
        render_config(HERO["shot"], HERO["css"], ASSETS_DIR / "hero.png", work)


if __name__ == "__main__":
    sys.exit(main())
