"""Desktop connection tester. Run with python -m adschecking.desktop."""
import queue
import secrets
import tempfile
import threading
import tkinter as tk
import webbrowser
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tkinter import ttk, messagebox
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import httpx
from cryptography.fernet import Fernet

from .service import Service, ConnectionError


class DesktopConnection:
    def __init__(self):
        self.proxy = None
        self.service = None
        self.storage = tempfile.TemporaryDirectory(prefix='adschecking-')

    def reset(self):
        self.proxy = None
        if self.service:
            self.service.disconnect()
            self.service.client.close()
            self.service = None

    def check_proxy(self, value):
        self.reset()
        try:
            parsed = urlsplit(value)
            valid = (parsed.scheme in ('http', 'https') and parsed.hostname and parsed.port
                     and parsed.path in ('', '/') and not parsed.query and not parsed.fragment)
        except ValueError:
            valid = False
        if not valid:
            raise ConnectionError('Nhập proxy HTTP/HTTPS có host và port hợp lệ.')
        try:
            with httpx.Client(proxy=value, trust_env=False, verify=True,
                              timeout=20, follow_redirects=False) as client:
                response = client.get('https://accounts.google.com/.well-known/openid-configuration')
                response.raise_for_status()
                if response.json().get('issuer') != 'https://accounts.google.com':
                    raise ValueError()
        except (httpx.HTTPError, ValueError):
            raise ConnectionError('Kiểm tra proxy thất bại. Kiểm tra địa chỉ, xác thực và kết nối; không dùng kết nối trực tiếp.') from None
        self.proxy = value

    def configure(self, client_id, client_secret, developer_token):
        if not self.proxy:
            raise ConnectionError('Phải kiểm tra proxy thành công trước.')
        if not all(v.strip() for v in (client_id, client_secret, developer_token)):
            raise ConnectionError('Nhập đủ Client ID, Client secret và developer token.')
        if self.service:
            self.service.disconnect()
            self.service.client.close()
        settings = SimpleNamespace(proxy=self.proxy, client_id=client_id.strip(),
            client_secret=client_secret.strip(), developer_token=developer_token.strip(),
            redirect='http://127.0.0.1:8000/oauth/callback', version='v25',
            cipher=Fernet(Fernet.generate_key()), path=Path(self.storage.name) / 'session.enc')
        self.service = Service(settings)

    def close(self):
        self.reset()
        self.storage.cleanup()


class OAuthListener:
    """Loopback-only launch route binds the browser cookie before Google redirect."""
    def __init__(self, service, events):
        self.service = service
        self.events = events
        self.launch = secrets.token_urlsafe(32)
        self.url, self.cookie = service.start()
        listener = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass  # OAuth query strings must not enter logs.

            def do_GET(self):
                parsed = urlsplit(self.path)
                if parsed.path == '/launch/' + listener.launch and listener.launch:
                    listener.launch = ''
                    self.send_response(302)
                    self.send_header('Location', listener.url)
                    self.send_header('Set-Cookie', f'ads_oauth={listener.cookie}; HttpOnly; SameSite=Lax; Path=/oauth/callback; Max-Age=600')
                    self.send_header('Cache-Control', 'no-store')
                    self.end_headers()
                    return
                if parsed.path != '/oauth/callback':
                    self.send_error(404)
                    return
                params = parse_qs(parsed.query)
                try:
                    cookies = SimpleCookie(self.headers.get('Cookie', ''))
                    browser = cookies['ads_oauth'].value if 'ads_oauth' in cookies else ''
                    if 'error' in params or not params.get('code'):
                        raise ConnectionError('Bạn chưa cấp quyền Google Ads. Hãy thử đăng nhập lại.')
                    listener.service.callback(params.get('state', [''])[0], browser, params['code'][0])
                    text = 'Đã kết nối Google Ads. Bạn có thể quay lại ứng dụng.'
                    listener.events.put(('oauth_ok', text))
                except Exception:
                    text = 'Không hoàn tất đăng nhập. Quay lại ứng dụng và thử lại.'
                    listener.events.put(('oauth_error', text))
                body = text.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = HTTPServer(('127.0.0.1', 8000), Handler)
        self.server.timeout = 1
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def open(self):
        return webbrowser.open('http://127.0.0.1:8000/launch/' + self.launch)

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class Desktop(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('AdsChecking • Kiểm tra kết nối Google Ads')
        self.geometry('1160x820')
        self.minsize(1000, 780)
        self.connection = DesktopConnection()
        self.events = queue.Queue()
        self.listener = None
        self.busy = False
        self.authenticated = False
        self.oauth_waiting = False
        self.manager_ready = False
        style = ttk.Style(self)
        style.theme_use('clam')
        background, surface, ink, muted, accent = '#f3f6fa', '#ffffff', '#172b43', '#526479', '#126c60'
        self.configure(background=background)
        style.configure('.', font=('Segoe UI', 10), background=background, foreground=ink)
        style.configure('TLabel', background=background)
        style.configure('TFrame', background=background)
        style.configure('TLabelframe', background=surface, bordercolor='#d9e2ec', relief='solid')
        style.configure('TLabelframe.Label', font=('Segoe UI', 10, 'bold'), background=background, foreground=accent)
        style.configure('TEntry', padding=4, fieldbackground=surface)
        style.configure('TCombobox', padding=4)
        style.configure('TButton', padding=(12, 6), background='#e4ebf2', borderwidth=0)
        style.map('TButton', background=[('active', '#d2dee9')])
        style.configure('Primary.TButton', background=accent, foreground='white')
        style.map('Primary.TButton', background=[('disabled', '#e4ebf2'), ('active', '#0c554b')],
                  foreground=[('disabled', '#677687')])
        style.configure('Title.TLabel', font=('Segoe UI', 20, 'bold'))
        style.configure('Muted.TLabel', foreground=muted)
        style.configure('Badge.TLabel', foreground=accent, font=('Segoe UI', 10, 'bold'))
        style.configure('Treeview', rowheight=32, background=surface, fieldbackground=surface, borderwidth=0)
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'), padding=9, background='#e4ebf2')
        style.map('Treeview', background=[('selected', accent)], foreground=[('selected', 'white')])
        root = ttk.Frame(self, padding=16)
        root.pack(fill='both', expand=True)
        footer = ttk.Frame(root)
        footer.pack(side='bottom', fill='x')
        brand = ttk.Frame(root)
        brand.pack(fill='x', pady=(0, 4))
        ttk.Label(brand, text='ADS CHECKING / DESKTOP', style='Badge.TLabel').pack(side='left')
        self.connection_state = tk.StringVar(value='Chưa kết nối')
        ttk.Label(brand, textvariable=self.connection_state, style='Badge.TLabel').pack(side='right')
        ttk.Label(root, text='Kết nối Google Ads', style='Title.TLabel').pack(anchor='w')
        ttk.Label(root, text='Proxy → Đăng nhập Google → Chọn MCC → Kiểm tra tài khoản con').pack(anchor='w', pady=(4, 8))
        proxy_box = ttk.LabelFrame(root, text='1. Proxy bắt buộc — thực hiện trước tiên', padding=8)
        proxy_box.pack(fill='x')
        self.proxy = tk.StringVar()
        self.proxy_entry = ttk.Entry(proxy_box, textvariable=self.proxy, show='•', width=65)
        self.proxy_entry.pack(side='left', fill='x', expand=True)
        self.proxy_button = ttk.Button(proxy_box, text='Kiểm tra proxy', style='Primary.TButton', command=self.check_proxy)
        self.proxy_button.pack(side='left', padx=(10, 0))
        ttk.Label(root, text='Định dạng: http://user:password@host:port • HTTP/HTTPS • Không chuyển sang mạng trực tiếp').pack(anchor='w', pady=6)
        self.proxy.trace_add('write', self.proxy_changed)
        credentials = ttk.LabelFrame(root, text='2. Thông tin ứng dụng Google', padding=8)
        credentials.pack(fill='x', pady=8)
        self.fields = []
        for row, label in enumerate(['OAuth Client ID', 'OAuth Client secret', 'Developer token']):
            ttk.Label(credentials, text=label).grid(row=row, column=0, sticky='w', padx=(0, 12), pady=4)
            entry = ttk.Entry(credentials, width=70, show='•' if row else '')
            entry.grid(row=row, column=1, sticky='ew', pady=4)
            self.fields.append(entry)
        credentials.columnconfigure(1, weight=1)
        actions = ttk.Frame(root)
        actions.pack(fill='x', pady=8)
        self.login_button = ttk.Button(actions, text='Đăng nhập Google', style='Primary.TButton', command=self.login)
        self.login_button.pack(side='left')
        self.accounts_button = ttk.Button(actions, text='Tải tài khoản truy cập', command=self.accounts)
        self.accounts_button.pack(side='left', padx=8)
        self.cancel_button = ttk.Button(actions, text='Hủy / ngắt kết nối', command=self.disconnect)
        self.cancel_button.pack(side='left')
        manager = ttk.LabelFrame(root, text='3. Chọn hoặc nhập MCC', padding=8)
        manager.pack(fill='x', pady=8)
        self.manager_value = tk.StringVar()
        self.manager = ttk.Combobox(manager, width=35, textvariable=self.manager_value)
        self.manager.pack(side='left', fill='x', expand=True)
        self.manager_button = ttk.Button(manager, text='Xác minh MCC', command=self.connect_manager)
        self.manager_button.pack(side='left', padx=8)
        self.clients_button = ttk.Button(manager, text='Tải tài khoản con', command=self.clients)
        self.clients_button.pack(side='left')
        columns = ('id', 'descriptiveName', 'status', 'manager', 'currencyCode', 'timeZone', 'level')
        self.result_summary = tk.StringVar(value='Chưa có dữ liệu · Kết nối và xác minh MCC để tải tài khoản.')
        ttk.Label(root, textvariable=self.result_summary, style='Muted.TLabel').pack(anchor='w', pady=(8, 4))
        table_frame = ttk.Frame(root)
        table_frame.pack(fill='both', expand=True, pady=8)
        self.table = ttk.Treeview(table_frame, columns=columns, show='headings', height=3)
        for key, label in zip(columns, ['ID', 'Tên tài khoản', 'Trạng thái', 'MCC', 'Tiền tệ', 'Múi giờ', 'Cấp']):
            self.table.heading(key, text=label)
            self.table.column(key, width=130 if key != 'level' else 45)
        self.table.pack(side='left', fill='both', expand=True)
        vertical = ttk.Scrollbar(table_frame, orient='vertical', command=self.table.yview)
        vertical.pack(side='right', fill='y')
        self.table.configure(yscrollcommand=vertical.set)
        self.table.tag_configure('alternate', background='#f0f5f8')
        scroll = ttk.Scrollbar(root, orient='horizontal', command=self.table.xview)
        scroll.pack(fill='x')
        self.table.configure(xscrollcommand=scroll.set)
        self.manager_value.trace_add('write', self.manager_changed)
        self.status = tk.StringVar(value='Bắt đầu bằng cách nhập và kiểm tra proxy. Chưa kết nối Google.')
        self.progress = ttk.Progressbar(footer, mode='indeterminate')
        self.progress.pack(fill='x', pady=(8, 0))
        ttk.Label(footer, textvariable=self.status, wraplength=940).pack(anchor='w', pady=8)
        ttk.Label(footer, text='Đăng nhập mở trên trình duyệt hệ thống: cấu hình proxy trình duyệt riêng nếu cần.\nPhiên desktop không lưu thông tin đăng nhập lâu dài; đóng ứng dụng sẽ xóa token cục bộ.', wraplength=940, style='Muted.TLabel').pack(anchor='w')
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.refresh()
        self.proxy_entry.focus_set()
        self.after(100, self.poll)

    def refresh(self):
        blocked = self.busy or self.oauth_waiting
        proxy_ok = bool(self.connection.proxy)
        self.connection_state.set('Đang xử lý…' if self.busy else 'Chờ đăng nhập Google' if self.oauth_waiting
                                  else 'MCC đã xác minh' if self.manager_ready else 'Google đã kết nối'
                                  if self.authenticated else 'Proxy đã xác minh' if proxy_ok else 'Chưa kết nối')
        self.progress.stop()
        if blocked:
            self.progress.start(16)
        else:
            self.progress['value'] = 0
        if not self.table.get_children():
            self.result_summary.set('Chưa có dữ liệu · Kết nối và xác minh MCC để tải tài khoản.')
        for widget in (self.proxy_entry, self.proxy_button):
            widget.configure(state='disabled' if blocked else 'normal')
        for widget in self.fields:
            widget.configure(state='normal' if proxy_ok and not blocked else 'disabled')
        for widget, enabled in [(self.login_button, proxy_ok and not blocked),
                (self.accounts_button, self.authenticated and not blocked),
                (self.manager, self.authenticated and not blocked),
                (self.manager_button, self.authenticated and not blocked),
                (self.clients_button, self.manager_ready and not blocked),
                (self.cancel_button, not self.busy and bool(self.connection.service))]:
            widget.configure(state='normal' if enabled else 'disabled')

    def clear_accounts(self):
        self.authenticated = self.manager_ready = False
        self.manager.set('')
        self.manager.configure(values=())
        self.table.delete(*self.table.get_children())

    def manager_changed(self, *_):
        self.manager_ready = False
        self.table.delete(*self.table.get_children())
        self.refresh()

    def proxy_changed(self, *_):
        self.connection.reset()
        self.clear_accounts()
        self.status.set('Proxy đã thay đổi. Kiểm tra lại trước khi tiếp tục.')
        self.refresh()

    def run(self, task, success):
        self.busy = True
        self.status.set('Đang xử lý…')
        self.refresh()
        def worker():
            try:
                self.events.put(('done', (success, task())))
            except (ConnectionError, ValueError):
                self.events.put(('error', 'Thao tác thất bại. Kiểm tra proxy, thông tin Google và quyền truy cập.'))
            except Exception:
                self.events.put(('error', 'Không thực hiện được thao tác. Kiểm tra cấu hình hoặc thử lại.'))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'done':
                    self.busy = False
                    value[0](value[1])
                elif kind == 'error':
                    self.busy = False
                    self.status.set(value)
                elif kind in ('oauth_ok', 'oauth_error'):
                    self.oauth_waiting = False
                    self.authenticated = kind == 'oauth_ok'
                    self.status.set(value)
                    if self.listener:
                        self.listener.close()
                        self.listener = None
                self.refresh()
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def check_proxy(self):
        value = self.proxy.get().strip()
        self.clear_accounts()
        self.run(lambda: self.connection.check_proxy(value),
                 lambda _: self.status.set('Proxy đã kiểm tra thành công. Nhập thông tin Google để tiếp tục; quyền Ads chưa được xác minh.'))

    def login(self):
        try:
            self.connection.configure(*(entry.get() for entry in self.fields))
            self.clear_accounts()
            self.listener = OAuthListener(self.connection.service, self.events)
            self.oauth_waiting = True
            if not self.listener.open():
                self.disconnect()
                self.status.set('Không mở được trình duyệt hệ thống. Kiểm tra trình duyệt mặc định rồi thử lại.')
                return
            self.status.set('Hoàn tất đăng nhập trong trình duyệt. Có thể hủy để quay lại cấu hình.')
            self.after(600000, self.expire_oauth, self.listener)
        except (ConnectionError, OSError):
            if self.listener:
                self.listener.close()
                self.listener = None
            self.oauth_waiting = False
            self.status.set('Chưa mở được đăng nhập. Kiểm tra thông tin và bảo đảm cổng 8000 không được backend khác sử dụng.')
        self.refresh()

    def expire_oauth(self, listener):
        if self.oauth_waiting and self.listener is listener:
            self.disconnect()
            self.status.set('Phiên đăng nhập hết hạn. Bấm đăng nhập Google để thử lại.')

    def accounts(self):
        def done(rows):
            self.manager.configure(values=[r.split('/')[-1] for r in rows])
            self.status.set(f'Đã tải {len(rows)} tài khoản truy cập trực tiếp. Chọn hoặc nhập ID MCC.')
        self.run(self.connection.service.accessible, done)

    def connect_manager(self):
        value = self.manager.get()
        self.manager_ready = False
        self.table.delete(*self.table.get_children())
        def done(_):
            self.manager_ready = True
            self.status.set('Đã xác minh MCC. Có thể tải danh sách tài khoản con.')
        self.run(lambda: self.connection.service.connect_manager(value), done)

    def clients(self):
        def done(rows):
            self.table.delete(*self.table.get_children())
            for index, row in enumerate(rows):
                self.table.insert('', 'end', values=[row.get(k, '') for k in self.table['columns']],
                                  tags=('alternate',) if index % 2 else ())
            self.result_summary.set(f'{len(rows)} tài khoản · Cây tài khoản MCC')
            self.status.set(f'Đã tải {len(rows)} tài khoản trong cây MCC (có thể gồm MCC trung gian).')
        self.run(self.connection.service.clients, done)

    def disconnect(self):
        if self.listener:
            self.listener.close()
            self.listener = None
        self.oauth_waiting = False
        # Drop completion events from a callback that finished while cancelling.
        try:
            while True:
                self.events.get_nowait()
        except queue.Empty:
            pass
        if self.connection.service:
            self.connection.service.disconnect()
        self.clear_accounts()
        self.status.set('Đã ngắt phiên cục bộ. Quyền ứng dụng tại Google không bị thu hồi.')
        self.refresh()

    def close(self):
        if self.busy:
            messagebox.showinfo('Đang xử lý', 'Vui lòng đợi thao tác kết nối kết thúc trước khi đóng.')
            return
        if self.listener:
            self.listener.close()
        self.connection.close()
        self.destroy()


if __name__ == '__main__':
    Desktop().mainloop()
