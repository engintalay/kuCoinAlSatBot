"""
KuCoin Al-Sat Botu — FastAPI Uygulama Giriş Noktası
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import asyncio
import json
import os

from src.utils.logger import logger, log_api_request

from src.modules.module1_account import KuCoinAccount
from src.modules.module2_market import KuCoinMarket
from src.modules.module3_orders import KuCoinOrders
from src.modules.settings import SettingsManager
from src.modules.recommendations import RecommendationEngine
from src.modules.market_regime import MarketRegime
from src.modules.bug_reports import BugTracker
from src.models.issues import IssueCreate, IssueUpdate
from src.config import Config
from src.utils.logger import logger
from src.utils.time_sync import timestamp

# --- Kimlik Doğrulama (Faz 1) ---
import socket
from fastapi import Cookie, Depends, HTTPException, status
from pydantic import BaseModel as _PydBaseModel
from src.auth.user_store import UserStore
from src.auth.auth_manager import AuthManager, SESSION_COOKIE

app = FastAPI(
    title="KuCoin Al-Sat Botu",
    description="KuCoin borsası için al-sat botu API'si ve dashboard.",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

market = KuCoinMarket()
orders = KuCoinOrders(market=market)
account = KuCoinAccount(orders=orders)
settings_mgr = SettingsManager(market=market)
recommender = RecommendationEngine(orders=orders, market=market)
market_regime = MarketRegime()
bug_tracker = BugTracker()

# --- Auth instance & dependency (Faz 1) ---
def _detect_server_ip() -> str | None:
    """Sunucunun yerel ağ IP'sini tespit et (yerel-ağ istisnası için)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


user_store = UserStore()
auth_manager = AuthManager(user_store, server_ip=_detect_server_ip())


def _client_ip(request: Request) -> str | None:
    """İstemci IP'sini al (proxy arkasında X-Forwarded-For öncelikli)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


async def get_current_user(
    request: Request,
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> dict:
    """Auth guard: geçerli oturumdaki kullanıcıyı döndürür, yoksa 401."""
    user = await auth_manager.resolve_session(session_cookie)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Oturum bulunamadı veya süresi doldu. Lütfen giriş yapın.")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Yalnızca admin rolüne izin verir."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Bu işlem için yönetici yetkisi gerekli.")
    return user


# --- Request-scoped borsa client fabrikası ---
from src.exchanges.factory import ExchangeClientFactory

client_factory = ExchangeClientFactory(user_store, shared_market=market)


async def get_user_orders(request: Request):
    """Oturumdaki kullanıcının Orders client'ı. Auth kapalıysa global instance (test)."""
    user = getattr(request.state, "user", None)
    if user is None:
        return orders  # auth_enabled=False (test) veya exempt
    return await client_factory.get_orders_for_user(user["id"])


async def get_user_account(request: Request):
    """Oturumdaki kullanıcının Account client'ı. Auth kapalıysa global instance (test)."""
    user = getattr(request.state, "user", None)
    if user is None:
        return account
    return await client_factory.get_account_for_user(user["id"])


def get_user_settings(request: Request):
    """Oturumdaki kullanıcıya bağlı SettingsManager. Auth kapalıysa global (test)."""
    user = getattr(request.state, "user", None)
    if user is None:
        return settings_mgr
    return settings_mgr.for_user(user["id"])


class LoginRequest(_PydBaseModel):
    username: str
    password: str
    totp_code: str | None = None


@app.on_event("startup")
async def startup_event():
    """
    Uygulama açılırken canlı bakiye WebSocket akışını başlat.
    MODULE_1_SPEC 3.3: REST bakiye çekimi sonrası WebSocket aboneliği.
    """
    await bug_tracker.init_db()
    await user_store.init_db()
    # Kaydedilmiş varsayılan modu yükle ve emir motoruna uygula
    try:
        s_data = await settings_mgr.get_settings()
        saved_mode = s_data.get("data", {}).get("default_mode")
        if saved_mode in ("paper", "live"):
            await orders.switch_mode(saved_mode)
            logger.info(f"💾 Kaydedilmiş mod yüklendi: {saved_mode}")
    except Exception as e:
        logger.error(f"Başlangıç mod yükleme hatası: {e}")

    if account.config.validate_credentials():
        # İlk REST bakiye çekimi (state'i hazırlar)
        await account.get_balances()
        await account.start_balance_stream()
    else:
        logger.warning("API kimlik bilgileri eksik; WebSocket bakiye akışı başlatılmadı.")


@app.on_event("shutdown")
async def shutdown_event():
    """Uygulama kapanırken ccxt exchange kaynaklarını serbest bırak."""
    await account.close()
    await market.close()
    await orders.close()


STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")


# Middleware: Hata durumunda istekleri logla
from fastapi import Request
from fastapi.responses import JSONResponse

# Auth zorunlu değil sayılan path önekleri (public)
_AUTH_EXEMPT_PREFIXES = (
    "/api/v1/auth/",   # login/logout/me
    "/static",
    "/ws",             # websocket kendi auth'unu yapar (Faz sonrası)
    "/docs", "/openapi.json", "/redoc",
)

# Test/geliştirme için auth zorlamasını kapatma bayrağı (varsayılan: açık)
app.state.auth_enabled = True


def _is_auth_exempt(path: str) -> bool:
    if path == "/" or path == "/api" or path == "/login":
        return True
    return any(path.startswith(p) for p in _AUTH_EXEMPT_PREFIXES)


@app.middleware("http")
async def auth_guard_mw(request: Request, call_next):
    """Korumalı yollara oturumsuz erişimi 401 ile engeller (public yollar hariç)."""
    if getattr(app.state, "auth_enabled", True) and request.url.path.startswith("/api/v1/") \
            and not _is_auth_exempt(request.url.path):
        session_id = request.cookies.get(SESSION_COOKIE)
        user = await auth_manager.resolve_session(session_id)
        if not user:
            return JSONResponse(
                status_code=401,
                content={"success": False, "data": {}, "error": "Oturum gerekli. Lütfen giriş yapın.",
                         "timestamp": timestamp()},
            )
        # Kullanıcıyı sonraki katmanlara aktar
        request.state.user = user
    return await call_next(request)


@app.middleware("http")
async def log_errors(request: Request, call_next):
    try:
        response = await call_next(request)
        # Hata durumları HTTPException veya Exception raised
        return response
    except Exception as e:
        # Hata oluştu, isteği logla
        query_params = dict(request.query_params)
        body = None
        try:
            body = await request.json()
            # Güvenlik: API key/secret çıkart
            for key in ["apiKey", "secret", "password", "api_key", "api_secret"]:
                body.pop(key, None)
        except Exception:
            pass
        log_api_request(
            logger,
            request.method,
            request.url.path,
            params=query_params if query_params else None,
            body=body,
            error=str(e),
        )
        raise  # Hatayı yukarı fırlat


@app.get("/")
async def dashboard():
    """Web Dashboard (tek sayfa uygulama)."""
    index = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"success": False, "error": "Dashboard bulunamadı", "timestamp": timestamp()}


@app.get("/login")
async def login_page():
    """Giriş ekranı (auth gerektirmez)."""
    page = os.path.join(STATIC_DIR, "login.html")
    if os.path.exists(page):
        return FileResponse(page)
    return {"success": False, "error": "Giriş ekranı bulunamadı", "timestamp": timestamp()}


@app.get("/api")
async def api_info():
    """API bilgi endpoint'i."""
    return {
        "success": True,
        "data": {
            "name": "KuCoin Al-Sat Botu",
            "version": "1.0.0",
            "status": "running"
        },
        "error": None,
        "timestamp": timestamp()
    }


# ============================================================================
# Kimlik Doğrulama (Faz 1)
# ============================================================================
@app.post("/api/v1/auth/login")
async def auth_login(req: LoginRequest, request: Request):
    """Kullanıcı adı/şifre (+ gerekiyorsa TOTP) ile giriş. Session cookie kurar."""
    ip = _client_ip(request)
    result = await auth_manager.login(req.username, req.password, req.totp_code, request_ip=ip)
    if not result["success"]:
        payload = {"success": False, "data": {"totp_required": result.get("totp_required", False)},
                   "error": result["error"], "timestamp": timestamp()}
        return JSONResponse(status_code=401, content=payload)
    resp = JSONResponse(content={
        "success": True, "data": {"user": result["user"]}, "error": None, "timestamp": timestamp()})
    # HttpOnly cookie — JS erişemez (XSS koruması)
    resp.set_cookie(
        key=SESSION_COOKIE, value=result["session_id"],
        httponly=True, samesite="lax", max_age=12 * 3600, path="/",
    )
    return resp


@app.post("/api/v1/auth/logout")
async def auth_logout(request: Request,
                      session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE)):
    """Oturumu sonlandırır ve cookie'yi siler."""
    await auth_manager.logout(session_cookie)
    resp = JSONResponse(content={"success": True, "data": {}, "error": None, "timestamp": timestamp()})
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp


@app.get("/api/v1/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    """Geçerli oturumdaki kullanıcı bilgisini döner."""
    return {"success": True,
            "data": {"id": user["id"], "username": user["username"], "role": user["role"],
                     "totp_enabled": bool(user.get("totp_secret"))},
            "error": None, "timestamp": timestamp()}


# --- 2FA (TOTP) kullanıcı-yönetimli kurulum ---
from src.auth import auth_service as _auth_svc


class Enable2FARequest(_PydBaseModel):
    secret: str
    code: str


class Disable2FARequest(_PydBaseModel):
    # Doğrulama için mevcut TOTP kodu VEYA hesap şifresi
    code: str | None = None
    password: str | None = None


@app.get("/api/v1/auth/2fa/status")
async def twofa_status(user: dict = Depends(get_current_user)):
    """Kullanıcının 2FA'sının aktif olup olmadığını döner."""
    return {"success": True, "data": {"enabled": bool(user.get("totp_secret"))},
            "error": None, "timestamp": timestamp()}


@app.post("/api/v1/auth/2fa/setup")
async def twofa_setup(user: dict = Depends(get_current_user)):
    """
    Yeni bir TOTP secret + QR üretir (henüz KAYDETMEZ). Kullanıcı authenticator'a
    ekleyip 'enable' ile doğrulayınca aktifleşir. Secret, enable çağrısında geri gönderilir.
    """
    if user.get("totp_secret"):
        return JSONResponse(status_code=400, content={
            "success": False, "data": {}, "error": "2FA zaten aktif. Önce devre dışı bırakın.",
            "timestamp": timestamp()})
    secret = _auth_svc.generate_totp_secret()
    qr = _auth_svc.totp_qr_data_uri(secret, user["username"])
    uri = _auth_svc.totp_provisioning_uri(secret, user["username"])
    return {"success": True, "data": {"secret": secret, "qr_data_uri": qr, "otpauth_uri": uri},
            "error": None, "timestamp": timestamp()}


@app.post("/api/v1/auth/2fa/enable")
async def twofa_enable(req: Enable2FARequest, user: dict = Depends(get_current_user)):
    """Setup'tan gelen secret + authenticator kodunu doğrular; doğruysa 2FA'yı aktifleştirir."""
    if user.get("totp_secret"):
        return JSONResponse(status_code=400, content={
            "success": False, "data": {}, "error": "2FA zaten aktif.", "timestamp": timestamp()})
    if not _auth_svc.verify_totp(req.secret, req.code):
        return JSONResponse(status_code=400, content={
            "success": False, "data": {}, "error": "Kod doğrulanamadı. Authenticator kodunu kontrol edin.",
            "timestamp": timestamp()})
    await user_store.update_user_fields(user["id"], totp_secret=req.secret)
    return {"success": True, "data": {"enabled": True}, "error": None, "timestamp": timestamp()}


@app.post("/api/v1/auth/2fa/disable")
async def twofa_disable(req: Disable2FARequest, user: dict = Depends(get_current_user)):
    """Mevcut TOTP kodu veya hesap şifresi ile doğrulayarak 2FA'yı devre dışı bırakır."""
    if not user.get("totp_secret"):
        return JSONResponse(status_code=400, content={
            "success": False, "data": {}, "error": "2FA zaten kapalı.", "timestamp": timestamp()})
    verified = False
    if req.code and _auth_svc.verify_totp(user["totp_secret"], req.code):
        verified = True
    elif req.password and _auth_svc.verify_password(req.password, user["password_hash"]):
        verified = True
    if not verified:
        return JSONResponse(status_code=400, content={
            "success": False, "data": {}, "error": "Doğrulama başarısız (kod veya şifre hatalı).",
            "timestamp": timestamp()})
    await user_store.update_user_fields(user["id"], totp_secret=None)
    return {"success": True, "data": {"enabled": False}, "error": None, "timestamp": timestamp()}


@app.get("/api/v1/account/status")
async def get_account_status(account=Depends(get_user_account)):
    """KuCoin API bağlantı durumu, gecikme süresi (ms) ve yetkileri döndürür."""
    result = await account.get_status()
    return result


@app.get("/api/v1/account/balances")
async def get_account_balances(account=Depends(get_user_account)):
    """Tüm kripto varlıkların serbest, kilitli ve USDT karşılığı bakiyelerini listeler."""
    result = await account.get_balances()
    return result


@app.get("/api/v1/account/summary")
async def get_portfolio_summary(account=Depends(get_user_account)):
    """Toplam portföy değeri ve serbest nakit özetini döndürür."""
    result = await account.get_summary()
    return result


@app.post("/api/v1/account/test-connection")
async def test_connection():
    """API anahtarlarını anlık olarak test eder ve doğrular."""
    result = account.test_connection()
    return result


class TransferRequest(_PydBaseModel):
    currency: str = "USDT"
    amount: float
    from_account: str   # spot | funding | margin | futures
    to_account: str


@app.post("/api/v1/account/transfer")
async def transfer_funds(req: TransferRequest, account=Depends(get_user_account)):
    """Hesap içi para transferi (Spot/Funding/Margin/Futures arası). Sonrası bakiye yenilenir."""
    result = await account.transfer_funds(
        req.currency, req.amount, req.from_account, req.to_account
    )
    if not result.get("success"):
        return JSONResponse(status_code=400, content=result)
    return result


# ============================================================================
# Modül 2: Piyasa Verileri (Market Data & Analysis)
# ============================================================================

@app.get("/api/v1/market/ticker")
async def get_market_ticker(symbol: str = "BTC/USDT", market_type: str = "spot"):
    """Belirtilen sembolün anlık fiyat ve 24s verilerini getirir (Spot, Margin, Futures)."""
    result = await market.get_ticker(symbol, market_type=market_type)
    return result


@app.get("/api/v1/market/orderbook")
async def get_market_orderbook(symbol: str = "BTC/USDT"):
    """Emir defteri (Level 2): best bid/ask, spread ve derinlik dengesizliği."""
    result = await market.get_orderbook(symbol)
    return result


@app.get("/api/v1/market/candles")
async def get_market_candles(
    symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 200,
    market_type: str = "spot"
):
    """Belirtilen zaman dilimindeki geçmiş OHLCV mum verilerini getirir (Spot, Margin, Futures)."""
    result = await market.get_candles(symbol, timeframe, limit, market_type=market_type)
    return result


@app.get("/api/v1/market/symbols")
async def get_market_symbols(quote: str = "USDT"):
    """KuCoin'de işlem gören aktif kripto işlem çiftlerini listeler."""
    result = await market.get_symbols(quote)
    return result


@app.get("/api/v1/market/analysis/indicators")
async def get_market_indicators(
    symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 300,
    include_derivatives: bool = False
):
    """
    Çekirdek indikatör katmanlarını (Trend/Momentum/Volatilite/Güç/Hacim/Seviye) hesaplar.
    Yalnızca kapanmış mumlar kullanılır (repaint koruması).
    include_derivatives=true ile KuCoin Futures funding/open interest eklenir.
    """
    result = await market.get_indicators(symbol, timeframe, limit, include_derivatives)
    return result


@app.get("/api/v1/market/analysis/structure")
async def get_market_structure(
    symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 300
):
    """
    Market Structure / SMC analizi: swing yapısı, BOS, CHoCH, FVG, Order Block.
    Yalnızca kapanmış mumlar kullanılır (lookahead-korumalı).
    """
    result = await market.get_structure(symbol, timeframe, limit)
    return result


@app.get("/api/v1/market/analysis/score")
async def get_market_score(
    symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 300,
    market_type: str = "spot"
):
    """
    Bileşik puanlama: 0-100 boğa/ayı skoru, sinyal durumu, gerekçe ve risk uyarıları.
    Spot, Margin ve Futures piyasa türleri desteklenir.
    """
    result = await market.get_score(symbol, timeframe, limit, market_type=market_type)
    return result


@app.get("/api/v1/market/analysis/mtf")
async def get_market_mtf(
    symbol: str = "BTC/USDT", limit: int = 300, base_timeframe: str = "15m",
    market_type: str = "spot"
):
    """
    Multi-Timeframe hiyerarşik analiz:
    Standart: 4H rejim → 1H setup → 15m tetikleyici.
    Sub-15m (1m/3m/5m): 1H rejim → 15m setup → alt tetikleyici.
    """
    result = await market.get_mtf(symbol, limit, base_timeframe=base_timeframe, market_type=market_type)
    return result


@app.get("/api/v1/market/trade-setup")
async def get_trade_setup(
    symbol: str = "BTC/USDT", timeframe: str = "1h", side: str = "buy",
    limit: int = 300, market_type: str = "spot", leverage: float = 5.0
):
    """
    Analiz motorundan otomatik işlem seviyeleri (Entry/TP1/TP2/SL/R:R, likidasyon).
    Spot, Margin ve Futures piyasa türleri desteklenir.
    """
    result = await market.get_trade_setup(
        symbol, timeframe, side, limit, market_type=market_type, leverage=leverage
    )
    return result


@app.get("/api/v1/market/regime")
async def get_market_regime():
    """
    Katman 9: Piyasa geneli rejim — BTC.D, Total Market Cap, Stablecoin.D (CoinGecko).
    Risk-on / risk-off ve altseason ipucu üretir.
    """
    return await asyncio.to_thread(market_regime.get_regime)



# ============================================================================
# Modül 3: Al-Sat Emir Yönetimi (Orders & Execution)
# ============================================================================
from pydantic import BaseModel


class OrderCreateRequest(BaseModel):
    symbol: str = "BTC/USDT"
    side: str = "buy"          # buy | sell
    order_type: str = "market"  # market | limit
    amount: float = 0.001
    price: float | None = None  # limit için gerekli
    market_type: str = "spot"   # spot | margin | futures
    margin_mode: str = "cross"  # futures: cross | isolated
    leverage: float | None = None  # futures kaldıraç (opsiyonel)


class SwitchModeRequest(BaseModel):
    mode: str = "paper"  # paper | live


@app.post("/api/v1/orders/create")
async def create_order(req: OrderCreateRequest, orders=Depends(get_user_orders)):
    """Yeni Market veya Limit Al/Sat emri iletir (Gerçek veya Sanal). Spot/Margin/Futures."""
    try:
        result = await orders.create_order(
            req.symbol, req.side, req.order_type, req.amount, req.price, req.market_type,
            req.margin_mode, req.leverage,
        )
        return result
    except Exception as e:
        log_api_request(logger, "POST", "/api/v1/orders/create", body=req.dict(exclude_unset=True), error=str(e))
        raise


class BracketOrderRequest(BaseModel):
    symbol: str = "BTC/USDT"
    side: str = "buy"
    usdt_amount: float = 100.0
    entry_price: float
    stop_loss_price: float
    tp1_price: float
    tp2_price: float
    market_type: str = "spot"  # spot | margin | futures
    margin_mode: str = "cross"  # futures: cross | isolated
    leverage: float | None = None


@app.post("/api/v1/orders/bracket")
async def create_bracket(req: BracketOrderRequest, orders=Depends(get_user_orders)):
    """Akıllı Paket Emir: Giriş + TP1 (%50) + TP2 (%50) + SL (%100) tek pakette. Spot/Margin/Futures."""
    result = await orders.create_bracket_order(
        req.symbol, req.side, req.usdt_amount,
        req.entry_price, req.stop_loss_price, req.tp1_price, req.tp2_price,
        req.market_type, req.margin_mode, req.leverage,
    )
    return result


@app.get("/api/v1/orders/open")
async def get_open_orders(symbol: str | None = None, orders=Depends(get_user_orders)):
    """Borsada dolmayı bekleyen açık emirleri listeler."""
    result = await orders.get_open_orders(symbol)
    return result


@app.get("/api/v1/orders/positions")
async def get_positions(symbol: str | None = None, orders=Depends(get_user_orders)):
    """Açık pozisyonları, giriş ve stop fiyatlarını, anlık PnL ile döner."""
    result = await orders.get_positions(symbol)
    return result



@app.get("/api/v1/orders/history")
async def get_order_history(symbol: str | None = None, limit: int | None = 200, orders=Depends(get_user_orders)):
    """Geçmişte dolan veya kapanan emir geçmişini döner."""
    result = await orders.get_history(symbol, limit)
    return result


@app.get("/api/v1/orders/pnl")
async def get_pnl_report(symbol: str | None = None, limit: int = 200, orders=Depends(get_user_orders)):
    """Emir geçmişinden hesaplanan kar/zarar (P&L) raporunu döner."""
    result = await orders.get_pnl_report(symbol, limit)
    return result


@app.delete("/api/v1/orders/{order_id}")
async def cancel_order(order_id: str, symbol: str | None = None, orders=Depends(get_user_orders)):
    """Belirtilen açık emri iptal eder."""
    result = await orders.cancel_order(order_id, symbol)
    return result


class OrderAmendRequest(BaseModel):
    price: float | None = None
    amount: float | None = None
    symbol: str | None = None


@app.put("/api/v1/orders/{order_id}")
async def amend_order(order_id: str, req: OrderAmendRequest, orders=Depends(get_user_orders)):
    """Açık emrin fiyatını ve/veya miktarını günceller (Amend)."""
    result = await orders.amend_order(order_id, req.price, req.amount, req.symbol)
    return result


@app.get("/api/v1/orders/recommendations")
async def get_recommendations():
    """Açık emirler + canlı piyasadan dinamik güncelleme tavsiyeleri üretir."""
    return await recommender.get_recommendations()


class ApplyRecRequest(BaseModel):
    order_id: str
    new_price: float | None = None


@app.post("/api/v1/orders/recommendations/apply")
async def apply_recommendation(req: ApplyRecRequest):
    """Bir tavsiyeyi uygular (örn. SL fiyatını günceller)."""
    return await recommender.apply_recommendation(req.order_id, req.new_price)


@app.post("/api/v1/orders/panic-stop")
async def panic_stop(orders=Depends(get_user_orders)):
    """Acil Durum: Tüm açık emirleri anında iptal eder ve botu durdurur."""
    result = await orders.panic_stop()
    return result


@app.post("/api/v1/orders/switch-mode")
async def switch_mode(req: SwitchModeRequest):
    """Gerçek KuCoin modu ile Simülasyon (Paper Trading) modu arasında geçiş yapar."""
    result = await orders.switch_mode(req.mode)
    if result.success:
        await settings_mgr.update_settings({"default_mode": req.mode})
    return result


@app.get("/api/v1/orders/mode")
async def get_order_mode():
    """Mevcut emir motoru modunu (paper veya live) döner."""
    return {
        "success": True,
        "data": {
            "mode": orders.mode,
            "bot_active": orders.bot_active,
            "is_live": orders.mode == "live",
            "has_credentials": account.config.validate_credentials()
        },
        "error": None,
        "timestamp": timestamp()
    }


# ============================================================================
# Ayarlar & Çoklu Coin (Settings & Watchlist) — MODULE_3_SPEC 2.8
# ============================================================================
class SettingsUpdateRequest(BaseModel):
    watchlist: list[str] | None = None
    default_mode: str | None = None
    default_symbol: str | None = None
    default_timeframe: str | None = None
    risk: dict | None = None


class WatchlistItemRequest(BaseModel):
    symbol: str


@app.get("/api/v1/settings")
async def get_settings(sm=Depends(get_user_settings)):
    """İzleme listesi, varsayılan mod ve risk parametrelerini döner."""
    return await sm.get_settings()


@app.post("/api/v1/settings")
async def update_settings(req: SettingsUpdateRequest, orders=Depends(get_user_orders), sm=Depends(get_user_settings)):
    """Ayarları kaydeder ve SQLite'ta kalıcı kılar."""
    payload = {k: v for k, v in req.model_dump().items() if v is not None}
    if "default_mode" in payload and payload["default_mode"] in ("paper", "live"):
        await orders.switch_mode(payload["default_mode"])
    return await sm.update_settings(payload)


@app.get("/api/v1/settings/symbols")
async def search_settings_symbols(query: str = "", quote: str = "USDT", sm=Depends(get_user_settings)):
    """KuCoin geçerli sembollerini arar ve listeler."""
    return await sm.search_symbols(query, quote)


@app.post("/api/v1/settings/watchlist")
async def add_watchlist(req: WatchlistItemRequest, sm=Depends(get_user_settings)):
    """İzleme listesine sembol ekler."""
    return await sm.add_to_watchlist(req.symbol)


@app.delete("/api/v1/settings/watchlist/{symbol:path}")
async def remove_watchlist(symbol: str, sm=Depends(get_user_settings)):
    """İzleme listesinden sembol çıkarır."""
    return await sm.remove_from_watchlist(symbol)


# --- Kullanıcı bazlı Borsa API Anahtarları ---
def _mask(value: str | None) -> str:
    """Hassas değeri maskeler: ilk 4 + **** + son 2 karakter."""
    if not value:
        return ""
    if len(value) <= 6:
        return "****"
    return f"{value[:4]}****{value[-2:]}"


class ApiKeysRequest(_PydBaseModel):
    api_key: str
    api_secret: str
    api_passphrase: str = ""
    is_sandbox: bool = False
    exchange: str = "kucoin"


@app.get("/api/v1/settings/api-keys")
async def get_api_keys(exchange: str = "kucoin", user: dict = Depends(get_current_user)):
    """
    Kullanıcının kayıtlı borsa API anahtarlarının DURUMUNU döndürür.
    Güvenlik: secret asla tam dönmez; yalnızca maskelenmiş önizleme.
    """
    keys = await user_store.get_api_keys(user["id"], exchange)
    if not keys:
        return {"success": True, "data": {"configured": False, "exchange": exchange},
                "error": None, "timestamp": timestamp()}
    return {"success": True, "data": {
        "configured": True,
        "exchange": exchange,
        "api_key_masked": _mask(keys["api_key"]),
        "api_passphrase_set": bool(keys["api_passphrase"]),
        "is_sandbox": keys["is_sandbox"],
    }, "error": None, "timestamp": timestamp()}


@app.post("/api/v1/settings/api-keys")
async def save_api_keys(req: ApiKeysRequest, user: dict = Depends(get_current_user)):
    """
    Kullanıcının borsa API anahtarlarını şifreli olarak kaydeder/günceller.
    Kaydetme sonrası kullanıcının önbellekteki borsa client'ları yenilenir.
    """
    if not req.api_key or not req.api_secret:
        return JSONResponse(status_code=400, content={
            "success": False, "data": {}, "error": "api_key ve api_secret zorunludur.",
            "timestamp": timestamp()})
    await user_store.save_api_keys(
        user["id"], req.api_key, req.api_secret, req.api_passphrase,
        exchange=req.exchange, is_sandbox=req.is_sandbox,
    )
    # Önbellekteki eski client'ları düşür → sonraki istekte yeni anahtarla kurulur
    await client_factory.invalidate_user(user["id"])
    return {"success": True, "data": {"configured": True, "exchange": req.exchange},
            "error": None, "timestamp": timestamp()}


# ============================================================================
# Hata Raporlama & Sorun Takibi (Issue Tracker)
# ============================================================================
@app.get("/api/v1/issues")
async def list_issues(status: str | None = None, category: str | None = None):
    """Kayıtlı hata bildirimlerini listeler."""
    try:
        issues = await bug_tracker.list_issues(status=status, category=category)
        open_count = sum(1 for i in issues if i["status"] in ("open", "in_progress"))
        resolved_count = sum(1 for i in issues if i["status"] in ("resolved", "closed"))
        return {
            "success": True,
            "data": issues,
            "total": len(issues),
            "open_count": open_count,
            "resolved_count": resolved_count,
            "error": None,
            "timestamp": timestamp(),
        }
    except Exception as e:
        logger.error(f"Hata listeleme başarısız: {e}")
        return {"success": False, "data": [], "total": 0, "open_count": 0, "resolved_count": 0, "error": str(e), "timestamp": timestamp()}


@app.post("/api/v1/issues")
async def create_issue(req: IssueCreate):
    """Yeni bir hata bildirimi kaydeder."""
    try:
        issue = await bug_tracker.create_issue(
            title=req.title,
            category=req.category,
            severity=req.severity,
            description=req.description,
            steps_to_reproduce=req.steps_to_reproduce,
            expected_behavior=req.expected_behavior,
            actual_behavior=req.actual_behavior,
            system_info=req.system_info,
        )
        return {"success": True, "data": issue, "error": None, "timestamp": timestamp()}
    except Exception as e:
        logger.error(f"Hata kaydı oluşturma başarısız: {e}")
        return {"success": False, "data": None, "error": str(e), "timestamp": timestamp()}


@app.get("/api/v1/issues/{issue_id}")
async def get_issue(issue_id: int):
    """Belirli bir hata bildiriminin detayını getirir."""
    try:
        issue = await bug_tracker.get_issue(issue_id)
        if not issue:
            return {"success": False, "data": None, "error": f"Hata #{issue_id} bulunamadı", "timestamp": timestamp()}
        return {"success": True, "data": issue, "error": None, "timestamp": timestamp()}
    except Exception as e:
        return {"success": False, "data": None, "error": str(e), "timestamp": timestamp()}


@app.patch("/api/v1/issues/{issue_id}")
async def update_issue(issue_id: int, req: IssueUpdate):
    """Hata durumunu veya çözüm notunu günceller."""
    try:
        updated = await bug_tracker.update_issue(
            issue_id=issue_id,
            status=req.status,
            resolution_note=req.resolution_note,
            severity=req.severity,
            title=req.title,
            description=req.description,
        )
        if not updated:
            return {"success": False, "data": None, "error": f"Hata #{issue_id} bulunamadı", "timestamp": timestamp()}
        return {"success": True, "data": updated, "error": None, "timestamp": timestamp()}
    except Exception as e:
        return {"success": False, "data": None, "error": str(e), "timestamp": timestamp()}


@app.delete("/api/v1/issues/{issue_id}")
async def delete_issue(issue_id: int):
    """Hata kaydını siler."""
    try:
        deleted = await bug_tracker.delete_issue(issue_id)
        if not deleted:
            return {"success": False, "error": f"Hata #{issue_id} bulunamadı", "timestamp": timestamp()}
        return {"success": True, "data": {"deleted_id": issue_id}, "error": None, "timestamp": timestamp()}
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": timestamp()}


@app.get("/api/v1/system/diagnostics")
async def get_diagnostics():
    """Sistem teşhis ve durum bilgilerini getirir."""
    try:
        diag = await bug_tracker.get_diagnostics()
        diag["orders_mode"] = orders.mode
        diag["bot_active"] = orders.bot_active
        diag["exchange_connected"] = bool(account.is_connected)
        settings_res = await settings_mgr.get_settings()
        watchlist = settings_res.get("data", {}).get("watchlist", []) if isinstance(settings_res, dict) else []
        diag["watchlist_count"] = len(watchlist)
        return {"success": True, "data": diag, "error": None, "timestamp": timestamp()}
    except Exception as e:
        return {"success": False, "data": None, "error": str(e), "timestamp": timestamp()}


# ============================================================================
# WebSocket: Canlı veri akışı (dashboard ve analiz ekranı için)
# ============================================================================
@app.websocket("/ws/live")
async def ws_live(
    websocket: WebSocket,
    symbol: str = "BTC/USDT",
    market_type: str = "spot",
):
    """
    Dashboard ve Analiz ekranlarına canlı ticker + portföy özeti + bağlantı durumu push eder.
    İstemci 'subscribe' mesajı göndererek sembol ve piyasa türünü (spot, margin, futures) dinamik değiştirebilir.
    """
    await websocket.accept()
    state = {
        "symbol": symbol,
        "market_type": market_type,
        "running": True,
    }
    trigger_tick = asyncio.Event()

    async def receiver():
        try:
            while state["running"]:
                try:
                    data = await websocket.receive_json()
                except json.JSONDecodeError:
                    continue
                if not isinstance(data, dict):
                    continue
                action = data.get("action")
                new_sym = data.get("symbol")
                new_mkt = data.get("market_type")
                updated = False
                if action == "subscribe" or new_sym:
                    if new_sym and isinstance(new_sym, str):
                        state["symbol"] = new_sym.strip()
                        updated = True
                    if new_mkt and isinstance(new_mkt, str):
                        state["market_type"] = new_mkt.strip().lower()
                        updated = True
                if updated:
                    trigger_tick.set()
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception as e:
            logger.debug(f"WS receiver sonlandı: {e}")
        finally:
            state["running"] = False
            trigger_tick.set()

    async def sender():
        try:
            while state["running"]:
                curr_sym = state["symbol"]
                curr_mkt = state["market_type"]
                payload = {
                    "type": "tick",
                    "timestamp": timestamp(),
                    "symbol": curr_sym,
                    "market_type": curr_mkt,
                }
                try:
                    ticker = await market.get_ticker(curr_sym, market_type=curr_mkt)
                    payload["ticker"] = ticker.data if ticker.success else None
                except Exception as e:
                    payload["ticker"] = None
                    logger.error(f"WS ticker hatası ({curr_sym}): {e}")

                try:
                    summary = await account.get_summary()
                    payload["summary"] = summary.data if summary.success else None
                except Exception:
                    payload["summary"] = None

                payload["mode"] = orders.mode
                payload["bot_active"] = orders.bot_active

                await websocket.send_json(payload)

                try:
                    await asyncio.wait_for(trigger_tick.wait(), timeout=2.0)
                    trigger_tick.clear()
                except asyncio.TimeoutError:
                    pass
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception as e:
            logger.error(f"WS sender hatası: {e}")
        finally:
            state["running"] = False

    recv_task = asyncio.create_task(receiver())
    send_task = asyncio.create_task(sender())

    try:
        done, pending = await asyncio.wait(
            [recv_task, send_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    except Exception as e:
        logger.error(f"WebSocket hatası: {e}")
    finally:
        recv_task.cancel()
        send_task.cancel()
        logger.info("WebSocket istemci bağlantısı kapandı.")


# Statik dosyaları (CSS/JS) sun — API rotalarından sonra mount edilir.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
