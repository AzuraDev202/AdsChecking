import json
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from adschecking.app import create_app
from adschecking.service import ConnectionError, Service, Settings, customer_id


@pytest.fixture
def settings(tmp_path):
    return SimpleNamespace(client_id='client', client_secret='secret',
        developer_token='developer', proxy='http://user:password@localhost:8080',
        admin_token='a' * 40, redirect='http://127.0.0.1:8000/oauth/callback',
        version='v25', cipher=Fernet(Fernet.generate_key()), path=tmp_path / 'token.enc')


def make_service(settings, handler):
    return Service(settings, httpx.Client(transport=httpx.MockTransport(handler)))


def test_oauth_binding_replay_and_encryption(settings):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={'refresh_token': 'private-refresh'})
    s = make_service(settings, handler)
    url, browser = s.start()
    params = parse_qs(urlsplit(url).query)
    assert params['code_challenge_method'] == ['S256']
    state = params['state'][0]
    for invalid_state, invalid_browser in [('wrong', browser), (state, 'wrong'), ('sai-phiên', browser)]:
        with pytest.raises(ConnectionError):
            s.callback(invalid_state, invalid_browser, 'code')
    assert not calls
    s.callback(state, browser, 'code')
    assert s.read()['refresh_token'] == 'private-refresh'
    assert b'private-refresh' not in settings.path.read_bytes()
    assert b'code_verifier=' in calls[0].content
    with pytest.raises(ConnectionError):
        s.callback(state, browser, 'code')
    assert len(calls) == 1


def test_expired_oauth(settings):
    s = make_service(settings, lambda r: pytest.fail('No request expected'))
    s.pending = ('state', 'verifier', 'browser', 0)
    with pytest.raises(ConnectionError):
        s.callback('state', 'browser', 'code')


def test_manager_and_paginated_clients(settings):
    def handler(request):
        if request.url.host == 'oauth2.googleapis.com':
            return httpx.Response(200, json={'access_token': 'access'})
        assert request.headers['login-customer-id'] == '1234567890'
        assert request.headers['developer-token'] == 'developer'
        body = json.loads(request.content)
        if 'FROM customer_client' not in body['query']:
            return httpx.Response(200, json={'results': [{'customer': {'id': '1234567890', 'manager': True}}]})
        if 'pageToken' not in body:
            return httpx.Response(200, json={'results': [{'customerClient': {'id': '1234567890'}}], 'nextPageToken': 'next'})
        assert body['pageToken'] == 'next'
        return httpx.Response(200, json={'results': [{'customerClient': {'id': '9876543210', 'currencyCode': 'VND', 'timeZone': 'Asia/Ho_Chi_Minh'}}]})
    s = make_service(settings, handler)
    s.save({'refresh_token': 'refresh'})
    s.connect_manager('123-456-7890')
    assert s.clients() == [{'id': '9876543210', 'currencyCode': 'VND', 'timeZone': 'Asia/Ho_Chi_Minh'}]
    s.disconnect()
    assert s.read() == {}


def test_reject_non_manager_preserves_selection(settings):
    s = make_service(settings, lambda r: httpx.Response(200, json=(
        {'access_token': 'access'} if r.url.host == 'oauth2.googleapis.com' else
        {'results': [{'customer': {'manager': False}}]})))
    s.save({'refresh_token': 'refresh', 'manager_id': '1111111111'})
    with pytest.raises(ConnectionError):
        s.connect_manager('1234567890')
    assert s.read()['manager_id'] == '1111111111'


def test_proxy_failure_redacted_no_retry(settings):
    calls = []
    def handler(request):
        calls.append(request)
        raise httpx.ProxyError('password private-refresh')
    s = make_service(settings, handler)
    with pytest.raises(ConnectionError) as error:
        s.request('GET', 'https://accounts.google.com')
    assert 'password' not in str(error.value)
    assert len(calls) == 1


def test_upstream_error_redacted(settings):
    s = make_service(settings, lambda r: httpx.Response(403, json={'error': 'private-refresh password'}))
    with pytest.raises(ConnectionError) as error:
        s.request('GET', 'https://googleads.googleapis.com')
    assert '403' in str(error.value)
    assert 'private-refresh' not in str(error.value)


def test_accessible_accounts_no_manager_header(settings):
    def handler(request):
        if request.url.host == 'oauth2.googleapis.com':
            return httpx.Response(200, json={'access_token': 'access'})
        assert 'login-customer-id' not in request.headers
        return httpx.Response(200, json={'resourceNames': ['customers/1234567890']})
    s = make_service(settings, handler)
    s.save({'refresh_token': 'refresh'})
    assert s.accessible() == ['customers/1234567890']


def test_production_transport_requires_proxy(settings, monkeypatch):
    captured = {}
    def client(**kwargs):
        captured.update(kwargs)
    monkeypatch.setattr(httpx, 'Client', client)
    Service(settings)
    assert captured['proxy'] == settings.proxy
    assert captured['trust_env'] is False
    assert captured['verify'] is True
    assert captured['follow_redirects'] is False


def test_http_auth_and_callback(settings):
    s = make_service(settings, lambda r: httpx.Response(200, json={'refresh_token': 'private-refresh'}))
    with TestClient(create_app(s)) as client:
        assert client.get('/connection').status_code in (401, 403)
        headers = {'Authorization': 'Bearer ' + settings.admin_token}
        response = client.post('/oauth/start', headers=headers)
        state = parse_qs(urlsplit(response.json()['authorization_url']).query)['state'][0]
        response = client.get('/oauth/callback', params={'state': state, 'code': 'code'})
        assert response.status_code == 200
        assert response.headers['Cache-Control'] == 'no-store'
        status = client.get('/connection', headers=headers)
        assert status.json()['oauth_connected'] is True
        assert 'private-refresh' not in status.text
        assert client.put('/manager', headers=headers, json={'customer_id': 'invalid'}).status_code == 422
        assert client.get('/health', headers={'host': 'evil.example'}).status_code == 400


@pytest.mark.parametrize('value', ['', '123', '1234567890 OR 1=1'])
def test_invalid_customer(value):
    with pytest.raises(ValueError):
        customer_id(value)


@pytest.mark.parametrize('proxy', ['', 'socks5://localhost:1080', 'http://localhost', 'http://localhost:80/path'])
def test_invalid_proxy(proxy, monkeypatch):
    for key in ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_ADS_DEVELOPER_TOKEN']:
        monkeypatch.setenv(key, 'test')
    monkeypatch.setenv('ADS_ADMIN_TOKEN', 'a' * 40)
    monkeypatch.setenv('ADS_PROXY_URL', proxy)
    with pytest.raises(ValueError):
        Settings()
