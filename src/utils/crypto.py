"""
KuCoin Al-Sat Botu — Kripto Formatlama Yardımcıları
"""

from decimal import Decimal, ROUND_HALF_UP


def format_price(symbol: str, value: float | Decimal) -> str:
    """Kripto fiyatını sembole göre formatla."""
    if isinstance(value, float):
        value = Decimal(str(value))

    # Fiyat hassasiyeti sembole göre
    precision = {
        "BTC": 2,
        "ETH": 2,
        "SOL": 2,
        "KCS": 2,
        "DOGE": 8,
        "SHIB": 8,
    }.get(symbol.upper(), 4)

    formatted = float(value).quantize(Decimal(10) ** (-precision), rounding=ROUND_HALF_UP)
    return f"{formatted:,.{precision}f}"


def format_amount(value: float | Decimal) -> str:
    """USDT tutarını formatla (2 ondalık + binlik ayraç)."""
    if isinstance(value, float):
        value = Decimal(str(value))
    return f"{float(value):,.2f}"
