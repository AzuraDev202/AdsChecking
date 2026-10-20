import httpx
import pytest
from adschecking.desktop import DesktopConnection, Desktop
from adschecking.service import ConnectionError


@pytest.mark.parametrize('ip', ['203.0.113.7', '2001:db8::7'])
def test_proxy_exit_ip_and_reset(monkeypatch, ip):
    original = httpx.Client
    seen = []
    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, json={'ip': ip} if request.url.host == 'api64.ipify.org'
                              else {'issuer': 'https://accounts.google.com'})
    def client(**kwargs):
        assert kwargs['proxy'] == 'http://localhost:8080'
        assert kwargs['trust_env'] is False and kwargs['verify'] is True
        return original(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(httpx, 'Client', client)
    c = DesktopConnection()
    try:
        c.check_proxy('http://localhost:8080')
        assert c.exit_ip == ip and c.ip_checked_at is not None
        assert seen == ['https://accounts.google.com/.well-known/openid-configuration',
                        'https://api64.ipify.org?format=json']
        c.reset()
        assert c.exit_ip is None and c.ip_checked_at is None
    finally:
        c.close()


@pytest.mark.parametrize('result', ['invalid', None])
def test_exit_ip_failure_does_not_undo_google_proxy_check(monkeypatch, result):
    original = httpx.Client
    def handler(request):
        if request.url.host == 'api64.ipify.org':
            if result is None:
                raise httpx.ConnectError('private-proxy-password')
            return httpx.Response(200, json={'ip': result})
        return httpx.Response(200, json={'issuer': 'https://accounts.google.com'})
    monkeypatch.setattr(httpx, 'Client', lambda **kw: original(transport=httpx.MockTransport(handler)))
    c = DesktopConnection()
    try:
        c.check_proxy('http://localhost:8080')
        assert c.proxy == 'http://localhost:8080'
        assert c.exit_ip is None and c.ip_checked_at is None
    finally:
        c.close()


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
        from datetime import datetime
        app.connection.exit_ip = '203.0.113.7'
        app.connection.ip_checked_at = datetime.now().astimezone()
        app.refresh()
        assert '203.0.113.7' in app.proxy_ip.get()
        assert str(app.login_button['state']) == 'normal'
        app.authenticated = app.manager_ready = True
        app.manager_value.set('1234567890')
        assert app.manager_ready is False
        assert str(app.clients_button['state']) == 'disabled'
        app.proxy.set('http://localhost:9090')
        assert app.connection.proxy is None
        assert '203.0.113.7' not in app.proxy_ip.get()
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
