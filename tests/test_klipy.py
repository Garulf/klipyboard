from __future__ import annotations

import httpx
import pytest

from klipyboard.klipy import GifItem, KlipyClient, KlipyHTTPError, KlipyNetworkError

API_KEY = "test-key"

SEARCH_URL = f"https://api.klipy.com/api/v1/{API_KEY}/gifs/search"
TRENDING_URL = f"https://api.klipy.com/api/v1/{API_KEY}/gifs/trending"

ITEM = {
    "id": "42",
    "title": "cat jump",
    "file": {
        "xs": {"jpg": {"url": "https://cdn.klipy.com/thumb/42.jpg"}},
        "hd": {"gif": {"url": "https://cdn.klipy.com/hd/42.gif"}},
    },
}


async def test_search_returns_gif_items(httpx_mock):
    httpx_mock.add_response(
        url=f"{SEARCH_URL}?q=cat&per_page=20",
        json={"data": [ITEM]},
    )

    client = KlipyClient(API_KEY)
    items = await client.search("cat")

    assert items == [
        GifItem(
            id="42",
            title="cat jump",
            thumbnail_url="https://cdn.klipy.com/thumb/42.jpg",
            gif_url="https://cdn.klipy.com/hd/42.gif",
        )
    ]


async def test_search_handles_nested_data_shape(httpx_mock):
    httpx_mock.add_response(
        url=f"{SEARCH_URL}?q=cat&per_page=20",
        json={"data": {"data": [ITEM]}},
    )

    client = KlipyClient(API_KEY)
    items = await client.search("cat")

    assert len(items) == 1
    assert items[0].id == "42"


async def test_search_falls_back_to_flat_gif_url(httpx_mock):
    item = {
        "id": "7",
        "title": "no hd",
        "file": {
            "xs": {"jpg": {"url": "https://cdn.klipy.com/thumb/7.jpg"}},
            "gif": {"url": "https://cdn.klipy.com/plain/7.gif"},
        },
    }
    httpx_mock.add_response(url=f"{SEARCH_URL}?q=cat&per_page=20", json={"data": [item]})

    client = KlipyClient(API_KEY)
    items = await client.search("cat")

    assert items[0].gif_url == "https://cdn.klipy.com/plain/7.gif"


async def test_search_extracts_preview_url_from_hd_jpg(httpx_mock):
    item = {
        "id": "42",
        "title": "cat jump",
        "file": {
            "xs": {"jpg": {"url": "https://cdn.klipy.com/thumb/42.jpg"}},
            "hd": {
                "gif": {"url": "https://cdn.klipy.com/hd/42.gif"},
                "jpg": {"url": "https://cdn.klipy.com/hd/42.jpg"},
            },
        },
    }
    httpx_mock.add_response(url=f"{SEARCH_URL}?q=cat&per_page=20", json={"data": [item]})

    client = KlipyClient(API_KEY)
    items = await client.search("cat")

    assert items[0].preview_url == "https://cdn.klipy.com/hd/42.jpg"


async def test_search_preview_url_falls_back_through_md_then_sm(httpx_mock):
    item_md = {
        "id": "1",
        "title": "md only",
        "file": {
            "xs": {"jpg": {"url": "https://cdn.klipy.com/thumb/1.jpg"}},
            "hd": {"gif": {"url": "https://cdn.klipy.com/hd/1.gif"}},
            "md": {"jpg": {"url": "https://cdn.klipy.com/md/1.jpg"}},
        },
    }
    httpx_mock.add_response(url=f"{SEARCH_URL}?q=cat&per_page=20", json={"data": [item_md]})
    items = await KlipyClient(API_KEY).search("cat")
    assert items[0].preview_url == "https://cdn.klipy.com/md/1.jpg"

    item_sm = {
        "id": "2",
        "title": "sm only",
        "file": {
            "xs": {"jpg": {"url": "https://cdn.klipy.com/thumb/2.jpg"}},
            "hd": {"gif": {"url": "https://cdn.klipy.com/hd/2.gif"}},
            "sm": {"jpg": {"url": "https://cdn.klipy.com/sm/2.jpg"}},
        },
    }
    httpx_mock.add_response(url=f"{SEARCH_URL}?q=cat&per_page=20", json={"data": [item_sm]})
    items = await KlipyClient(API_KEY).search("cat")
    assert items[0].preview_url == "https://cdn.klipy.com/sm/2.jpg"


async def test_search_preview_url_none_when_no_larger_jpg_available(httpx_mock):
    httpx_mock.add_response(url=f"{SEARCH_URL}?q=cat&per_page=20", json={"data": [ITEM]})

    client = KlipyClient(API_KEY)
    items = await client.search("cat")

    assert items[0].preview_url is None


async def test_search_skips_items_missing_required_urls(httpx_mock):
    broken = {"id": "9", "title": "broken", "file": {}}
    httpx_mock.add_response(
        url=f"{SEARCH_URL}?q=cat&per_page=20", json={"data": [broken, ITEM]}
    )

    client = KlipyClient(API_KEY)
    items = await client.search("cat")

    assert [item.id for item in items] == ["42"]


async def test_trending_returns_gif_items(httpx_mock):
    httpx_mock.add_response(url=f"{TRENDING_URL}?per_page=20", json={"data": [ITEM]})

    client = KlipyClient(API_KEY)
    items = await client.trending()

    assert len(items) == 1
    assert items[0].id == "42"


async def test_http_error_status_raises_klipy_http_error(httpx_mock):
    httpx_mock.add_response(url=f"{SEARCH_URL}?q=cat&per_page=20", status_code=401)

    client = KlipyClient(API_KEY)
    with pytest.raises(KlipyHTTPError) as excinfo:
        await client.search("cat")
    assert excinfo.value.status_code == 401


async def test_network_error_raises_klipy_network_error(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("boom"))

    client = KlipyClient(API_KEY)
    with pytest.raises(KlipyNetworkError):
        await client.search("cat")
