from unittest.mock import MagicMock

import pytest
import requests

from korrector.krakoa import Krakoa, Series


def test_series_from_json() -> None:
    data = {
        "id": "123",
        "name": "Test Series",
        "metadata": {"title": "Test Title", "titleLock": True},
        "booksMetadata": {"releaseDate": "2020-01-01"},
        "oneshot": False,
    }
    s = Series.from_json(data)
    assert s.id == "123"
    assert s.name == "Test Series"
    assert s.title == "Test Title"
    assert s.release_date == "2020-01-01"
    assert s.oneshot is False
    assert s.title_lock is True


def test_make_request_get(monkeypatch: pytest.MonkeyPatch) -> None:
    k = Krakoa(api_key="key", api_base_url="http://test")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"foo": "bar"}
    mock_resp.raise_for_status.return_value = None
    monkeypatch.setattr("requests.get", lambda *a, **kw: mock_resp)
    result = k.make_request("GET", "http://test", {}, None)
    assert result == {"foo": "bar"}


def test_make_request_post(monkeypatch: pytest.MonkeyPatch) -> None:
    k = Krakoa(api_key="key", api_base_url="http://test")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"foo": "bar"}
    mock_resp.raise_for_status.return_value = None
    monkeypatch.setattr("requests.post", lambda *a, **kw: mock_resp)
    result = k.make_request("POST", "http://test", {}, {"data": 1})
    assert result == {"foo": "bar"}


def test_make_request_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    k = Krakoa(api_key="key", api_base_url="http://test")

    def raise_timeout(*a, **kw):
        raise requests.Timeout()

    monkeypatch.setattr("requests.get", raise_timeout)
    result = k.make_request("GET", "http://test", {}, None)
    assert result is None


def test_get_all_series() -> None:
    k = Krakoa(api_key="key", api_base_url="http://test")
    # Mock make_request to return two pages
    responses = [
        {
            "content": [
                {
                    "id": "1",
                    "name": "A",
                    "metadata": {"title": "A", "titleLock": False},
                    "booksMetadata": {"releaseDate": "2020-01-01"},
                    "oneshot": False,
                },
            ],
            "last": False,
        },
        {
            "content": [
                {
                    "id": "2",
                    "name": "B",
                    "metadata": {"title": "B", "titleLock": True},
                    "booksMetadata": {"releaseDate": "2021-01-01"},
                    "oneshot": True,
                },
            ],
            "last": True,
        },
    ]

    def fake_make_request(*a, **kw):
        return responses.pop(0)

    k.make_request = fake_make_request
    result = list(k.get_all_series())
    assert len(result) == 2
    assert result[0].id == "1"
    assert result[1].id == "2"


def test_make_korrection() -> None:
    k = Krakoa(api_key="key", api_base_url="http://test")
    called = {}

    def fake_make_request(method, url, headers, data):
        called["method"] = method
        called["url"] = url
        called["headers"] = headers
        called["data"] = data
        return {"result": "ok"}

    k.make_request = fake_make_request
    k._generate_sort_title = lambda t: t + "_sort"
    k.make_korrection("series123", "New Title")
    assert called["method"] == "POST"
    assert called["url"].endswith("/series/series123/metadata")
    assert called["data"]["title"] == "New Title"
    assert called["data"]["sortTitle"] == "New Title_sort"
    assert called["data"]["titleLock"] is True
    assert called["data"]["sortTitleLock"] is True
