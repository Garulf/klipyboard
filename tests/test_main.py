from __future__ import annotations

from pathlib import Path

from klipyboard.__main__ import _cache_dir


def test_cache_dir_prefers_appdata(tmp_path: Path):
    env = {"APPDATA": str(tmp_path)}
    result = _cache_dir(tmp_path / "plugin-root", env)
    expected = tmp_path / "FlowLauncher" / "Settings" / "Plugins" / "Klipyboard" / "thumbnails"
    assert result == expected


def test_cache_dir_falls_back_to_plugin_root_without_appdata(tmp_path: Path):
    result = _cache_dir(tmp_path, {})
    assert result == tmp_path / ".cache" / "thumbnails"
