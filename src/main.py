"""
KuCoin Al-Sat Botu — FastAPI Uygulama Giriş Noktası
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import os

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

# KuCoin API bağlantısı instance
account = KuCoinAccount()
market = KuCoinMarket()
orders = KuCoinOrders(market=market)
settings_mgr = SettingsManager(market=market)
recommender = RecommendationEngine(orders=orders, market=market)
market_regime = MarketRegime()
bug_tracker = BugTracker()


@app.on_event("startup")
async def startup_event():
    """
    Uygulama açılırken canlı bakiye WebSocket akışını başlat.
    MODULE_1_SPEC 3.3: REST bakiye çekimi sonrası WebSocket aboneliği.
    """
    await bug_tracker.init_db()
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


@app.get("/")
async def dashboard():
    """Web Dashboard (tek sayfa uygulama)."""
    index = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"success": False, "error": "Dashboard bulunamadı", "timestamp": timestamp()}


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


@app.get("/api/v1/account/status")
async def get_account_status():
    """KuCoin API bağlantı durumu, gecikme süresi (ms) ve yetkileri döndürür."""
    result = await account.get_status()
    return result


@app.get("/api/v1/account/balances")
async def get_account_balances():
    """Tüm kripto varlıkların serbest, kilitli ve USDT karşılığı bakiyelerini listeler."""
    result = await account.get_balances()
    return result


@app.get("/api/v1/account/summary")
async def get_portfolio_summary():
    """Toplam portföy değeri ve serbest nakit özetini döndürür."""
    result = await account.get_summary()
    return result


@app.post("/api/v1/account/test-connection")
async def test_connection():
    """API anahtarlarını anlık olarak test eder ve doğrular."""
    result = account.test_connection()
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


class SwitchModeRequest(BaseModel):
    mode: str = "paper"  # paper | live


@app.post("/api/v1/orders/create")
async def create_order(req: OrderCreateRequest):
    """Yeni Market veya Limit Al/Sat emri iletir (Gerçek veya Sanal)."""
    result = await orders.create_order(
        req.symbol, req.side, req.order_type, req.amount, req.price
    )
    return result


class BracketOrderRequest(BaseModel):
    symbol: str = "BTC/USDT"
    side: str = "buy"
    usdt_amount: float = 100.0
    entry_price: float
    stop_loss_price: float
    tp1_price: float
    tp2_price: float


@app.post("/api/v1/orders/bracket")
async def create_bracket(req: BracketOrderRequest):
    """Akıllı Paket Emir: Giriş + TP1 (%50) + TP2 (%50) + SL (%100) tek pakette."""
    result = await orders.create_bracket_order(
        req.symbol, req.side, req.usdt_amount,
        req.entry_price, req.stop_loss_price, req.tp1_price, req.tp2_price,
    )
    return result


@app.get("/api/v1/orders/open")
async def get_open_orders(symbol: str | None = None):
    """Borsada dolmayı bekleyen açık emirleri listeler."""
    result = await orders.get_open_orders(symbol)
    return result


@app.get("/api/v1/orders/history")
async def get_order_history(symbol: str | None = None, limit: int = 50):
    """Geçmişte dolan veya kapanan emir geçmişini döner."""
    result = await orders.get_history(symbol, limit)
    return result


@app.delete("/api/v1/orders/{order_id}")
async def cancel_order(order_id: str, symbol: str | None = None):
    """Belirtilen açık emri iptal eder."""
    result = await orders.cancel_order(order_id, symbol)
    return result


class OrderAmendRequest(BaseModel):
    price: float | None = None
    amount: float | None = None
    symbol: str | None = None


@app.put("/api/v1/orders/{order_id}")
async def amend_order(order_id: str, req: OrderAmendRequest):
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
async def panic_stop():
    """Acil Durum: Tüm açık emirleri anında iptal eder ve botu durdurur."""
    result = await orders.panic_stop()
    return result


@app.post("/api/v1/orders/switch-mode")
async def switch_mode(req: SwitchModeRequest):
    """Gerçek KuCoin modu ile Simülasyon (Paper Trading) modu arasında geçiş yapar."""
    result = await orders.switch_mode(req.mode)
    return result


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
async def get_settings():
    """İzleme listesi, varsayılan mod ve risk parametrelerini döner."""
    return await settings_mgr.get_settings()


@app.post("/api/v1/settings")
async def update_settings(req: SettingsUpdateRequest):
    """Ayarları kaydeder ve SQLite'ta kalıcı kılar."""
    payload = {k: v for k, v in req.model_dump().items() if v is not None}
    return await settings_mgr.update_settings(payload)


@app.get("/api/v1/settings/symbols")
async def search_settings_symbols(query: str = "", quote: str = "USDT"):
    """KuCoin geçerli sembollerini arar ve listeler."""
    return await settings_mgr.search_symbols(query, quote)


@app.post("/api/v1/settings/watchlist")
async def add_watchlist(req: WatchlistItemRequest):
    """İzleme listesine sembol ekler."""
    return await settings_mgr.add_to_watchlist(req.symbol)


@app.delete("/api/v1/settings/watchlist/{symbol:path}")
async def remove_watchlist(symbol: str):
    """İzleme listesinden sembol çıkarır."""
    return await settings_mgr.remove_from_watchlist(symbol)


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
# WebSocket: Canlı veri akışı (dashboard için)
# ============================================================================
@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket, symbol: str = "BTC/USDT"):
    """
    Dashboard'a canlı ticker + portföy özeti + bağlantı durumu push eder.
    İstemci her ~3 saniyede güncel veri alır.
    """
    await websocket.accept()
    try:
        while True:
            payload = {"type": "tick", "timestamp": timestamp()}
            try:
                ticker = await market.get_ticker(symbol)
                payload["ticker"] = ticker.data if ticker.success else None
            except Exception as e:
                payload["ticker"] = None
                logger.error(f"WS ticker hatası: {e}")

            try:
                summary = await account.get_summary()
                payload["summary"] = summary.data if summary.success else None
            except Exception:
                payload["summary"] = None

            payload["mode"] = orders.mode
            payload["bot_active"] = orders.bot_active

            await websocket.send_json(payload)
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        logger.info("WebSocket istemci bağlantısı kapandı.")
    except Exception as e:
        logger.error(f"WebSocket hatası: {e}")


# Statik dosyaları (CSS/JS) sun — API rotalarından sonra mount edilir.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
