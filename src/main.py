"""
KuCoin Al-Sat Botu — FastAPI Uygulama Giriş Noktası
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.modules.module1_account import KuCoinAccount
from src.config import Config
from src.utils.logger import logger

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
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
    }


@app.get("/api/v1/account/status")
async def get_account_status():
    """KuCoin API bağlantı durumu, gecikme süresi (ms) ve yetkileri döndürür."""
    try:
        # API'ye bağlan
        if not account.exchange:
            account.connect()

        if account.is_connected:
            success, latency_ms, message = account._check_time_sync()
            permissions = []
            try:
                balance = await account.exchange.fetch_balance()
                permissions = list(set(balance.get("permissions", [])))
            except Exception as e:
                logger.error(f"Yetki kontrolü hatası: {e}")

            return {
                "success": True,
                "data": {
                    "status": "CONNECTED",
                    "is_sandbox": account.config.IS_SANDBOX,
                    "latency_ms": latency_ms,
                    "permissions": permissions
                },
                "error": None,
                "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
            }
        else:
            return {
                "success": False,
                "data": {},
                "error": "KuCoin API'ye bağlanılamadı",
                "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
            }
    except Exception as e:
        logger.error(f"Account status hatası: {e}")
        return {
            "success": False,
            "data": {},
            "error": f"Hata: {e}",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
        }


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
