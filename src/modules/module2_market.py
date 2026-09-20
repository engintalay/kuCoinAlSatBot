"""
KuCoin Al-Sat Botu — Modül 2: Piyasa Verileri (Temel Veri Katmanı)

Bu modül MODULE_2_SPEC Bölüm 2 (Data Ingestion Layer) kapsamını uygular:
- Canlı ticker (son fiyat, 24s high/low/hacim/değişim)
- Emir defteri (Level 2): best bid/ask, spread, order book imbalance
- Mum (OHLCV) verisi + Rolling Ring Buffer (300-500 mum) + repaint koruması
- Aktif işlem çiftleri listesi

Not: Çok katmanlı analiz motoru (10 indikatör katmanı, scoring, MTF) bu
temel katmanın üzerine sonraki parçalarda eklenecektir.
"""

import ccxt
import ccxt.async_support
import pandas as pd
from collections import deque

from src.config import Config
from src.models.market import (
    TickerResponse,
    CandlesResponse,
    SymbolListResponse,
    OrderBookResponse,
    AnalysisSignalResponse,
)
from src.modules.indicators.trend import compute_trend
from src.modules.indicators.momentum import compute_momentum
from src.modules.indicators.volatility import compute_volatility
from src.modules.indicators.strength import compute_strength
from src.modules.indicators.volume import compute_volume
from src.modules.indicators.levels import compute_levels
from src.modules.indicators.structure import compute_structure
from src.modules.indicators.derivatives import DerivativesData
from src.modules.analysis.scoring_engine import compute_score
from src.modules.analysis.mtf_engine import evaluate_mtf
from src.utils.logger import logger
from src.utils.time_sync import timestamp

# KuCoin fetch_order_book yalnızca 20 veya 100 limitini kabul eder.
ORDERBOOK_LIMIT = 20

# Ring buffer başına tutulacak maksimum kapanmış mum sayısı (spec 2.2).
RING_BUFFER_SIZE = 500

# Desteklenen zaman dilimleri (spec 2.2 — 15m altı 1m/3m/5m dahil).
SUPPORTED_TIMEFRAMES = ("1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d")


class KuCoinMarket:
    """KuCoin piyasa verisi çekme ve önbellekleme."""

    def __init__(self):
        self.config = Config()
        self.exchange: ccxt.async_support.kucoin | None = None
        # Ring buffer: {(symbol, timeframe): deque([[ts,o,h,l,c,v], ...])}
        self._candle_buffers: dict[tuple[str, str], deque] = {}
        # Katman 8: türev veri sağlayıcı (kucoinfutures)
        self.derivatives = DerivativesData()

    def connect(self) -> bool:
        """KuCoin public API'ye bağlan (piyasa verisi auth gerektirmez)."""
        try:
            self.exchange = ccxt.async_support.kucoin(
                {"sandbox": self.config.IS_SANDBOX}
            )
            logger.info("✅ KuCoin piyasa verisi bağlantısı kuruldu")
            return True
        except Exception as e:
            logger.error(f"❌ KuCoin piyasa bağlantı hatası: {e}")
            return False

    def _ensure_exchange(self) -> bool:
        """Exchange yoksa bağlanmayı dene (lazy connect)."""
        if not self.exchange:
            self.connect()
        return self.exchange is not None

    async def get_ticker(self, symbol: str, market_type: str = "spot") -> TickerResponse:
        """
        Belirtilen sembolün anlık fiyat ve 24s verilerini getirir (Spot, Margin, Futures).
        MODULE_2_SPEC 2.1.
        """
        try:
            if market_type == "futures":
                ft = await self.derivatives.get_futures_ticker(symbol)
                if ft:
                    return TickerResponse(
                        success=True,
                        data={
                            "symbol": symbol,
                            "market_type": "futures",
                            "last_price": ft.get("last"),
                            "high_24h": ft.get("high"),
                            "low_24h": ft.get("low"),
                            "volume_24h": ft.get("baseVolume"),
                            "quote_volume_24h": ft.get("quoteVolume"),
                            "change_percentage_24h": ft.get("percentage"),
                            "best_bid": ft.get("bid"),
                            "best_ask": ft.get("ask"),
                        },
                        error=None,
                        timestamp=timestamp(),
                    )

            if not self._ensure_exchange():
                return TickerResponse(
                    success=False, data={},
                    error="KuCoin API'ye bağlanılamadı",
                    timestamp=timestamp(),
                )

            t = await self.exchange.fetch_ticker(symbol)
            return TickerResponse(
                success=True,
                data={
                    "symbol": symbol,
                    "market_type": market_type,
                    "last_price": t.get("last"),
                    "high_24h": t.get("high"),
                    "low_24h": t.get("low"),
                    "volume_24h": t.get("baseVolume"),
                    "quote_volume_24h": t.get("quoteVolume"),
                    "change_percentage_24h": t.get("percentage"),
                    "best_bid": t.get("bid"),
                    "best_ask": t.get("ask"),
                },
                error=None,
                timestamp=timestamp(),
            )
        except Exception as e:
            logger.error(f"Ticker hatası ({symbol} {market_type}): {e}")
            return TickerResponse(
                success=False, data={},
                error=f"Ticker alınamadı: {e}",
                timestamp=timestamp(),
            )

    async def get_orderbook(self, symbol: str) -> OrderBookResponse:
        """
        Emir defteri (Level 2): best bid/ask, spread ve order book imbalance.
        MODULE_2_SPEC 2.1 (Level 2 Micro-structure).
        """
        try:
            if not self._ensure_exchange():
                return OrderBookResponse(
                    success=False, data={},
                    error="KuCoin API'ye bağlanılamadı",
                    timestamp=timestamp(),
                )

            ob = await self.exchange.fetch_order_book(symbol, ORDERBOOK_LIMIT)
            bids = ob.get("bids", [])
            asks = ob.get("asks", [])

            if not bids or not asks:
                return OrderBookResponse(
                    success=False, data={},
                    error="Emir defteri verisi boş",
                    timestamp=timestamp(),
                )

            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            spread = round(best_ask - best_bid, 8)
            mid = (best_ask + best_bid) / 2
            spread_percent = round(spread / mid * 100, 4) if mid > 0 else 0.0

            # Order Book Imbalance: (BidVol - AskVol) / (BidVol + AskVol)
            bid_vol = sum(float(b[1]) for b in bids)
            ask_vol = sum(float(a[1]) for a in asks)
            denom = bid_vol + ask_vol
            imbalance = round((bid_vol - ask_vol) / denom, 4) if denom > 0 else 0.0

            return OrderBookResponse(
                success=True,
                data={
                    "symbol": symbol,
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "spread": spread,
                    "spread_percent": spread_percent,
                    "bid_volume": round(bid_vol, 8),
                    "ask_volume": round(ask_vol, 8),
                    "imbalance": imbalance,
                },
                error=None,
                timestamp=timestamp(),
            )
        except Exception as e:
            logger.error(f"Order book hatası ({symbol}): {e}")
            return OrderBookResponse(
                success=False, data={},
                error=f"Emir defteri alınamadı: {e}",
                timestamp=timestamp(),
            )

    async def get_candles(
        self, symbol: str, timeframe: str = "1h", limit: int = 200,
        market_type: str = "spot"
    ) -> CandlesResponse:
        """
        Geçmiş OHLCV mum verilerini getirir ve ring buffer'a yazar.
        MODULE_2_SPEC 2.2 & 2.3: repaint koruması — son mum 'açık' (provisional)
        olarak işaretlenir, kapanmış mumlar 'confirmed' sayılır.
        """
        try:
            if timeframe not in SUPPORTED_TIMEFRAMES:
                return CandlesResponse(
                    success=False, data={},
                    error=f"Desteklenmeyen timeframe: {timeframe}. "
                          f"Geçerli: {', '.join(SUPPORTED_TIMEFRAMES)}",
                    timestamp=timestamp(),
                )

            if market_type == "futures":
                raw = await self.derivatives.get_futures_ohlcv(symbol, timeframe, limit=limit)
                if raw is None:
                    # fallback to spot if futures public endpoint fails or connection unavailable
                    if not self._ensure_exchange():
                        return CandlesResponse(
                            success=False, data={},
                            error="KuCoin Futures ve Spot API'ye bağlanılamadı",
                            timestamp=timestamp(),
                        )
                    raw = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            else:
                if not self._ensure_exchange():
                    return CandlesResponse(
                        success=False, data={},
                        error="KuCoin API'ye bağlanılamadı",
                        timestamp=timestamp(),
                    )
                raw = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

            # Ring buffer'ı güncelle (kapanmış mumlar).
            key = (symbol, timeframe)
            buf = self._candle_buffers.setdefault(key, deque(maxlen=RING_BUFFER_SIZE))
            buf.clear()
            buf.extend(raw)
            if market_type != "spot":
                self._candle_buffers[(f"{symbol}:{market_type}", timeframe)] = buf

            candles = []
            last_index = len(raw) - 1
            for i, c in enumerate(raw):
                candles.append({
                    "timestamp": int(c[0]),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5]),
                    # Repaint koruması: en son mum henüz kapanmamış olabilir.
                    "confirmed": i < last_index,
                })

            return CandlesResponse(
                success=True,
                data={
                    "symbol": symbol,
                    "market_type": market_type,
                    "timeframe": timeframe,
                    "count": len(candles),
                    "candles": candles,
                },
                error=None,
                timestamp=timestamp(),
            )
        except Exception as e:
            logger.error(f"Candle hatası ({symbol} {timeframe} {market_type}): {e}")
            return CandlesResponse(
                success=False, data={},
                error=f"Mum verisi alınamadı: {e}",
                timestamp=timestamp(),
            )

    async def get_symbols(self, quote: str = "USDT") -> SymbolListResponse:
        """
        KuCoin'de işlem gören aktif çiftleri listeler (varsayılan: USDT pariteleri).
        MODULE_2_SPEC Bölüm 4.
        """
        try:
            if not self._ensure_exchange():
                return SymbolListResponse(
                    success=False, data={},
                    error="KuCoin API'ye bağlanılamadı",
                    timestamp=timestamp(),
                )

            markets = await self.exchange.load_markets()
            symbols = sorted(
                m["symbol"] for m in markets.values()
                if m.get("active") and m.get("quote") == quote and m.get("spot")
            )

            return SymbolListResponse(
                success=True,
                data={"quote": quote, "count": len(symbols), "symbols": symbols},
                error=None,
                timestamp=timestamp(),
            )
        except Exception as e:
            logger.error(f"Sembol listesi hatası: {e}")
            return SymbolListResponse(
                success=False, data={},
                error=f"Sembol listesi alınamadı: {e}",
                timestamp=timestamp(),
            )

    async def get_indicators(
        self, symbol: str, timeframe: str = "1h", limit: int = 300,
        include_derivatives: bool = False
    ) -> AnalysisSignalResponse:
        """
        Çekirdek indikatör katmanlarını (Trend, Momentum, Volatilite) hesaplar.
        MODULE_2_SPEC Faz 2a. Repaint koruması: yalnızca kapanmış mumlar kullanılır.

        data_quality:
          - UNAVAILABLE: veri yok / çekilemedi / yetersiz
          - DEGRADED: EMA200 warm-up karşılanmıyor (<250 kapanmış mum)
          - OK: yeterli geçmiş var
        """
        try:
            candles_resp = await self.get_candles(symbol, timeframe, limit)
            if not candles_resp.success:
                return AnalysisSignalResponse(
                    success=False, data={"data_quality": "UNAVAILABLE"},
                    error=candles_resp.error,
                    timestamp=timestamp(),
                )

            all_candles = candles_resp.data.get("candles", [])
            # Repaint koruması: yalnızca kapanmış (confirmed) mumlar.
            confirmed = [c for c in all_candles if c.get("confirmed")]

            if len(confirmed) < 30:
                return AnalysisSignalResponse(
                    success=False,
                    data={"data_quality": "UNAVAILABLE",
                          "confirmed_candles": len(confirmed)},
                    error="Analiz için yetersiz kapanmış mum verisi (min 30).",
                    timestamp=timestamp(),
                )

            df = pd.DataFrame(confirmed)

            # EMA200 warm-up: max(lookback)+50 ~ 250 mum (spec 2.3).
            data_quality = "OK" if len(confirmed) >= 250 else "DEGRADED"

            indicators = {
                "trend": compute_trend(df),
                "momentum": compute_momentum(df),
                "volatility": compute_volatility(df),
                "strength": compute_strength(df),
                "volume": compute_volume(df),
                "levels": compute_levels(df),
            }

            # Katman 8: türev veri (opsiyonel, ek ağ çağrısı gerektirir)
            if include_derivatives:
                indicators["derivatives"] = await self.derivatives.get_derivatives(symbol)

            return AnalysisSignalResponse(
                success=True,
                data={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "data_quality": data_quality,
                    "confirmed_candles": len(confirmed),
                    "indicators": indicators,
                },
                error=None,
                timestamp=timestamp(),
            )
        except Exception as e:
            logger.error(f"İndikatör hesaplama hatası ({symbol} {timeframe}): {e}")
            return AnalysisSignalResponse(
                success=False, data={"data_quality": "UNAVAILABLE"},
                error=f"İndikatör hesaplanamadı: {e}",
                timestamp=timestamp(),
            )

    async def get_structure(
        self, symbol: str, timeframe: str = "1h", limit: int = 300, swing_n: int = 3
    ) -> AnalysisSignalResponse:
        """
        Market Structure / SMC analizi (swing, BOS, CHoCH, FVG, Order Block).
        MODULE_2_SPEC 3.7. Yalnızca kapanmış mumlar (repaint koruması).
        """
        try:
            candles_resp = await self.get_candles(symbol, timeframe, limit)
            if not candles_resp.success:
                return AnalysisSignalResponse(
                    success=False, data={"data_quality": "UNAVAILABLE"},
                    error=candles_resp.error, timestamp=timestamp(),
                )

            confirmed = [c for c in candles_resp.data.get("candles", []) if c.get("confirmed")]
            if len(confirmed) < (2 * swing_n + 3):
                return AnalysisSignalResponse(
                    success=False,
                    data={"data_quality": "UNAVAILABLE", "confirmed_candles": len(confirmed)},
                    error="Yapı analizi için yetersiz kapanmış mum verisi.",
                    timestamp=timestamp(),
                )

            df = pd.DataFrame(confirmed)
            structure = compute_structure(df, n=swing_n)

            return AnalysisSignalResponse(
                success=True,
                data={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "data_quality": "OK" if len(confirmed) >= 250 else "DEGRADED",
                    "confirmed_candles": len(confirmed),
                    "market_structure": structure,
                },
                error=None, timestamp=timestamp(),
            )
        except Exception as e:
            logger.error(f"Yapı analizi hatası ({symbol} {timeframe}): {e}")
            return AnalysisSignalResponse(
                success=False, data={"data_quality": "UNAVAILABLE"},
                error=f"Yapı analizi yapılamadı: {e}", timestamp=timestamp(),
            )

    async def _all_features(
        self, symbol: str, timeframe: str, limit: int, market_type: str = "spot"
    ) -> dict | None:
        """
        Tek çekimle tüm katman feature'larını (indikatör + structure + türev) üretir.
        Yeterli kapanmış mum yoksa None döner.
        """
        candles_resp = await self.get_candles(symbol, timeframe, limit, market_type=market_type)
        if not candles_resp.success:
            return None
        confirmed = [c for c in candles_resp.data.get("candles", []) if c.get("confirmed")]
        if len(confirmed) < 30:
            return None

        df = pd.DataFrame(confirmed)
        feats = {
            "confirmed_candles": len(confirmed),
            "trend": compute_trend(df),
            "momentum": compute_momentum(df),
            "volatility": compute_volatility(df),
            "strength": compute_strength(df),
            "volume": compute_volume(df),
            "levels": compute_levels(df),
            "structure": compute_structure(df),
        }
        if market_type == "futures":
            feats["derivatives"] = await self.derivatives.get_derivatives(symbol)
        return feats

    async def get_score(
        self, symbol: str, timeframe: str = "1h", limit: int = 300,
        market_type: str = "spot"
    ) -> AnalysisSignalResponse:
        """
        Bileşik puanlama motoru: 0-100 boğa/ayı skoru, sinyal, gerekçe, uyarılar.
        MODULE_2_SPEC 4.2 & 4.3.
        """
        try:
            features = await self._all_features(symbol, timeframe, limit, market_type=market_type)
            if features is None:
                return AnalysisSignalResponse(
                    success=False, data={"data_quality": "UNAVAILABLE"},
                    error="Puanlama için yetersiz kapanmış mum verisi.",
                    timestamp=timestamp(),
                )
            score = compute_score(features, market_type=market_type)
            return AnalysisSignalResponse(
                success=True,
                data={
                    "symbol": symbol,
                    "market_type": market_type,
                    "timeframe": timeframe,
                    "data_quality": "OK" if features["confirmed_candles"] >= 250 else "DEGRADED",
                    "score": score,
                },
                error=None, timestamp=timestamp(),
            )
        except Exception as e:
            logger.error(f"Puanlama hatası ({symbol} {timeframe} {market_type}): {e}")
            return AnalysisSignalResponse(
                success=False, data={"data_quality": "UNAVAILABLE"},
                error=f"Puanlama yapılamadı: {e}", timestamp=timestamp(),
            )

    async def get_mtf(
        self, symbol: str, limit: int = 300, base_timeframe: str = "15m",
        market_type: str = "spot"
    ) -> AnalysisSignalResponse:
        """
        Multi-Timeframe analiz:
        Standart: 4H rejim → 1H setup → 15m trigger.
        15m altı (1m/3m/5m): 1H rejim → 15m setup → alt tetikleyici (örn. 5m).
        """
        try:
            if base_timeframe in ("1m", "3m", "5m"):
                chain = ("1h", "15m", base_timeframe)
            else:
                chain = ("4h", "1h", "15m")

            scores = {}
            for tf in chain:
                feats = await self._all_features(symbol, tf, limit, market_type=market_type)
                scores[tf] = compute_score(feats, market_type=market_type) if feats else {"signal": "NEUTRAL"}

            decision = evaluate_mtf(scores[chain[0]], scores[chain[1]], scores[chain[2]])
            return AnalysisSignalResponse(
                success=True,
                data={
                    "symbol": symbol,
                    "market_type": market_type,
                    "timeframe_chain": list(chain),
                    "timeframes": {chain[0]: scores[chain[0]], chain[1]: scores[chain[1]], chain[2]: scores[chain[2]]},
                    "decision": decision,
                },
                error=None, timestamp=timestamp(),
            )
        except Exception as e:
            logger.error(f"MTF analiz hatası ({symbol} {market_type}): {e}")
            return AnalysisSignalResponse(
                success=False, data={},
                error=f"MTF analizi yapılamadı: {e}", timestamp=timestamp(),
            )

    async def get_trade_setup(
        self, symbol: str, timeframe: str = "1h", side: str = "buy",
        limit: int = 300, market_type: str = "spot", leverage: float = 5.0
    ) -> AnalysisSignalResponse:
        """
        Analiz motorundan otomatik işlem seviyeleri üretir (Spot, Margin, Futures).
        MODULE_3_SPEC 2.5: Entry, TP1, TP2, Stop-Loss, R:R ve likidasyon seviyesi.
        """
        try:
            features = await self._all_features(symbol, timeframe, limit, market_type=market_type)
            if features is None:
                return AnalysisSignalResponse(
                    success=False, data={"data_quality": "UNAVAILABLE"},
                    error="İşlem seviyeleri için yetersiz kapanmış mum verisi.",
                    timestamp=timestamp(),
                )

            side = (side or "buy").lower()
            vol = features.get("volatility") or {}
            atr = vol.get("atr")
            trend = features.get("trend") or {}
            entry = trend.get("price")

            if entry is None or atr is None or atr <= 0:
                return AnalysisSignalResponse(
                    success=False, data={"data_quality": "DEGRADED"},
                    error="Giriş fiyatı veya ATR hesaplanamadı.", timestamp=timestamp(),
                )

            atr_mult = 1.5
            if side == "buy":
                stop_loss = entry - atr_mult * atr
                risk = entry - stop_loss
                tp1 = entry + 1.5 * risk
                tp2 = entry + 3.0 * risk
            else:
                stop_loss = entry + atr_mult * atr
                risk = stop_loss - entry
                tp1 = entry - 1.5 * risk
                tp2 = entry - 3.0 * risk

            setup_data = {
                "entry_price": round(float(entry), 8),
                "stop_loss_price": round(float(stop_loss), 8),
                "tp1_price": round(float(tp1), 8),
                "tp2_price": round(float(tp2), 8),
                "atr": round(float(atr), 8),
                "risk_per_unit": round(float(risk), 8),
                "risk_reward_ratio": 3.0,
            }

            # Margin ve Futures için kaldıraç & likidasyon seviyesi
            if market_type in ("futures", "margin"):
                lev = max(1.0, float(leverage or 5.0))
                liq_buffer = 0.9 / lev
                if side == "buy":
                    est_liq = entry * (1.0 - liq_buffer)
                else:
                    est_liq = entry * (1.0 + liq_buffer)
                setup_data["leverage"] = lev
                setup_data["est_liquidation_price"] = round(float(est_liq), 8)
                setup_data["liquidation_distance_percent"] = round(abs(entry - est_liq) / entry * 100, 2)
                if market_type == "futures" and "derivatives" in features:
                    setup_data["derivatives"] = features["derivatives"]

            return AnalysisSignalResponse(
                success=True,
                data={
                    "symbol": symbol,
                    "market_type": market_type,
                    "timeframe": timeframe,
                    "side": side,
                    "trade_setup": setup_data,
                },
                error=None, timestamp=timestamp(),
            )
        except Exception as e:
            logger.error(f"Trade setup hatası ({symbol} {timeframe} {market_type}): {e}")
            return AnalysisSignalResponse(
                success=False, data={},
                error=f"İşlem seviyeleri hesaplanamadı: {e}", timestamp=timestamp(),
            )

    def get_buffer(self, symbol: str, timeframe: str, market_type: str = "spot") -> list:
        """Bellekteki ring buffer'ın kopyasını döndürür (analiz motoru için)."""
        key = (f"{symbol}:{market_type}", timeframe)
        if key in self._candle_buffers:
            return list(self._candle_buffers[key])
        return list(self._candle_buffers.get((symbol, timeframe), []))


    async def close(self) -> None:
        """ccxt async exchange kaynaklarını serbest bırak."""
        await self.derivatives.close()
        if self.exchange is not None:
            try:
                await self.exchange.close()
            except Exception as e:
                logger.error(f"Market exchange kapatma hatası: {e}")
            finally:
                self.exchange = None
