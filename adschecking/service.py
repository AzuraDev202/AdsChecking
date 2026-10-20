"""Read-only Google Ads manager connection through a mandatory proxy."""
import base64
import hashlib
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import httpx
from cryptography.fernet import Fernet


class ConnectionError(Exception):
    pass


def customer_id(value: str) -> str:
    value = value.replace('-', '')
    if not re.fullmatch(r'[0-9]{10}', value):
        raise ValueError('ID tài khoản phải có 10 chữ số.')
    return value


class Settings:
    def __init__(self):
        self.client_id = os.environ['GOOGLE_CLIENT_ID']
        self.client_secret = os.environ['GOOGLE_CLIENT_SECRET']
        self.developer_token = os.environ['GOOGLE_ADS_DEVELOPER_TOKEN']
        if not all((self.client_id.strip(), self.client_secret.strip(), self.developer_token.strip())):
            raise ValueError('Thiếu cấu hình OAuth hoặc developer token.')
        self.proxy = os.environ['ADS_PROXY_URL']
        self.admin_token = os.environ['ADS_ADMIN_TOKEN']
        if len(self.admin_token) < 32:
            raise ValueError('ADS_ADMIN_TOKEN cần ít nhất 32 ký tự.')
        parsed = urlsplit(self.proxy)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                or not parsed.port or parsed.path not in ('', '/')
                or parsed.query or parsed.fragment):
            raise ValueError('Proxy cần URL HTTP/HTTPS có hostname và port.')
        self.redirect = 'http://127.0.0.1:8000/oauth/callback'
        self.version = os.environ.get('GOOGLE_ADS_API_VERSION', 'v25')
        if not re.fullmatch(r'v\d+', self.version):
            raise ValueError('Phiên bản API không hợp lệ.')
        self.cipher = Fernet(os.environ['ADS_ENCRYPTION_KEY'].encode())
        self.path = Path(os.environ.get('ADS_TOKEN_FILE', 'data/connection.enc'))


class Service:
    def __init__(self, settings, client=None):
        self.settings = settings
        self.client = client or httpx.Client(
            proxy=settings.proxy, trust_env=False, verify=True,
            timeout=30, follow_redirects=False,
        )
        self.lock = threading.RLock()
        self.pending = None

    def request(self, method, url, **kwargs):
        try:
            response = self.client.request(method, url, **kwargs)
        except httpx.HTTPError:
            raise ConnectionError('Không thể kết nối qua proxy; không chuyển sang kết nối trực tiếp.') from None
        if not response.is_success:
            # Never expose upstream payloads, URLs, tokens or proxy credentials.
            raise ConnectionError(f'Dịch vụ Google trả HTTP {response.status_code}; kiểm tra quyền, token và cấu hình.')
        try:
            return response.json()
        except ValueError:
            raise ConnectionError('Google trả dữ liệu không hợp lệ.') from None

    def read(self):
        if not self.settings.path.exists():
            return {}
        try:
            return json.loads(self.settings.cipher.decrypt(self.settings.path.read_bytes()))
        except Exception:
            raise ConnectionError('Không đọc được dữ liệu kết nối đã mã hóa.') from None

    def save(self, data):
        path = self.settings.path
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        temp.write_bytes(self.settings.cipher.encrypt(json.dumps(data).encode()))
        temp.replace(path)

    def start(self):
        with self.lock:
            state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
            browser = secrets.token_urlsafe(32)
            self.pending = (state, verifier, browser, time.monotonic() + 600)
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
            query = urlencode(dict(client_id=self.settings.client_id,
                redirect_uri=self.settings.redirect, response_type='code',
                scope='https://www.googleapis.com/auth/adwords', access_type='offline',
                prompt='consent', state=state, code_challenge=challenge,
                code_challenge_method='S256'))
            return 'https://accounts.google.com/o/oauth2/v2/auth?' + query, browser

    def callback(self, state, browser, code):
        with self.lock:
            pending = self.pending
            if (not pending or pending[3] < time.monotonic()
                    or not secrets.compare_digest(state.encode(), pending[0].encode())
                    or not secrets.compare_digest(browser.encode(), pending[2].encode())):
                raise ConnectionError('Phiên OAuth không hợp lệ hoặc đã hết hạn.')
            self.pending = None  # single use, even if exchange fails
            token = self.request('POST', 'https://oauth2.googleapis.com/token', data=dict(
                client_id=self.settings.client_id, client_secret=self.settings.client_secret,
                redirect_uri=self.settings.redirect, grant_type='authorization_code',
                code=code, code_verifier=pending[1]))
            if not token.get('refresh_token'):
                raise ConnectionError('Google chưa cấp refresh token; vui lòng kết nối lại và cấp quyền.')
            self.save({'refresh_token': token['refresh_token']})

    def headers(self):
        data = self.read()
        if not data.get('refresh_token'):
            raise ConnectionError('Chưa kết nối OAuth Google Ads.')
        token = self.request('POST', 'https://oauth2.googleapis.com/token', data=dict(
            client_id=self.settings.client_id, client_secret=self.settings.client_secret,
            refresh_token=data['refresh_token'], grant_type='refresh_token'))
        if not token.get('access_token'):
            raise ConnectionError('Google không trả access token.')
        return {'Authorization': 'Bearer ' + token['access_token'],
                'developer-token': self.settings.developer_token}

    @property
    def base(self):
        return f'https://googleads.googleapis.com/{self.settings.version}'

    def accessible(self):
        return self.request('GET', self.base + '/customers:listAccessibleCustomers', headers=self.headers()).get('resourceNames', [])

    def search(self, manager, query, headers):
        headers = {**headers, 'login-customer-id': manager}
        rows, page = [], None
        while True:
            body = {'query': query}
            if page:
                body['pageToken'] = page
            result = self.request('POST', f'{self.base}/customers/{manager}/googleAds:search', headers=headers, json=body)
            rows.extend(result.get('results', []))
            page = result.get('nextPageToken')
            if not page:
                return rows

    def connect_manager(self, manager):
        manager = customer_id(manager)
        with self.lock:
            rows = self.search(manager, 'SELECT customer.id, customer.descriptive_name, customer.manager FROM customer', self.headers())
            if len(rows) != 1 or not rows[0].get('customer', {}).get('manager'):
                raise ConnectionError('Tài khoản được chọn không phải tài khoản quản lý MCC.')
            data = self.read()
            data['manager_id'] = manager
            self.save(data)
            return rows[0]['customer']

    def clients(self):
        with self.lock:
            manager = self.read().get('manager_id')
            if not manager:
                raise ConnectionError('Chưa chọn tài khoản quản lý.')
            rows = self.search(manager, 'SELECT customer_client.id, customer_client.descriptive_name, customer_client.manager, customer_client.level, customer_client.currency_code, customer_client.time_zone, customer_client.status FROM customer_client', self.headers())
            return [r['customerClient'] for r in rows if str(r['customerClient']['id']) != manager]

    def disconnect(self):
        with self.lock:
            self.pending = None
            self.settings.path.unlink(missing_ok=True)
