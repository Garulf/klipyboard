"""Flow Launcher rendering layer: turns GifService results into `Result`
objects and registers the `query` method and error handling on a
pyflowlauncher `Plugin`. Performs no network I/O and holds no caching
policy - that all lives in `klipyboard.service`.
"""

from __future__ import annotations

from typing import AsyncIterator, Callable

from pyflowlauncher import Plugin, Result
from pyflowlauncher.models.result import PreviewInfo

from klipyboard.klipy import GifItem, KlipyError
from klipyboard.service import DEFAULT_ICON, GifService, ResolvedGif
from klipyboard.settings import Settings

#: Ranks the settings/error prompt above (nonexistent) other matches.
_PROMPT_SCORE = 1000


def build(
    plugin: Plugin,
    service_factory: Callable[[], GifService],
    settings: Callable[[], Settings],
) -> None:
    api = plugin.launcher.api

    def _settings_result(title: str, subtitle: str) -> Result:
        return Result(
            title=title,
            subtitle=subtitle,
            icon=DEFAULT_ICON,
            score=_PROMPT_SCORE,
            # Command subclasses dict and is accepted at runtime wherever
            # pyflowlauncher expects a JsonRPCRequest (see discord-flow's
            # identical usage); the library's own type annotation just
            # hasn't caught up since its commands API redesign.
            json_rpc_action=api.open_setting_dialog(),  # type: ignore[arg-type]
        )

    def _preview_for(item: GifItem) -> PreviewInfo | None:
        if not item.preview_url:
            return None
        # Klipy's preview_url is a still JPEG, not the animated GIF - Flow's
        # preview panel is a plain WPF Image control that only ever shows a
        # GIF's first frame anyway, so a bigger static frame here is a real
        # upgrade over relying on the small IcoPath thumbnail with no loss.
        return PreviewInfo(
            PreviewImagePath=item.preview_url,
            Description=item.title,
            IsMedia=True,
            PreviewDeligate=None,
        )

    def _gif_result(resolved: ResolvedGif, score: int) -> Result:
        item = resolved.item
        return Result(
            title=item.title,
            subtitle="Press Enter to copy the GIF URL to your clipboard",
            icon=resolved.icon,
            score=score,
            copy_text=item.gif_url,
            preview=_preview_for(item),
            json_rpc_action=api.copy_to_clipboard(item.gif_url),  # type: ignore[arg-type]
        )

    async def query(query: str) -> AsyncIterator[Result]:
        if not settings().has_api_key:
            yield _settings_result(
                "Set your Klipy API key",
                "Press Enter to open settings and paste your Klipy API key",
            )
            return

        service = service_factory()
        stripped = query.strip()
        resolved = await service.search(stripped) if stripped else await service.trending()

        total = len(resolved)
        for index, item in enumerate(resolved):
            yield _gif_result(item, score=total - index)

    def _on_klipy_error(exc: KlipyError) -> Result:
        return Result(
            title="GIF search failed",
            subtitle="Couldn't reach Klipy - try again in a moment",
            icon=DEFAULT_ICON,
        )

    plugin.add_method(query)
    # pyflowlauncher>=1.2.1 walks the exception's MRO, so registering the
    # base KlipyError here also catches KlipyHTTPError/KlipyNetworkError.
    plugin.add_exception_handler(KlipyError, _on_klipy_error)
