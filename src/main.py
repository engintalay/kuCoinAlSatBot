"""
KuCoin Al-Sat Botu — FastAPI Uygulama Giriş Noktası
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.modules.module1_account import KuCoinAccount
from src.modules.module2_market import KuCoinMarket
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
