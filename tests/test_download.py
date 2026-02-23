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
    def __init__(self, chunks: list[bytes], http_error: requests.exceptions.HTTPError | None = None):
        self._chunks = chunks
        self._http_error = http_error
        self.iter_content_called = False

    def raise_for_status(self) -> None:
        if self._http_error is not None:
            raise self._http_error
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
    def __init__(self, responses: list[object]):
        self._responses = list(responses)
        self.calls: list[tuple[str, bool]] = []

    def get(self, url: str, timeout: float, stream: bool = False):
        self.calls.append((url, stream))
        if not self._responses:
            raise AssertionError("No response configured")
        next_item = self._responses.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return next_item

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
    session = _Session([response])

    monkeypatch.setattr(dl.requests, "Session", lambda: session)

    items = [RemoteFITS(name="A.fit.gz", url="http://example.com/A.fit.gz")]
    out = download_files(items, out_dir=tmp_path, chunk_size=2)

    assert len(out) == 1
    assert out[0].read_bytes() == b"abcdef"
    assert response.iter_content_called
    assert session.calls[0][1] is True


def test_download_files_overwrite_skip(monkeypatch, tmp_path):
    existing = tmp_path / "A.fit.gz"
    existing.write_bytes(b"existing")

    session = _Session([])
    monkeypatch.setattr(dl.requests, "Session", lambda: session)

    items = [RemoteFITS(name="A.fit.gz", url="http://example.com/A.fit.gz")]
    out = download_files(items, out_dir=tmp_path, overwrite="skip")

    assert out == [existing]
    assert existing.read_bytes() == b"existing"
    assert session.calls == []


def test_download_files_overwrite_error(monkeypatch, tmp_path):
    existing = tmp_path / "A.fit.gz"
    existing.write_bytes(b"existing")

    session = _Session([])
    monkeypatch.setattr(dl.requests, "Session", lambda: session)

    items = [RemoteFITS(name="A.fit.gz", url="http://example.com/A.fit.gz")]
    with pytest.raises(DownloadError, match="already exists"):
        download_files(items, out_dir=tmp_path, overwrite="error")


def test_download_files_retries_then_success(monkeypatch, tmp_path):
    session = _Session([requests.exceptions.Timeout("boom"), _StreamingResponse([b"ok"])])
    monkeypatch.setattr(dl.requests, "Session", lambda: session)
    monkeypatch.setattr(dl.time, "sleep", lambda _: None)

    items = [RemoteFITS(name="A.fit.gz", url="http://example.com/A.fit.gz")]
    out = download_files(items, out_dir=tmp_path, retries=1, retry_backoff_s=0.01)

    assert len(out) == 1
    assert out[0].read_bytes() == b"ok"
    assert len(session.calls) == 2


def test_download_files_retries_exhausted(monkeypatch, tmp_path):
    session = _Session(
        [
            requests.exceptions.ConnectionError("boom1"),
            requests.exceptions.ConnectionError("boom2"),
            requests.exceptions.ConnectionError("boom3"),
        ]
    )
    monkeypatch.setattr(dl.requests, "Session", lambda: session)
    monkeypatch.setattr(dl.time, "sleep", lambda _: None)

    items = [RemoteFITS(name="A.fit.gz", url="http://example.com/A.fit.gz")]
    with pytest.raises(DownloadError, match="Failed to download"):
        download_files(items, out_dir=tmp_path, retries=2, retry_backoff_s=0.01)
    assert len(session.calls) == 3


def test_download_files_retries_http_503_then_success(monkeypatch, tmp_path):
    response = requests.Response()
    response.status_code = 503
    http_error = requests.exceptions.HTTPError("server unavailable")
    http_error.response = response

    session = _Session([_StreamingResponse([], http_error=http_error), _StreamingResponse([b"ok"])])
    monkeypatch.setattr(dl.requests, "Session", lambda: session)
    monkeypatch.setattr(dl.time, "sleep", lambda _: None)

    items = [RemoteFITS(name="A.fit.gz", url="http://example.com/A.fit.gz")]
    out = download_files(items, out_dir=tmp_path, retries=1)

    assert len(out) == 1
    assert out[0].read_bytes() == b"ok"
    assert len(session.calls) == 2


def test_download_files_parallel_workers_preserve_order(monkeypatch, tmp_path):
    class _ParallelSession:
        def __init__(self):
            self.calls: list[str] = []

        def get(self, url: str, timeout: float, stream: bool = False):
            self.calls.append(url)
            name = url.rsplit("/", 1)[-1]
            return _StreamingResponse([name.encode("utf-8")])

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    sessions: list[_ParallelSession] = []

    def session_factory():
        s = _ParallelSession()
        sessions.append(s)
        return s

    monkeypatch.setattr(dl.requests, "Session", session_factory)

    items = [
        RemoteFITS(name="A.fit.gz", url="http://example.com/A.fit.gz"),
        RemoteFITS(name="B.fit.gz", url="http://example.com/B.fit.gz"),
        RemoteFITS(name="C.fit.gz", url="http://example.com/C.fit.gz"),
    ]
    out = download_files(items, out_dir=tmp_path, workers=3)

    assert [p.name for p in out] == ["A.fit.gz", "B.fit.gz", "C.fit.gz"]
    assert out[0].read_bytes() == b"A.fit.gz"
    assert out[1].read_bytes() == b"B.fit.gz"
    assert out[2].read_bytes() == b"C.fit.gz"
    assert len(sessions) == 3


def test_download_files_invalid_chunk_size(tmp_path):
    with pytest.raises(ValueError, match="chunk_size"):
        download_files([], out_dir=tmp_path, chunk_size=0)


def test_download_files_invalid_workers(tmp_path):
    with pytest.raises(ValueError, match="workers"):
        download_files([], out_dir=tmp_path, workers=0)


def test_download_files_invalid_retries(tmp_path):
    with pytest.raises(ValueError, match="retries"):
        download_files([], out_dir=tmp_path, retries=-1)


def test_download_files_invalid_retry_backoff(tmp_path):
    with pytest.raises(ValueError, match="retry_backoff_s"):
        download_files([], out_dir=tmp_path, retry_backoff_s=-0.1)


def test_download_files_invalid_overwrite(tmp_path):
    with pytest.raises(ValueError, match="overwrite"):
        download_files([], out_dir=tmp_path, overwrite="invalid")  # type: ignore[arg-type]
