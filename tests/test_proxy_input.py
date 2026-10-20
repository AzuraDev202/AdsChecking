import httpx
import pytest

from adschecking.desktop import DesktopConnection, normalize_proxy
from adschecking.service import ConnectionError


@pytest.mark.parametrize('value, expected', [
    ('proxy.example:8080:alice:secret', 'http://alice:secret@proxy.example:8080'),
    ('127.0.0.1:3128:user:p@ss:word/#?%', 'http://user:p%40ss%3Aword%2F%23%3F%25@127.0.0.1:3128'),
    ('host:8080:user:https://password', 'http://user:https%3A%2F%2Fpassword@host:8080'),
    ('[2001:db8::1]:8080:user:secret', 'http://user:secret@[2001:db8::1]:8080'),
    ('https://user:secret@proxy.example:8443', 'https://user:secret@proxy.example:8443'),
])
def test_normalize_proxy(value, expected):
    assert normalize_proxy(value) == expected


@pytest.mark.parametrize('value', ['host:abc:user:secret', 'host:0:user:secret',
    'host:65536:user:secret', 'host:8080:user', 'host:8080::secret',
    'host:8080:user:', 'host/path:8080:user:secret', 'host@evil:8080:user:secret',
    'socks5://host:8080', '[bad]:8080:user:secret', 'host:8080:user:pass\nword'])
def test_invalid_input_does_not_expose_credentials(value):
    with pytest.raises(ConnectionError) as exc:
        normalize_proxy(value)
    assert 'secret' not in str(exc.value)


def test_short_form_is_used_by_google_transport(monkeypatch):
    original = httpx.Client
    seen = []
    def factory(**kwargs):
        seen.append(kwargs)
        return original(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={
            'issuer': 'https://accounts.google.com', 'ip': '203.0.113.5'})))
    monkeypatch.setattr(httpx, 'Client', factory)
    connection = DesktopConnection()
    try:
        connection.check_proxy('proxy.example:8080:alice:p@ss:word')
        assert seen[0]['proxy'] == 'http://alice:p%40ss%3Aword@proxy.example:8080'
        assert connection.proxy == seen[0]['proxy']
        assert connection.exit_ip == '203.0.113.5'
    finally:
        connection.close()
