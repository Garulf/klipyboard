from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from klipyboard.cache import ThumbnailCache
from klipyboard.klipy import GifItem
from klipyboard.service import DEFAULT_ICON, GifService

ITEM_A = GifItem(id="1", title="a", thumbnail_url="https://x/1.jpg", gif_url="https://x/1.gif")
ITEM_B = GifItem(id="2", title="b", thumbnail_url="https://x/2.jpg", gif_url="https://x/2.gif")


class FakeClient:
    def __init__(self, items: List[GifItem]) -> None:
        self._items = items
        self.search_calls = []
        self.trending_calls = 0

    async def search(self, query: str, per_page: int = 20) -> List[GifItem]:
        self.search_calls.append((query, per_page))
        return self._items

    async def trending(self, per_page: int = 20) -> List[GifItem]:
        self.trending_calls += 1
        return self._items


async def test_search_downloads_and_caches_missing_thumbnails(tmp_path: Path):
    cache = ThumbnailCache(tmp_path / "thumbnails")
    client = FakeClient([ITEM_A])
    downloaded_urls = []

    async def download(url: str) -> bytes:
        downloaded_urls.append(url)
        return b"jpeg-bytes"

    service = GifService(client, cache, download)
    resolved = await service.search("cat")

    assert downloaded_urls == ["https://x/1.jpg"]
    assert resolved[0].item is ITEM_A
    assert resolved[0].icon == str(cache.path_for("1"))
    assert cache.has("1") is True


async def test_search_reuses_cached_thumbnail_without_downloading(tmp_path: Path):
    cache = ThumbnailCache(tmp_path / "thumbnails")
    cache.store("1", b"already-cached")
    client = FakeClient([ITEM_A])

    async def download(url: str) -> bytes:
        raise AssertionError("should not download a cached thumbnail")

    service = GifService(client, cache, download)
    resolved = await service.search("cat")

    assert resolved[0].icon == str(cache.path_for("1"))


async def test_search_falls_back_to_default_icon_on_download_failure(tmp_path: Path):
    cache = ThumbnailCache(tmp_path / "thumbnails")
    client = FakeClient([ITEM_A])

    async def download(url: str) -> bytes:
        raise RuntimeError("network blew up")

    service = GifService(client, cache, download)
    resolved = await service.search("cat")

    assert resolved[0].icon == DEFAULT_ICON
    assert cache.has("1") is False


async def test_trending_delegates_to_client_trending(tmp_path: Path):
    cache = ThumbnailCache(tmp_path / "thumbnails")
    client = FakeClient([ITEM_A, ITEM_B])

    async def download(url: str) -> bytes:
        return b"x"

    service = GifService(client, cache, download)
    resolved = await service.trending()

    assert client.trending_calls == 1
    assert [r.item.id for r in resolved] == ["1", "2"]


async def test_search_passes_query_and_per_page_through(tmp_path: Path):
    cache = ThumbnailCache(tmp_path / "thumbnails")
    client = FakeClient([])

    async def download(url: str) -> bytes:
        return b"x"

    service = GifService(client, cache, download)
    await service.search("dog", per_page=5)

    assert client.search_calls == [("dog", 5)]
