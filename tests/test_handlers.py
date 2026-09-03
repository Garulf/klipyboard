from __future__ import annotations

from typing import List

from pyflowlauncher import Plugin
from pyflowlauncher.launcher import FlowLauncherV1

from klipyboard import handlers
from klipyboard.klipy import GifItem, KlipyHTTPError
from klipyboard.service import DEFAULT_ICON, GifService, ResolvedGif
from klipyboard.settings import Settings

ITEM_A = GifItem(id="1", title="cat jump", thumbnail_url="https://x/1.jpg", gif_url="https://x/1.gif")
ITEM_B = GifItem(id="2", title="cat nap", thumbnail_url="https://x/2.jpg", gif_url="https://x/2.gif")


class FakeService:
    def __init__(self, resolved: List[ResolvedGif], error: Exception | None = None) -> None:
        self._resolved = resolved
        self._error = error
        self.search_query = None
        self.trending_called = False

    async def search(self, query: str, per_page: int = 20) -> List[ResolvedGif]:
        self.search_query = query
        if self._error:
            raise self._error
        return self._resolved

    async def trending(self, per_page: int = 20) -> List[ResolvedGif]:
        self.trending_called = True
        if self._error:
            raise self._error
        return self._resolved


def _build(service: FakeService, settings: Settings) -> Plugin:
    plugin = Plugin(launcher=FlowLauncherV1())
    handlers.build(plugin, lambda: service, lambda: settings)
    return plugin


async def _run_query(plugin: Plugin, text: str) -> list[dict]:
    # trigger_event runs the registered "query" async generator to
    # completion and collects it into {'Result': [...], ...} via
    # EventHandler._await_maybe - each entry is a Result.to_json() dict
    # (Title/SubTitle/IcoPath/Score/CopyText/JsonRPCAction), not a Result
    # object. Mirrors discord-flow's tests/test_handlers.py run_query helper.
    response = await plugin._event_handler.trigger_event("query", text)
    return response["Result"]


async def test_missing_api_key_shows_settings_prompt():
    service = FakeService([])
    plugin = _build(service, Settings(api_key=""))

    results = await _run_query(plugin, "cat")

    assert len(results) == 1
    assert "API key" in results[0]["Title"]
    assert service.search_query is None


async def test_empty_query_shows_trending():
    resolved = [ResolvedGif(item=ITEM_A, icon="/tmp/1.jpg")]
    service = FakeService(resolved)
    plugin = _build(service, Settings(api_key="key"))

    results = await _run_query(plugin, "")

    assert service.trending_called is True
    assert len(results) == 1
    assert results[0]["Title"] == "cat jump"
    assert results[0]["IcoPath"] == "/tmp/1.jpg"
    assert results[0]["CopyText"] == "https://x/1.gif"


async def test_nonempty_query_searches():
    resolved = [ResolvedGif(item=ITEM_A, icon="/tmp/1.jpg")]
    service = FakeService(resolved)
    plugin = _build(service, Settings(api_key="key"))

    results = await _run_query(plugin, "cat")

    assert service.search_query == "cat"
    assert len(results) == 1


async def test_results_preserve_api_order_via_descending_score():
    resolved = [
        ResolvedGif(item=ITEM_A, icon="/tmp/1.jpg"),
        ResolvedGif(item=ITEM_B, icon="/tmp/2.jpg"),
    ]
    service = FakeService(resolved)
    plugin = _build(service, Settings(api_key="key"))

    results = await _run_query(plugin, "cat")

    assert results[0]["Score"] > results[1]["Score"]


async def test_result_missing_thumbnail_uses_default_icon():
    resolved = [ResolvedGif(item=ITEM_A, icon=DEFAULT_ICON)]
    service = FakeService(resolved)
    plugin = _build(service, Settings(api_key="key"))

    results = await _run_query(plugin, "cat")

    assert results[0]["IcoPath"] == DEFAULT_ICON


async def test_klipy_error_surfaces_as_failure_result():
    service = FakeService([], error=KlipyHTTPError(500))
    plugin = _build(service, Settings(api_key="key"))

    results = await _run_query(plugin, "cat")

    assert len(results) == 1
    assert "failed" in results[0]["Title"].lower()
