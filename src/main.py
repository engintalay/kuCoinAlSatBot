"""
KuCoin Al-Sat Botu — FastAPI Uygulama Giriş Noktası
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.modules.module1_account import KuCoinAccount
from src.modules.module2_market import KuCoinMarket
from src.modules.module3_orders import KuCoinOrders
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


@app.on_event("startup")
async def startup_event():
    """
    Uygulama açılırken canlı bakiye WebSocket akışını başlat.
    MODULE_1_SPEC 3.3: REST bakiye çekimi sonrası WebSocket aboneliği.
    """
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


@app.get("/")
async def root():
    """Uygulama root endpoint."""
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
async def get_market_ticker(symbol: str = "BTC/USDT"):
    """Belirtilen sembolün anlık fiyat ve 24s verilerini getirir."""
    result = await market.get_ticker(symbol)
    return result


@app.get("/api/v1/market/orderbook")
async def get_market_orderbook(symbol: str = "BTC/USDT"):
    """Emir defteri (Level 2): best bid/ask, spread ve derinlik dengesizliği."""
    result = await market.get_orderbook(symbol)
    return result


@app.get("/api/v1/market/candles")
async def get_market_candles(
    symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 200
):
    """Belirtilen zaman dilimindeki geçmiş OHLCV mum verilerini getirir."""
    result = await market.get_candles(symbol, timeframe, limit)
    return result


@app.get("/api/v1/market/symbols")
async def get_market_symbols(quote: str = "USDT"):
    """KuCoin'de işlem gören aktif kripto işlem çiftlerini listeler."""
    result = await market.get_symbols(quote)
    return result


@app.get("/api/v1/market/analysis/indicators")
async def get_market_indicators(
    symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 300
):
    """
    Çekirdek indikatör katmanlarını (Trend/Momentum/Volatilite) hesaplar.
    Yalnızca kapanmış mumlar kullanılır (repaint koruması).
    """
    result = await market.get_indicators(symbol, timeframe, limit)
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
    symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 300
):
    """
    Bileşik puanlama: 0-100 boğa/ayı skoru, sinyal durumu, gerekçe ve risk uyarıları.
    """
    result = await market.get_score(symbol, timeframe, limit)
    return result


@app.get("/api/v1/market/analysis/mtf")
async def get_market_mtf(symbol: str = "BTC/USDT", limit: int = 300):
    """
    Multi-Timeframe hiyerarşik analiz: 4H rejim → 1H setup → 15m tetikleyici.
    """
    result = await market.get_mtf(symbol, limit)
    return result


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
