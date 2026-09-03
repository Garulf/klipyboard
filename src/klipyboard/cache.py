"""On-disk cache of downloaded GIF thumbnails, keyed by Klipy item id.

Flow renders local files but not remote URLs, so every result icon must
resolve to a path on disk. This cache is the only thing that persists
between runs - full search/trending result lists are never cached.
"""

from __future__ import annotations

from pathlib import Path


class ThumbnailCache:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def path_for(self, item_id: str) -> Path:
        return self._directory / f"{item_id}.jpg"

    def has(self, item_id: str) -> bool:
        return self.path_for(item_id).exists()

    def store(self, item_id: str, content: bytes) -> Path:
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self.path_for(item_id)
        path.write_bytes(content)
        return path
