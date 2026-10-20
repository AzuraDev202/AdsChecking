from contextlib import asynccontextmanager
import secrets

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .service import ConnectionError, Service, Settings


def create_app(service=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.service = service or Service(Settings())
        yield
        app.state.service.client.close()

    app = FastAPI(title='AdsChecking — Kết nối MCC và proxy', lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])
    bearer = HTTPBearer()

    def svc(request: Request):
        return request.app.state.service

    def authorized(credentials: HTTPAuthorizationCredentials = Depends(bearer), s=Depends(svc)):
        if not secrets.compare_digest(credentials.credentials.encode(), s.settings.admin_token.encode()):
            raise HTTPException(401, 'Không có quyền truy cập.')

    @app.middleware('http')
    async def privacy(request, call_next):
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.exception_handler(ConnectionError)
    async def connection_error(request, exc):
        return JSONResponse(status_code=400, content={'detail': str(exc)})

    @app.get('/health')
    def health():
        return {'status': 'ok'}

    @app.get('/connection', dependencies=[Depends(authorized)])
    def status(s=Depends(svc)):
        data = s.read()
        return {'oauth_connected': bool(data.get('refresh_token')), 'manager_id': data.get('manager_id'), 'proxy_required': True}

    @app.post('/oauth/start', dependencies=[Depends(authorized)])
    def start(response: Response, s=Depends(svc)):
        url, browser = s.start()
        response.set_cookie('ads_oauth', browser, httponly=True, samesite='lax', max_age=600, path='/oauth/callback')
        return {'authorization_url': url}

    @app.get('/oauth/callback', response_class=HTMLResponse)
    def callback(request: Request, state: str = '', code: str = '', error: str = '', s=Depends(svc)):
        if error or not code:
            raise HTTPException(400, 'Chưa được cấp quyền; hãy bắt đầu kết nối lại.')
        s.callback(state, request.cookies.get('ads_oauth', ''), code)
        response = HTMLResponse('<h1>Đã kết nối Google Ads</h1><p>Bạn có thể đóng tab này và chọn tài khoản quản lý.</p>')
        response.delete_cookie('ads_oauth', path='/oauth/callback')
        return response

    @app.get('/accounts', dependencies=[Depends(authorized)])
    def accounts(s=Depends(svc)):
        return {'accounts': s.accessible()}

    class Manager(BaseModel):
        customer_id: str

    @app.put('/manager', dependencies=[Depends(authorized)])
    def manager(body: Manager, s=Depends(svc)):
        try:
            return s.connect_manager(body.customer_id)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @app.get('/manager/clients', dependencies=[Depends(authorized)])
    def clients(s=Depends(svc)):
        return {'clients': s.clients()}

    @app.post('/proxy/check', dependencies=[Depends(authorized)])
    def proxy_check(s=Depends(svc)):
        # Fixed Google endpoint: no arbitrary URL probe / SSRF.
        result = s.request('GET', 'https://accounts.google.com/.well-known/openid-configuration')
        if result.get('issuer') != 'https://accounts.google.com':
            raise ConnectionError('Không xác minh được kết nối Google qua proxy.')
        return {'proxy_reachable': True, 'google_ads_access_verified': False}

    @app.delete('/connection', dependencies=[Depends(authorized)])
    def disconnect(s=Depends(svc)):
        s.disconnect()
        return {'disconnected_locally': True}

    return app
