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
from .updates import APP_VERSION, check_update


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
        self.update_busy = False
        self.update_url = None
        self._progress_active = False
        self.results_loaded = False
        style = ttk.Style(self)
        style.theme_use('clam')
        background, surface, ink, muted, accent = '#f1f5f4', '#ffffff', '#202725', '#58625e', '#126c60'
        self.configure(background=background)
        style.configure('.', font=('Segoe UI', 10), background=background, foreground=ink)
        style.configure('TFrame', background=background)
        style.configure('TLabel', background=background)
        style.configure('Sheet.TFrame', background=surface)
        style.configure('Sheet.TLabel', background=surface)
        style.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'))
        style.configure('Section.TLabel', font=('Segoe UI', 11, 'bold'))
        style.configure('SheetTitle.TLabel', font=('Segoe UI', 14, 'bold'), background=surface)
        style.configure('Muted.TLabel', foreground=muted)
        style.configure('SheetMuted.TLabel', foreground=muted, background=surface)
        style.configure('State.TLabel', foreground=muted, padding=(10, 5), background='#e6ece9')
        style.configure('Ready.State.TLabel', foreground='#145b48', background='#e1eee7')
        style.configure('Working.State.TLabel', foreground='#7a5214', background='#f7edda')
        style.configure('TEntry', padding=(10, 7), fieldbackground=surface, bordercolor='#c6cfca',
                        lightcolor=surface, darkcolor=surface, insertcolor=ink)
        style.map('TEntry', bordercolor=[('focus', accent)],
                  fieldbackground=[('disabled', '#e9eeeb')], foreground=[('disabled', '#626d67')])
        style.configure('TCombobox', padding=(8, 7), fieldbackground=surface, bordercolor='#c6cfca')
        style.map('TCombobox', bordercolor=[('focus', accent)],
                  fieldbackground=[('disabled', '#f1f3f2')], foreground=[('disabled', '#626d67')])
        style.configure('TButton', padding=(12, 7), background=surface, foreground=ink,
                        bordercolor='#c6cfca', lightcolor=surface, darkcolor=surface, borderwidth=1)
        style.map('TButton', background=[('disabled', '#edf1ef'), ('pressed', '#dbe3de'), ('active', '#e5ece8')],
                  foreground=[('disabled', '#647168')], bordercolor=[('focus', accent)])
        style.configure('Primary.TButton', background=ink, foreground=surface, bordercolor=ink)
        style.map('Primary.TButton', background=[('disabled', '#e2e8e4'), ('pressed', '#101a15'), ('active', '#36473e')],
                  foreground=[('disabled', '#647168')], bordercolor=[('disabled', '#e2e8e4'), ('focus', accent)])
        style.configure('Quiet.TButton', background=background, bordercolor=background)
        style.configure('Treeview', rowheight=38, background=surface, fieldbackground=surface,
                        borderwidth=0, foreground=ink)
        style.configure('Treeview.Heading', font=('Segoe UI', 9), foreground=muted,
                        padding=(8, 10), background=surface, borderwidth=0, relief='flat')
        style.map('Treeview.Heading', background=[('active', '#f0f4f1')])
        style.map('Treeview', background=[('selected', '#e0ede6')], foreground=[('selected', '#154d39')])
        style.configure('Horizontal.TProgressbar', background=accent, troughcolor='#e2e8e4',
                        borderwidth=0, lightcolor=accent, darkcolor=accent, thickness=3)

        # At 1160px: 24 + 340 + 24 + 748 + 24 = 1160; results take surplus width.
        root = ttk.Frame(self, padding=24)
        root.pack(fill='both', expand=True)
        header = ttk.Frame(root)
        header.pack(fill='x', pady=(0, 20))
        title = ttk.Frame(header)
        title.pack(side='left')
        ttk.Label(title, text='AdsChecking', style='Title.TLabel').pack(anchor='w')
        ttk.Label(title, text='Không gian kết nối Google Ads', style='Muted.TLabel').pack(anchor='w', pady=(2, 0))
        self.connection_state = tk.StringVar(value='Chưa kết nối')
        self.state_badge = ttk.Label(header, textvariable=self.connection_state, style='State.TLabel')
        self.state_badge.pack(side='right')

        footer = ttk.Frame(root)
        footer.pack(side='bottom', fill='x', pady=(16, 0))
        progress_track = ttk.Frame(footer, height=4)
        progress_track.pack(fill='x')
        self.progress = ttk.Progressbar(progress_track, mode='determinate')
        self.progress.place(relwidth=1, relheight=1)
        status_row = ttk.Frame(footer)
        status_row.pack(fill='x', pady=(8, 4))
        self.status = tk.StringVar(value='Nhập proxy để bắt đầu kết nối Google Ads.')
        self.status_label = ttk.Label(status_row, textvariable=self.status, wraplength=790)
        self.status_label.pack(side='left', fill='x', expand=True)
        self.cancel_button = ttk.Button(status_row, text='Ngắt kết nối', style='Quiet.TButton', command=self.disconnect)
        self.cancel_button.pack(side='right', padx=(12, 0))
        updates = ttk.Frame(footer)
        updates.pack(fill='x')
        self.update_status = tk.StringVar(value=f'Phiên bản {APP_VERSION}')
        self.update_label = ttk.Label(updates, textvariable=self.update_status, style='Muted.TLabel', wraplength=650)
        self.update_label.pack(side='left', fill='x', expand=True)
        self.update_button = ttk.Button(updates, text='Kiểm tra cập nhật', style='Quiet.TButton', command=self.check_updates)
        self.update_button.pack(side='right')
        self.download_button = ttk.Button(updates, text='Tải bản mới', command=self.download_update)

        body = ttk.Frame(root)
        body.pack(fill='both', expand=True)
        body.columnconfigure(0, minsize=340)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        setup = ttk.Frame(body, width=340)
        setup.grid(row=0, column=0, sticky='nsew', padx=(0, 24))
        ttk.Label(setup, text='Thiết lập kết nối', style='Section.TLabel').pack(anchor='w')
        self.setup_hint = tk.StringVar(value='Xác minh proxy trước khi đăng nhập Google.')
        ttk.Label(setup, textvariable=self.setup_hint, style='Muted.TLabel', wraplength=330).pack(anchor='w', pady=(4, 16))
        ttk.Label(setup, text='Proxy HTTP / HTTPS').pack(anchor='w')
        self.proxy = tk.StringVar()
        self.proxy_entry = ttk.Entry(setup, textvariable=self.proxy, show='•', width=32)
        self.proxy_entry.pack(fill='x', pady=(6, 8))
        self.proxy_button = ttk.Button(setup, text='Kiểm tra proxy', style='Primary.TButton', command=self.check_proxy)
        self.proxy_button.pack(fill='x')
        ttk.Label(setup, text='http://user:password@host:port\nKhông chuyển sang mạng trực tiếp khi proxy lỗi.',
                  style='Muted.TLabel', wraplength=330).pack(anchor='w', pady=(8, 16))
        self.proxy.trace_add('write', self.proxy_changed)
        self.fields = []
        for label in ['OAuth Client ID', 'OAuth Client secret', 'Developer token']:
            ttk.Label(setup, text=label).pack(anchor='w', pady=(0, 6))
            entry = ttk.Entry(setup, width=32, show='' if label == 'OAuth Client ID' else '•')
            entry.pack(fill='x', pady=(0, 8))
            self.fields.append(entry)
        self.login_button = ttk.Button(setup, text='Đăng nhập Google', command=self.login)
        self.login_button.pack(fill='x', pady=(4, 0))
        ttk.Label(setup, text='Đăng nhập bằng trình duyệt hệ thống.\nCấu hình proxy trình duyệt riêng nếu cần.\nToken chỉ tồn tại trong phiên desktop.',
                  style='Muted.TLabel', wraplength=330).pack(anchor='w', pady=(8, 0))

        sheet = ttk.Frame(body, padding=20, style='Sheet.TFrame')
        sheet.grid(row=0, column=1, sticky='nsew')
        manager_heading = ttk.Frame(sheet, style='Sheet.TFrame')
        manager_heading.pack(fill='x')
        ttk.Label(manager_heading, text='Tài khoản quản lý', style='SheetTitle.TLabel').pack(side='left')
        self.accounts_button = ttk.Button(manager_heading, text='Tải tài khoản truy cập', command=self.accounts)
        self.accounts_button.pack(side='right')
        ttk.Label(sheet, text='Chọn tài khoản truy cập hoặc nhập ID MCC để xác minh.',
                  style='SheetMuted.TLabel').pack(anchor='w', pady=(8, 12))
        manager_row = ttk.Frame(sheet, style='Sheet.TFrame')
        manager_row.pack(fill='x')
        self.manager_value = tk.StringVar()
        self.manager = ttk.Combobox(manager_row, width=24, textvariable=self.manager_value)
        self.manager.pack(side='left', fill='x', expand=True)
        self.manager_button = ttk.Button(manager_row, text='Xác minh MCC', command=self.connect_manager)
        self.manager_button.pack(side='right', padx=(8, 0))
        ttk.Separator(sheet).pack(fill='x', pady=20)
        table_heading = ttk.Frame(sheet, style='Sheet.TFrame')
        table_heading.pack(fill='x')
        ttk.Label(table_heading, text='Cây tài khoản', style='SheetTitle.TLabel').pack(side='left')
        self.clients_button = ttk.Button(table_heading, text='Tải tài khoản con', command=self.clients)
        self.clients_button.pack(side='right')
        self.result_summary = tk.StringVar(value='Chưa tải dữ liệu tài khoản.')
        ttk.Label(sheet, textvariable=self.result_summary, style='SheetMuted.TLabel').pack(anchor='w', pady=(6, 16))
        columns = ('id', 'descriptiveName', 'status', 'manager', 'currencyCode', 'timeZone', 'level')
        table_frame = ttk.Frame(sheet, style='Sheet.TFrame')
        table_frame.pack(fill='both', expand=True)
        self.table = ttk.Treeview(table_frame, columns=columns, show='headings', height=4)
        widths = (122, 200, 110, 65, 72, 140, 48)
        for key, label, width in zip(columns,
                ['ID', 'Tên tài khoản', 'Trạng thái', 'MCC', 'Tiền tệ', 'Múi giờ', 'Cấp'], widths):
            anchor = 'e' if key == 'level' else 'w'
            self.table.heading(key, text=label, anchor=anchor)
            self.table.column(key, width=width, minwidth=width, anchor=anchor, stretch=key == 'descriptiveName')
        self.table.pack(side='left', fill='both', expand=True)
        vertical = ttk.Scrollbar(table_frame, orient='vertical', command=self.table.yview)
        vertical.pack(side='right', fill='y')
        self.table.configure(yscrollcommand=vertical.set)
        scroll = ttk.Scrollbar(sheet, orient='horizontal', command=self.table.xview)
        scroll.pack(fill='x', pady=(6, 0))
        self.table.configure(xscrollcommand=scroll.set)
        self.empty_panel = ttk.Frame(table_frame, style='Sheet.TFrame', padding=16)
        self.empty_title = tk.StringVar(value='Kết nối để xem tài khoản')
        self.empty_detail = tk.StringVar(value='Kiểm tra proxy, đăng nhập Google rồi xác minh MCC.\nDanh sách tài khoản con sẽ xuất hiện tại đây.')
        ttk.Label(self.empty_panel, textvariable=self.empty_title, style='SheetTitle.TLabel',
                  anchor='center').pack(fill='x')
        self.empty_description = ttk.Label(self.empty_panel, textvariable=self.empty_detail,
                  style='SheetMuted.TLabel', justify='center', anchor='center', wraplength=400)
        self.empty_description.pack(fill='x', pady=(8, 0))
        self.manager_value.trace_add('write', self.manager_changed)
        def resize(event):
            if event.widget is self:
                self.status_label.configure(wraplength=max(400, event.width - 240))
                self.update_label.configure(wraplength=max(350, event.width - 430))
            elif event.widget is table_frame:
                self.empty_description.configure(wraplength=max(200, event.width - 80))
        self.bind('<Configure>', resize)
        table_frame.bind('<Configure>', resize)

        self.protocol('WM_DELETE_WINDOW', self.close)
        self.refresh()
        self.proxy_entry.focus_set()
        self.after(100, self.poll)
        self.after(1500, self.check_updates)

    def check_updates(self):
        if self.update_busy:
            return
        self.update_busy = True
        self.update_button.configure(state='disabled')
        self.update_status.set(f'Phiên bản {APP_VERSION} · Đang kiểm tra cập nhật…')
        def worker():
            try:
                self.events.put(('update', check_update()))
            except Exception:
                self.events.put(('update_error', None))
        threading.Thread(target=worker, daemon=True).start()

    def finish_update(self, kind, value):
        self.update_busy = False
        self.update_button.configure(state='normal')
        if kind == 'update_error':
            self.update_status.set(f'Phiên bản {APP_VERSION} · Chưa kiểm tra được cập nhật. Hãy thử lại.')
        elif value:
            version, self.update_url = value
            self.update_status.set(f'Có bản mới {version} · Đang dùng {APP_VERSION}')
            self.download_button.pack(side='right', padx=8)
        else:
            self.update_status.set(f'Phiên bản {APP_VERSION} · Chưa có bản ổn định mới hơn.')
        if hasattr(self, 'update_timer'):
            self.after_cancel(self.update_timer)
        self.update_timer = self.after(3600000, self.check_updates)

    def download_update(self):
        if self.update_url:
            if webbrowser.open(self.update_url):
                messagebox.showinfo('Cập nhật AdsChecking',
                    'Tải ZIP, kiểm tra SHA-256 trên GitHub Releases, rồi đóng ứng dụng '
                    'và giải nén bản mới vào thư mục riêng. Mở AdsChecking.exe trong thư mục mới.')
            else:
                self.update_status.set('Không mở được trình duyệt. Hãy tải bản mới trên GitHub Releases.')

    def refresh(self):
        blocked = self.busy or self.oauth_waiting
        proxy_ok = bool(self.connection.proxy)
        self.connection_state.set('Đang xử lý…' if self.busy else 'Chờ đăng nhập Google' if self.oauth_waiting
                                  else 'MCC đã xác minh' if self.manager_ready else 'Google đã kết nối'
                                  if self.authenticated else 'Proxy đã xác minh' if proxy_ok else 'Chưa kết nối')
        self.state_badge.configure(style='Working.State.TLabel' if blocked else
                                   'Ready.State.TLabel' if proxy_ok else 'State.TLabel')
        if blocked != self._progress_active:
            self._progress_active = blocked
            if blocked:
                self.progress.configure(mode='indeterminate')
                self.progress.start(16)
            else:
                self.progress.stop()
                self.progress.configure(mode='determinate')
                self.progress['value'] = 0
        self.proxy_button.configure(style='TButton' if proxy_ok else 'Primary.TButton')
        self.login_button.configure(style='Primary.TButton' if proxy_ok and not self.authenticated else 'TButton')
        self.setup_hint.set('Đang chờ bạn hoàn tất đăng nhập trong trình duyệt.' if self.oauth_waiting else
                            'Google đã kết nối. Chọn và xác minh MCC ở bên phải.' if self.authenticated else
                            'Proxy đã sẵn sàng. Nhập thông tin ứng dụng Google.' if proxy_ok else
                            'Xác minh proxy trước khi đăng nhập Google.')
        if self.table.get_children():
            self.empty_panel.place_forget()
        else:
            self.empty_panel.place(relx=0.5, rely=0.56, relwidth=0.94, anchor='center')
            self.empty_title.set('Đang tải dữ liệu…' if self.busy else
                                 'Chưa có tài khoản con' if self.results_loaded else
                                 'Sẵn sàng tải cây tài khoản' if self.manager_ready else
                                 'Chọn tài khoản quản lý' if self.authenticated else
                                 'Kết nối để xem tài khoản')
            self.empty_detail.set('Dữ liệu sẽ hiển thị khi thao tác hoàn tất.' if self.busy else
                                  'MCC này chưa trả về tài khoản con. Bạn có thể tải lại.' if self.results_loaded else
                                  'Bấm Tải tài khoản con để đọc cây MCC đã xác minh.' if self.manager_ready else
                                  'Tải tài khoản truy cập hoặc nhập ID MCC, rồi bấm Xác minh MCC.' if self.authenticated else
                                  'Kiểm tra proxy, đăng nhập Google rồi xác minh MCC.\nDanh sách tài khoản con sẽ xuất hiện tại đây.')
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
        self.results_loaded = False
        self.result_summary.set('Chưa tải dữ liệu tài khoản.')
        self.manager.set('')
        self.manager.configure(values=())
        self.table.delete(*self.table.get_children())

    def manager_changed(self, *_):
        self.manager_ready = False
        self.results_loaded = False
        self.result_summary.set('Chưa tải dữ liệu tài khoản.')
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
                if kind in ('update', 'update_error'):
                    self.finish_update(kind, value)
                    continue
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
        self.results_loaded = False
        self.result_summary.set('Chưa tải dữ liệu tài khoản.')
        self.table.delete(*self.table.get_children())
        def done(_):
            self.manager_ready = True
            self.status.set('Đã xác minh MCC. Có thể tải danh sách tài khoản con.')
        self.run(lambda: self.connection.service.connect_manager(value), done)

    def clients(self):
        def done(rows):
            self.table.delete(*self.table.get_children())
            self.results_loaded = True
            for row in rows:
                self.table.insert('', 'end', values=[row.get(k, '—') for k in self.table['columns']])
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
            retained = []
            while True:
                event = self.events.get_nowait()
                if event[0] in ('update', 'update_error'):
                    retained.append(event)
        except queue.Empty:
            for event in retained:
                self.events.put(event)
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
        for timer in self.tk.call('after', 'info'):
            self.after_cancel(timer)
        self.destroy()


if __name__ == '__main__':
    Desktop().mainloop()
