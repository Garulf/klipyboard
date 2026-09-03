"""Plugin entrypoint.

Wiring only: builds a GifService factory (client + cache + downloader) and
hands it to `handlers.build`. No business logic lives here.

Settings note: `plugin.settings` stays `{}` until Flow's first JSON-RPC
request arrives inside `plugin.run()`. `_settings()` and `_build_service()`
are only ever called from inside a registered method (after that first
request lands), and read `plugin.settings` fresh every time, so changing the
API key in Flow's settings UI takes effect on the very next query.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

import httpx

from pyflowlauncher import Plugin

from klipyboard import handlers
from klipyboard.cache import ThumbnailCache
from klipyboard.klipy import KlipyClient
from klipyboard.service import GifService
from klipyboard.settings import Settings

plugin = Plugin()

DOWNLOAD_TIMEOUT = 10.0


def _settings() -> Settings:
    return Settings.from_raw(plugin.settings)


def _root_dir() -> Path:
    # plugin.root_dir walks up from sys.argv[0] looking for plugin.json; that
    # walk raises FileNotFoundError whenever the plugin isn't running from
    # inside a Flow Launcher plugin directory (e.g. under pytest), so this
    # must not propagate.
    try:
        return plugin.root_dir
    except FileNotFoundError:
        return Path(__file__).resolve().parent


def _cache_dir(root_dir: Path, env: Mapping[str, str]) -> Path:
    """Resolve the thumbnail cache's on-disk directory.

    Prefers Flow Launcher's per-plugin settings directory under %APPDATA%
    (the writable location Flow itself uses for plugin data on Windows);
    falls back to a `.cache` directory under the plugin root when APPDATA
    isn't set, which keeps this resolvable during local/dev runs off
    Windows.
    """
    appdata = env.get("APPDATA")
    if appdata:
        base = Path(appdata) / "FlowLauncher" / "Settings" / "Plugins" / "Klipyboard"
    else:
        base = root_dir / ".cache"
    return base / "thumbnails"


async def _download(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


def _build_service() -> GifService:
    settings = _settings()
    client = KlipyClient(settings.api_key)
    cache = ThumbnailCache(_cache_dir(_root_dir(), os.environ))
    return GifService(client, cache, _download)


handlers.build(plugin, _build_service, _settings)


def main() -> None:
    plugin.run()


if __name__ == "__main__":
    main()
