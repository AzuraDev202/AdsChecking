import httpx
import pytest
from adschecking import updates
from adschecking.desktop import Desktop


def release(tag='v0.2.0'):
    return {'tag_name': tag, 'assets': [{
        'name': 'AdsChecking-windows-x64.zip', 'state': 'uploaded', 'size': 123,
        'browser_download_url': updates.REPOSITORY + '/releases/download/' + tag + '/AdsChecking-windows-x64.zip'}]}


def mock_release(monkeypatch, data, status=200):
    original = httpx.Client
    def handler(request):
        assert str(request.url) == updates.RELEASE_API
        assert 'authorization' not in request.headers
        return httpx.Response(status, json=data)
    def client(**kwargs):
        assert kwargs['trust_env'] is False
        assert kwargs['timeout'] == 10
        return original(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(httpx, 'Client', client)


def test_new_release_pins_zip(monkeypatch):
    mock_release(monkeypatch, release())
    assert updates.check_update() == ('v0.2.0', release()['assets'][0]['browser_download_url'])


@pytest.mark.parametrize('tag', ['v0.1.0', 'v0.0.9'])
def test_no_upgrade(monkeypatch, tag):
    mock_release(monkeypatch, release(tag))
    assert updates.check_update() is None


@pytest.mark.parametrize('flag', ['draft', 'prerelease'])
def test_skip_unstable(monkeypatch, flag):
    data = release()
    data[flag] = True
    mock_release(monkeypatch, data)
    assert updates.check_update() is None


@pytest.mark.parametrize('url', ['https://evil.example/app.zip', updates.DOWNLOAD_URL])
def test_reject_unexpected_download(monkeypatch, url):
    data = release()
    data['assets'][0]['browser_download_url'] = url
    mock_release(monkeypatch, data)
    with pytest.raises(ValueError):
        updates.check_update()


def test_missing_zip(monkeypatch):
    data = release()
    data['assets'] = []
    mock_release(monkeypatch, data)
    with pytest.raises(ValueError):
        updates.check_update()


def test_no_release(monkeypatch):
    mock_release(monkeypatch, {}, 404)
    assert updates.check_update() is None


def test_rate_limit(monkeypatch):
    mock_release(monkeypatch, {}, 403)
    with pytest.raises(httpx.HTTPStatusError):
        updates.check_update()


def test_numeric_versions():
    assert updates.version_tuple('v0.10.0') > updates.version_tuple('v0.9.0')
    for tag in ['v1.0.0-beta', 'v1.0', '../1.0.0', 'v01.0.0']:
        with pytest.raises(ValueError):
            updates.version_tuple(tag)


def assert_update_banner_does_not_unlock_google(monkeypatch):
    app = Desktop()
    app.withdraw()
    try:
        app.finish_update('update', ('v0.2.0', updates.DOWNLOAD_URL))
        assert 'v0.2.0' in app.update_status.get()
        assert app.download_button.winfo_manager() == 'pack'
        assert str(app.login_button['state']) == 'disabled'
        app.events.put(('update_error', None))
        app.disconnect()
        app.poll()
        assert app.update_busy is False
        assert str(app.update_button['state']) == 'normal'
    finally:
        app.close()


def assert_background_check_and_download(monkeypatch):
    import time
    from adschecking import desktop
    monkeypatch.setattr(desktop, 'check_update', lambda: ('v0.2.0', updates.DOWNLOAD_URL))
    opened = []
    monkeypatch.setattr(desktop.webbrowser, 'open', lambda url: opened.append(url) or True)
    monkeypatch.setattr(desktop.messagebox, 'showinfo', lambda *args: None)
    app = Desktop()
    app.withdraw()
    try:
        app.check_updates()
        deadline = time.monotonic() + 3
        while app.update_busy and time.monotonic() < deadline:
            app.update()
            time.sleep(0.01)
        assert not app.update_busy
        app.download_update()
        assert opened == [updates.DOWNLOAD_URL]
    finally:
        app.close()


@pytest.mark.parametrize('scenario', [
    'assert_update_banner_does_not_unlock_google',
    'assert_background_check_and_download',
])
def test_desktop_update_in_isolated_tcl_process(scenario):
    # Separate Tcl interpreters in fresh processes, as with the packaged desktop.
    import subprocess
    import sys
    code = (
        "import runpy, pytest; "
        "scenarios = runpy.run_path('tests/test_updates.py'); "
        f"scenarios[{scenario!r}](pytest.MonkeyPatch())"
    )
    result = subprocess.run([sys.executable, '-c', code], capture_output=True,
                            text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
