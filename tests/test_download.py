"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

from datetime import date

import pytest
import requests

import ecallistolib.download as dl
from ecallistolib.download import RemoteFITS, download_files, list_remote_fits, list_remote_fits_range
from ecallistolib.exceptions import DownloadError


class _ListingResponse:
    def __init__(self, html: str):
        self.content = html.encode("utf-8")

    def raise_for_status(self) -> None:
        return None


class _StreamingResponse:
    def __init__(self, chunks: list[bytes]):
        self._chunks = chunks
        self.iter_content_called = False

    def raise_for_status(self) -> None:
        return None

    @property
    def content(self) -> bytes:
        raise AssertionError("download_files should stream content via iter_content")

    def iter_content(self, chunk_size: int):
        self.iter_content_called = True
        yield from self._chunks

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _Session:
    def __init__(self, response: _StreamingResponse):
        self._response = response
        self.calls: list[tuple[str, bool]] = []

    def get(self, url: str, timeout: float, stream: bool = False):
        self.calls.append((url, stream))
        return self._response

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_list_remote_fits_filters_by_hour_and_station(monkeypatch):
    html = """
    <html><body>
    <a href="ALASKA_20230601_120000_01.fit.gz">a</a>
    <a href="ALASKA_20230601_130000_01.fit.gz">b</a>
    <a href="GLASGOW_20230601_120000_01.fit.gz">c</a>
    </body></html>
    """

    def fake_get(url, timeout):
        return _ListingResponse(html)

    monkeypatch.setattr(dl.requests, "get", fake_get)

    out = list_remote_fits(
        day=date(2023, 6, 1),
        hour=12,
        station_substring="alaska",
        base_url="http://example.com",
    )

    assert len(out) == 1
    assert out[0].name == "ALASKA_20230601_120000_01.fit.gz"


def test_list_remote_fits_range_fetches_each_day_once(monkeypatch):
    html = """
    <html><body>
    <a href="ALASKA_20230601_120000_01.fit.gz">a</a>
    <a href="ALASKA_20230601_130000_01.fit.gz">b</a>
    <a href="ALASKA_20230601_140000_01.fit.gz">c</a>
    </body></html>
    """
    calls = {"count": 0}

    def fake_get(url, timeout):
        calls["count"] += 1
        return _ListingResponse(html)

    monkeypatch.setattr(dl.requests, "get", fake_get)

    out = list_remote_fits_range(
        start_date=date(2023, 6, 1),
        end_date=date(2023, 6, 1),
        hours=[12, 13, 14],
        station_substring="alaska",
        base_url="http://example.com",
    )

    assert calls["count"] == 1
    assert len(out) == 3


def test_list_remote_fits_range_error_policy_raise(monkeypatch):
    def fake_get(url, timeout):
        raise requests.exceptions.ConnectionError("boom")

    monkeypatch.setattr(dl.requests, "get", fake_get)

    with pytest.raises(DownloadError):
        list_remote_fits_range(
            start_date=date(2023, 6, 1),
            end_date=date(2023, 6, 1),
            hours=[12],
            station_substring="alaska",
            base_url="http://example.com",
            error_policy="raise",
        )


def test_list_remote_fits_range_error_policy_skip(monkeypatch):
    def fake_get(url, timeout):
        raise requests.exceptions.ConnectionError("boom")

    monkeypatch.setattr(dl.requests, "get", fake_get)

    out = list_remote_fits_range(
        start_date=date(2023, 6, 1),
        end_date=date(2023, 6, 1),
        hours=[12],
        station_substring="alaska",
        base_url="http://example.com",
        error_policy="skip",
    )

    assert out == []


def test_download_files_streams_content(monkeypatch, tmp_path):
    response = _StreamingResponse([b"abc", b"", b"def"])
    session = _Session(response)

    monkeypatch.setattr(dl.requests, "Session", lambda: session)

    items = [RemoteFITS(name="A.fit.gz", url="http://example.com/A.fit.gz")]
    out = download_files(items, out_dir=tmp_path, chunk_size=2)

    assert len(out) == 1
    assert out[0].read_bytes() == b"abcdef"
    assert response.iter_content_called
    assert session.calls[0][1] is True


def test_download_files_invalid_chunk_size(tmp_path):
    with pytest.raises(ValueError, match="chunk_size"):
        download_files([], out_dir=tmp_path, chunk_size=0)
