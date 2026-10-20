import httpx
import pytest
from adschecking.desktop import DesktopConnection, Desktop
from adschecking.service import ConnectionError


def test_loopback_oauth_launch_and_callback(monkeypatch):
    import queue
    from urllib.parse import parse_qs, urlsplit
    from adschecking.desktop import OAuthListener
    c = DesktopConnection()
    c.proxy = 'http://localhost:8080'
    c.configure('id', 'secret', 'developer')
    c.service.client.close()
    c.service.client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, json={'refresh_token': 'private-token'})))
    events = queue.Queue()
    listener = OAuthListener(c.service, events)
    try:
        with httpx.Client(trust_env=False) as browser:
            launch = browser.get('http://127.0.0.1:8000/launch/' + listener.launch)
            assert launch.status_code == 302
            state = parse_qs(urlsplit(launch.headers['location']).query)['state'][0]
            result = browser.get('http://127.0.0.1:8000/oauth/callback', params={'state': state, 'code': 'code'})
            assert result.status_code == 200
            assert events.get(timeout=2)[0] == 'oauth_ok'
            assert c.service.read()['refresh_token'] == 'private-token'
    finally:
        listener.close()
        c.close()


def test_proxy_gate_and_reset(monkeypatch):
    c = DesktopConnection()
    with pytest.raises(ConnectionError):
        c.configure('id', 'secret', 'dev')
    original = httpx.Client
    seen = []
    def client(**kwargs):
        seen.append(kwargs)
        return original(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={'issuer': 'https://accounts.google.com'})))
    monkeypatch.setattr(httpx, 'Client', client)
    c.check_proxy('http://localhost:8080')
    assert seen[0]['trust_env'] is False and seen[0]['verify'] is True
    c.configure('id', 'secret', 'dev')
    c.service.save({'refresh_token': 'secret'})
    c.reset()
    assert c.proxy is None and c.service is None
    c.close()


def test_proxy_failure_never_unlocks(monkeypatch):
    c = DesktopConnection()
    original = httpx.Client
    def handler(request):
        raise httpx.ProxyError('private-password')
    monkeypatch.setattr(httpx, 'Client', lambda **kw: original(transport=httpx.MockTransport(handler)))
    with pytest.raises(ConnectionError) as exc:
        c.check_proxy('http://localhost:8080')
    assert 'private-password' not in str(exc.value)
    assert c.proxy is None
    c.close()


def test_desktop_initial_gate_and_proxy_edit():
    app = Desktop()
    app.withdraw()
    try:
        assert str(app.proxy_button['state']) == 'normal'
        assert str(app.login_button['state']) == 'disabled'
        assert str(app.manager_button['state']) == 'disabled'
        assert str(app.fields[0]['state']) == 'disabled'
        app.connection.proxy = 'http://localhost:8080'
        app.refresh()
        assert str(app.login_button['state']) == 'normal'
        app.authenticated = app.manager_ready = True
        app.manager_value.set('1234567890')
        assert app.manager_ready is False
        assert str(app.clients_button['state']) == 'disabled'
        app.proxy.set('http://localhost:9090')
        assert app.connection.proxy is None
        assert str(app.login_button['state']) == 'disabled'
    finally:
        app.close()


def test_desktop_minimum_layout_keeps_table_and_status_visible():
    app = Desktop()
    try:
        app.geometry('1000x780')
        app.update()
        assert app.progress.winfo_ismapped()
        assert app.table.winfo_height() >= 80
        assert app.progress.winfo_rooty() + app.progress.winfo_height() < app.winfo_rooty() + app.winfo_height()
    finally:
        app.close()
