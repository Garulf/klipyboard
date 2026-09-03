from __future__ import annotations

from pathlib import Path

from klipyboard.cache import ThumbnailCache


def test_has_is_false_before_store(tmp_path: Path):
    cache = ThumbnailCache(tmp_path / "thumbnails")
    assert cache.has("42") is False


def test_store_then_has_and_path_for(tmp_path: Path):
    cache = ThumbnailCache(tmp_path / "thumbnails")

    path = cache.store("42", b"fake-jpeg-bytes")

    assert path == cache.path_for("42")
    assert path.read_bytes() == b"fake-jpeg-bytes"
    assert cache.has("42") is True


def test_store_creates_missing_directory(tmp_path: Path):
    target_dir = tmp_path / "does" / "not" / "exist"
    cache = ThumbnailCache(target_dir)

    cache.store("1", b"x")

    assert target_dir.exists()
    assert cache.has("1") is True


def test_path_for_is_stable_for_same_id(tmp_path: Path):
    cache = ThumbnailCache(tmp_path / "thumbnails")
    assert cache.path_for("42") == cache.path_for("42")
