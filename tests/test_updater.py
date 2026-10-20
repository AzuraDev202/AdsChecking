import hashlib
import io
import zipfile

import httpx
import pytest

from adschecking import updater


def archive(entries=None):
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as z:
        for path, value in (entries or {
            'AdsChecking/AdsChecking.exe': b'executable',
            'AdsChecking/VERSION.txt': b'0.3.0',
            'AdsChecking/_internal/runtime.dll': b'runtime',
        }).items():
            z.writestr(path, value)
    return data.getvalue()


def mock_download(monkeypatch, data, checksum=None):
    original = httpx.Client
    requests = []
    def handler(request):
        requests.append(str(request.url))
        assert 'authorization' not in request.headers
        if request.url.path.endswith('SHA256SUMS.txt'):
            return httpx.Response(200, text=(checksum or hashlib.sha256(data).hexdigest()) +
                                  '  AdsChecking-windows-x64.zip\n')
        return httpx.Response(200, content=data)
    def client(**kwargs):
        assert kwargs['trust_env'] is False
        return original(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(httpx, 'Client', client)
    return requests


def test_update_kinds():
    assert updater.update_kind('v0.2.1', '0.2.0') == 'patch'
    assert updater.update_kind('v0.3.0', '0.2.1') == 'feature'
    assert updater.update_kind('v1.0.0', '0.2.1') == 'feature'


def test_download_verify_and_stage(monkeypatch, tmp_path):
    seen = mock_download(monkeypatch, archive())
    staged = updater.prepare_update('v0.3.0', updater.release_zip('v0.3.0'), tmp_path)
    assert (staged / 'AdsChecking.exe').read_bytes() == b'executable'
    assert len(seen) == 2


def test_checksum_mismatch_does_not_stage(monkeypatch, tmp_path):
    mock_download(monkeypatch, archive(), '0' * 64)
    with pytest.raises(ValueError):
        updater.prepare_update('v0.3.0', updater.release_zip('v0.3.0'), tmp_path)
    assert not list(tmp_path.rglob('AdsChecking.exe'))


@pytest.mark.parametrize('path', ['../escape.exe', 'AdsChecking/../escape.exe',
    'AdsChecking/C:escape', '/AdsChecking/escape', 'AdsChecking/CON',
    'AdsChecking/hello:stream', 'AdsChecking/a.', 'AdsChecking/dir\\escape'])
def test_reject_unsafe_archive(monkeypatch, tmp_path, path):
    mock_download(monkeypatch, archive({path: b'bad'}))
    with pytest.raises(ValueError):
        updater.prepare_update('v0.3.0', updater.release_zip('v0.3.0'), tmp_path)


def test_reject_wrong_version(monkeypatch, tmp_path):
    mock_download(monkeypatch, archive({'AdsChecking/AdsChecking.exe': b'exe',
                                      'AdsChecking/VERSION.txt': b'0.2.0'}))
    with pytest.raises(ValueError):
        updater.prepare_update('v0.3.0', updater.release_zip('v0.3.0'), tmp_path)


def test_reject_external_download_before_request(monkeypatch, tmp_path):
    seen = mock_download(monkeypatch, archive())
    with pytest.raises(ValueError):
        updater.prepare_update('v0.3.0', 'https://example.com/app.zip', tmp_path)
    assert not seen


def test_redirect_to_untrusted_host_is_not_requested(monkeypatch, tmp_path):
    original = httpx.Client
    requests = []
    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(302, headers={'location': 'https://evil.example/payload'})
    monkeypatch.setattr(httpx, 'Client', lambda **kw: original(transport=httpx.MockTransport(handler)))
    with pytest.raises(ValueError):
        updater.prepare_update('v0.3.0', updater.release_zip('v0.3.0'), tmp_path)
    assert len(requests) == 1


def test_size_limit_cleans_incomplete_job(monkeypatch, tmp_path):
    mock_download(monkeypatch, archive())
    monkeypatch.setattr(updater, 'MAX_DOWNLOAD', 4)
    with pytest.raises(ValueError):
        updater.prepare_update('v0.3.0', updater.release_zip('v0.3.0'), tmp_path)
    assert not list(tmp_path.iterdir())
