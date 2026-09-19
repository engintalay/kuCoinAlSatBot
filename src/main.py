"""
KuCoin Al-Sat Botu — FastAPI Uygulama Giriş Noktası
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.modules.module1_account import KuCoinAccount
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
