"""Orchestrates the Klipy client and thumbnail cache into render-ready
results.

Pure policy layer: no Flow Launcher types here, so it stays testable with
fakes instead of the real network or filesystem semantics beyond tmp_path.
`handlers.py` is the only consumer, and it only ever sees ResolvedGif.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, List

from klipyboard.cache import ThumbnailCache
from klipyboard.klipy import GifItem, KlipyClient

DEFAULT_ICON = "icon.png"


@dataclass(frozen=True)
class ResolvedGif:
    item: GifItem
    icon: str


class GifService:
    def __init__(
        self,
        client: KlipyClient,
        cache: ThumbnailCache,
        download: Callable[[str], Awaitable[bytes]],
    ) -> None:
        self._client = client
        self._cache = cache
        self._download = download

    async def search(self, query: str, per_page: int = 20) -> List[ResolvedGif]:
        items = await self._client.search(query, per_page=per_page)
        return await self._resolve(items)

    async def trending(self, per_page: int = 20) -> List[ResolvedGif]:
        items = await self._client.trending(per_page=per_page)
        return await self._resolve(items)

    async def _resolve(self, items: List[GifItem]) -> List[ResolvedGif]:
        return [ResolvedGif(item=item, icon=await self._icon_for(item)) for item in items]

    async def _icon_for(self, item: GifItem) -> str:
        if self._cache.has(item.id):
            return str(self._cache.path_for(item.id))
        try:
            content = await self._download(item.thumbnail_url)
        except Exception:
            # A single bad thumbnail must not drop the result or fail the
            # whole query - fall back to the plugin's own icon.
            return DEFAULT_ICON
        path = self._cache.store(item.id, content)
        return str(path)
