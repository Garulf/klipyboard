"""HTTP client for the Klipy GIF API.

Pure network + parsing layer: raises typed KlipyError subclasses instead of
letting httpx exceptions leak, and normalizes both observed response shapes
(`{"data": [...]}` and `{"data": {"data": [...]}}`) into a flat list of
GifItem. Never returns partially-invalid items - one missing a thumbnail or
GIF url is dropped rather than surfaced with a broken field.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

KLIPY_BASE = "https://api.klipy.com/api/v1"


@dataclass(frozen=True)
class GifItem:
    id: str
    title: str
    thumbnail_url: str
    gif_url: str


class KlipyError(Exception):
    """Base class for all Klipy client errors."""


class KlipyNetworkError(KlipyError):
    """Raised when the request itself fails (DNS, connection, timeout)."""


class KlipyHTTPError(KlipyError):
    """Raised when Klipy responds with a non-200 status code."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"Klipy returned HTTP {status_code}")


class KlipyClient:
    def __init__(self, api_key: str, timeout: float = 10.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    async def search(self, query: str, per_page: int = 20) -> List[GifItem]:
        return await self._fetch("gifs/search", {"q": query, "per_page": per_page})

    async def trending(self, per_page: int = 20) -> List[GifItem]:
        return await self._fetch("gifs/trending", {"per_page": per_page})

    async def _fetch(self, path: str, params: Dict[str, Any]) -> List[GifItem]:
        url = f"{KLIPY_BASE}/{self._api_key}/{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params)
        except httpx.RequestError as exc:
            raise KlipyNetworkError(str(exc)) from exc

        if response.status_code != 200:
            raise KlipyHTTPError(response.status_code)

        try:
            payload = response.json()
        except ValueError as exc:
            raise KlipyHTTPError(response.status_code) from exc

        return _parse_items(payload)


def _parse_items(payload: Any) -> List[GifItem]:
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, dict):
        data = data.get("data")
    if not isinstance(data, list):
        return []
    items = []
    for raw in data:
        item = _parse_item(raw)
        if item is not None:
            items.append(item)
    return items


def _parse_item(raw: Any) -> Optional[GifItem]:
    if not isinstance(raw, dict):
        return None
    item_id = raw.get("id")
    files = raw.get("file")
    if not item_id or not isinstance(files, dict):
        return None
    thumbnail_url = _dig(files, "xs", "jpg", "url")
    gif_url = _dig(files, "hd", "gif", "url") or _dig(files, "gif", "url")
    if not thumbnail_url or not gif_url:
        return None
    title = raw.get("title") or "GIF"
    return GifItem(id=str(item_id), title=title, thumbnail_url=thumbnail_url, gif_url=gif_url)


def _dig(mapping: Dict[str, Any], *keys: str) -> Optional[str]:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current if isinstance(current, str) else None
