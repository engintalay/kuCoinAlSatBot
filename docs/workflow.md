# KuCoin Al-Sat Botu — Workflow & Geliştirme Planı

> **Tasarım & Spesifikasyon Durumu:** %100 (Onaylandı & Genişletildi ✅) | **Kodlama & Test Durumu:** Tüm modüller + Frontend + Hata Raporlama + Spot/Margin/Futures Emir & Bakiye + Açık Pozisyonlar + Kar/Zarar Raporu %100 ✅ (210/210 Test Geçiyor, %80 Coverage ✅) | **Son Güncelleme:** 2026-09-23 19:41:00 (+03:00)

---

## 1. Mevcut Durum

| Öğe | Durum |
|-----|-------|
| Tasarım Dokümantasyonu | ✅ Tamamlandı (`docs/`) |
| `.env` Yapılandırma Dosyası | ✅ Oluşturuldu (Kök dizinde mevcut) |
| Sanal Ortam & Yönetim Scriptleri | ✅ Tamamlandı (`install.sh`, `first_run.sh`, `run.sh`, `run_tests.sh`) |
| `requirements.txt` | ✅ Güncellendi (`aiosqlite`, `requests` dahil) & Sanal ortama kuruldu |
| Proje İskeleti (`src/`) | ✅ Oluşturuldu (`config`, `database`, `utils`, `models`, `modules`, `indicators`, `analysis`, `settings`, `recommendations`) |
| Modül 1 (Hesap & Bağlantı) | ✅ **%100 Tamamlandı** (Bağlantı, bakiye, portföy payı, yetki denetimi, WebSocket stream) — 29 test |
| Modül 2 — Faz 2a (Veri & Çekirdek İndikatörler) | ✅ **%100 Tamamlandı** (Ticker, L2 Order Book, Ring Buffer, Repaint Guard, Trend, Momentum, Volatilite, 5 REST endpoint'i) |
| Modül 2 — Faz 2b (İleri SMC, Scoring & MTF) | ✅ **%100 Tamamlandı** (Supertrend, Ichimoku, Parabolic SAR, ADX, Aroon, Choppiness, Squeeze, SMC Swings/BOS/CHoCH/FVG/OB, 0-100 Puanlama Motoru, MTF Hiyerarşisi, 3 REST endpoint'i) |
| Modül 2 — İleri Katmanlar (Hacim & Seviyeler) | ✅ **%100 Tamamlandı** (`indicators/volume.py`: RVOL, OBV, VWAP, MFI, CMF, Volume Profile; `indicators/levels.py`: Pivots, Fib, Donchian; Hacim Puanlaması) — 10 test |
| Modül 2 — Faz 2c (Ek Osilatörler, Türev, Çoklu Piyasa, Sub-15m, Katman 9) | ✅ **%100 Tamamlandı** (StochRSI, CCI, Williams %R, ROC; KuCoin Futures USDT-M funding/OI, 1m/3m/5m timeframe, Spot/Margin/Futures analiz, trade-setup; Katman 9 CoinGecko BTC.D/Total MCap/Stablecoin.D) — 22 test |
| Modül 2 — Sadeleştirilmiş & Eğitici Analiz Motoru | ✅ **%100 Tamamlandı** (Sade durum & tavsiye özeti, 4-boyutlu gerekçeler: İndikatör, Neden Oldu, Neyi Gösterir, Neye Sebep Olur; Korunma tavsiyeli risk uyarıları) — 2 test |
| Modül 2 — Test Dağılımı | ✅ 79 test: `market: 8`, `indicators: 19`, `volume_levels: 10`, `structure: 8`, `analysis: 12`, `phase2c: 10`, `market_types: 12` |
| Modül 3 (Emir Yönetimi, Bracket & Öneriler) | ✅ **%100 Tamamlandı** (Market/Limit, açık emir & geçmiş, iptal, Panic Stop, Paper Trading $10k, mod geçişi, pre-trade risk, Bracket orders, Amend, RecommendationEngine) — 31 test |
| Ayarlar & Çoklu Coin Modülü (`settings.py`) | ✅ **%100 Tamamlandı** (Watchlist yönetimi, mod/sembol ayarları, SQLite kalıcılık, sembol arama; 5 REST endpoint'i) — 6 test |
| Frontend Dashboard (Adım 5) | ✅ **%100 Tamamlandı** (Dark glassmorphism SPA: header/sidebar/footer + Panic Stop, 6 görünüm, SVG mum grafiği, WebSocket canlı akış, Kılavuz, 7 Info butonu, Ayarlar paneli, Seviyeli mum grafiği, Sade özet kartı & 4-boyutlu eğitici gerekçe gridleri; `static/` mount) — 11 servis testi |
| Yardımcı Fonksiyonlar (`utils/`) | ✅ **%100 Tamamlandı** (`crypto.py`, `time_sync.py`, `logger.py` — %100 coverage) — 14 test |
| Toplam Birim Test Durumu | ✅ **174/174 test başarıyla geçiyor** (`run_tests.sh` %100 yeşil) |



---

## 2. Proje Yapısı

> **Not:** Aşağıdaki ağaç **hedef (nihai) yapıdır**. Kaynak: `src/{config,database,main}.py`, `src/utils/*`, `src/models/*`, `src/modules/{module1_account,module2_market,module3_orders,settings,recommendations,market_regime}.py`, `src/modules/indicators/{trend,momentum,strength,volatility,structure,volume,levels,derivatives}.py`, `src/modules/analysis/{scoring_engine,mtf_engine}.py`, Frontend `static/{index.html,css/style.css,js/app.js}`. Testler: 15 dosya — toplam **174 test**. Henüz oluşturulmayanlar (opsiyonel): `analysis/feature_engine.py`, `analysis/filters.py` (mantık `_all_features`/`scoring_engine` içine gömülü), `conftest.py`, CVD/L-S Ratio (taker-akış verisi gerektirir).

```
kuCoinAlSatBot/
├── src/
│   ├── __init__.py
│   ├── main.py                  # FastAPI uygulama giriş noktası
│   ├── config.py                # .env okuma & yapılandırma
│   ├── database.py              # SQLite bağlantı
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py            # Logging yapısı
│   │   ├── crypto.py            # Kripto formatlama yardımcıları
│   │   └── time_sync.py         # Zaman senkronizasyonu
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── module1_account.py   # Modül 1: Hesap & Bağlantı
│   │   ├── module2_market.py    # Modül 2: Piyasa Verileri
│   │   └── module3_orders.py    # Modül 3: Emir Yönetimi
│   └── models/
│       ├── __init__.py
│       ├── account.py           # Pydantic şemalar (Modül 1)
│       ├── market.py            # Pydantic şemalar (Modül 2)
│       └── orders.py            # Pydantic şemalar (Modül 3)
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures & mocks
│   ├── test_module_1_account.py
│   ├── test_module_2_market.py
│   ├── test_module_3_orders.py
│   └── test_utils.py
├── install.sh               # Sanal ortam ve bağımlılık kurulum scripti
├── first_run.sh             # İlk çalıştırma ve hazırlık sihirbazı
├── run.sh                   # Uygulama başlatma scripti
├── run_tests.sh             # Otomatik birim test ve raporlama scripti
├── requirements.txt         # Python bağımlılıkları listesi
├── .env.example             # Çevre değişkenleri şablonu
├── .env                     # Yerel çevre değişkenleri ve API anahtarları
└── docs/
    ├── PROJECT_ANALYSIS.md
    ├── GLOBAL_STANDARDS.md
    ├── MODULE_1_SPEC.md
    ├── MODULE_2_SPEC.md
    ├── MODULE_3_SPEC.md
    └── workflow.md
```

---

## 3. Sıralı Geliştirme Adımları

### ✅ Adım 1 — Proje İskeleti & Ortam Hazırlığı
- ✅ `requirements.txt` yazıldı ve sanal ortama kuruldu
- ✅ `.env.example` şablonu ve kök dizinde `.env` dosyası oluşturuldu
- ✅ Yönetim betikleri (`install.sh`, `first_run.sh`, `run.sh`, `run_tests.sh`) hazırlandı
- ✅ `src/` alt dizinleri ve `__init__.py` dosyaları oluşturuldu

### ✅ Adım 2 — Modül 1: KuCoin Bağlantısı & Hesap Durumu (Tamamlandı)
- ✅ `config.py` — `.env` okuma, yapılandırma
- ✅ `utils/logger.py` — Logging ayarları
- ✅ `utils/time_sync.py` — KuCoin zaman senkronizasyonu (`timestamp`, `check_time_sync`)
- ✅ `models/account.py` — Pydantic şemaları (`ConnectionStatusResponse`, `AccountBalancesResponse`, `PortfolioSummaryResponse`, `TestConnectionResponse`)
- ✅ `module1_account.py` — KuCoin API entegrasyonu
  - ✅ Bağlantı & kimlik bilgisi doğrulama (ccxt async kucoin)
  - ✅ Yetki kontrolü (Read/Trade/Withdraw denetimi)
  - ✅ Bakiye sorgulama (free/used/total, trade+main)
  - ✅ USDT karşılığı & portföy payı hesaplama
  - ✅ WebSocket bakiye aboneliği (`ccxt.pro`)
- ✅ `main.py` — `/api/v1/account/*` endpoint'leri (4 adet)

### ✅ Adım 3 — Modül 2: Çok Katmanlı Piyasa Verileri & Analiz Motoru (Analiz motoru tamamlandı)
- ✅ `models/market.py` — Pydantic yanıt modelleri (`TickerResponse`, `CandlesResponse`, `SymbolListResponse`, `OrderBookResponse`, `AnalysisSignalResponse`)
- ✅ `module2_market.py` — Ticker, L2 Derinlik, OHLCV verisi & Ring Buffer (500 mum)
- `indicators/` — Modüler indikatör katmanları:
  - ✅ `trend.py` (EMA 20/50/100/200, SMA, Supertrend, Ichimoku, SAR)
  - ✅ `momentum.py` (RSI 14, MACD) — *StochRSI, CCI, %R, ROC kapsam dışı (sonraki)*
  - ✅ `strength.py` (ADX, Aroon, Choppiness Index)
  - ✅ `volume.py` (RVOL, OBV, VWAP, MFI 14, CMF 20, Volume Profile POC/VAH/VAL)
  - ✅ `volatility.py` (ATR, Bollinger Bands, Keltner Channels, Squeeze)
  - ✅ `levels.py` (Pivot Points, PDH/PDL, Fibonacci Retracement, Donchian Channels)
  - ✅ `structure.py` (Swing High/Low, HH/HL/LH/LL, BOS, CHoCH, FVG, Order Block)
- `analysis/` — Analiz motoru ve strateji:
  - ✅ Feature Engine (`module2_market.py:_all_features` — tüm 6 katmanın birleşimi)
  - ✅ `scoring_engine.py` (0-100 Bileşik Puanlama: Hacim katkısı dahil max_points 80, Gerekçelendirme + risk filtreleri)
  - ✅ `mtf_engine.py` (4H Rejim → 1H Setup → 15m Tetikleyici)
- ✅ `main.py` — `/api/v1/market/*` endpoint'leri (8 adet: 4 veri + 4 analiz)
- ✅ **Faz 2c yapıldı:** Ek momentum osilatörleri (StochRSI, CCI, Williams %R, ROC) `indicators/momentum.py`'ye; Katman 8 (Türev — Funding Rate + Open Interest) `indicators/derivatives.py`'ye eklendi (`include_derivatives` flag).
- ✅ **Katman 9 (Piyasa Geneli) Tamamlandı:** BTC.D / Total Market Cap / Stablecoin.D — `market_regime.py` (CoinGecko `/global`), risk-on/risk-off + altseason yorumu, `GET /market/regime`, Dashboard rejim kartı. (CVD/L-S Ratio hâlâ taker-akış verisi gerektirir; kapsam dışı.)

### ✅ Adım 4 — Modül 3: Al-Sat Emir Yönetimi (Tamamlandı)
- ✅ `models/orders.py` — Pydantic şemaları (`OrderCreateResponse`, `OpenOrdersResponse`, `OrderHistoryResponse`, `OrderCancelResponse`, `PanicStopResponse`, `SwitchModeResponse`)
- ✅ `module3_orders.py` — Emir yönetimi
  - ✅ Market & Limit emir oluşturma
  - ✅ Açık emir takibi & işlem geçmişi
  - ✅ Simülasyon (Paper Trading) modu — $10k sanal USDT
  - ✅ Panic stop
  - ✅ Bakiye limiti / pre-trade risk kontrolü
  - ✅ Mod geçişi (paper ↔ live)
- ✅ `main.py` — `/api/v1/orders/*` endpoint'leri (6 adet)
- ✅ **Yeni Eklenen Backend Görevleri (Kullanıcı Talepleri):**
  - [x] Modül 2: Otomatik Seviye Hesaplayıcı (`trade_setup`: Entry, TP1, TP2, SL, R:R) — `get_trade_setup`, `GET /market/trade-setup`
  - [x] Modül 3: Akıllı Paket Emir Motoru (`POST /api/v1/orders/bracket`) — giriş + TP1(%50) + TP2(%50) + SL(%100), `bracket_id`
  - [x] Modül 3: Açık Emir Düzenleme Motoru (`PUT /api/v1/orders/{order_id}`) — `amend_order`, paper güncelle / live cancel-replace
  - [x] Modül 3: Dinamik Öneri Motoru (`GET /api/v1/orders/recommendations` & `/apply`) — `recommendations.py`, SL yakınlık/TP realizasyon tavsiyeleri
  - [x] Ayarlar Modülü: Çoklu coin & Watchlist, mod seçimi, risk parametreleri (`/api/v1/settings/*` & SQLite kalıcılığı) — `settings.py`, 5 endpoint, 6 test

### Adım 5 — Frontend Dashboard (HTML5/CSS3/JS)
- ✅ Dark mode tema (koyu kömür `#0d1117`) (`static/css/style.css`)
- ✅ Glassmorphism kartlar
- ✅ SVG candlestick grafikler (`app.js:loadChart`, 60sn yenileme)
- ✅ WebSocket canlı veri akışı (`/ws/live` endpoint + `app.js` WS istemci; polling fallback + 5sn reconnect)
- ✅ Toast bildirimleri (başarı/uyarı/hata)
- ✅ Sol menü & üst bar & alt bar + Panic Stop (Master Layout, GLOBAL_STANDARDS 3)
- ✅ 4 görünüm: Dashboard, Hesap (bakiye tablosu), Analiz (skor/gerekçe/uyarı), Emirler (oluştur/listele/iptal)
- ✅ `static/` StaticFiles mount; root `/` dashboard, `/api` bilgi endpoint'i
- ✅ **Yeni Eklenen Frontend Görevleri (Kullanıcı Talepleri):**
  - [x] Ana sayfadan erişilebilir **Kullanım Kılavuzu Sayfası / Görünümü** (Uygulamanın nasıl çalıştığı, modlar, göstergelerin yorumu, panic stop rehberi) — `view-guide` + sol menü/header linki
  - [x] Önemli noktalarda **Bağlamsal Info Düğmeleri (`ℹ️`)** (Portföy, mod, panic stop, bileşik puan, MTF, SMC, emir formu açıklamaları) — 7 nokta + glass popover
  - [x] **Ayarlar Ekranı (`⚙️ Ayarlar` Görünümü)**: Çoklu coin izleme listesi (Watchlist ekle/çıkar), mod seçimi, varsayılan sembol/timeframe, maks emir tutarı — sembol seçimi watchlist datalist'i ile entegre (`/settings/symbols` arama backend'de hazır)
  - [x] **İzleme Listesi (Watchlist) Global Arayüz Entegrasyonu**:
    - [x] Dashboard'a izleme listesindeki coin'leri gösteren **Aktif Koin Seçici** (tıklanabilir mini widget)
    - [x] Koin seçildiğinde Dashboard Canlı Fiyatı ve SVG mum grafiğinin seçilen koine dinamik geçmesi
    - [x] Analiz ve Emirler ekranlarındaki sembol girişlerinin izleme listesinden beslenen seçim (`datalist`) haline getirilmesi
    - [x] Dashboard'a izlenen tüm koinlerin anlık fiyat ve % değişimini özetleyen **Mini Watchlist Widget**
  - [x] **Akıllı Paket Emir Bileşeni**: Analiz motorundan otomatik seviye yükleme (Entry, TP1, TP2, SL, R:R), USDT tutar girişi, "🚀 Akıllı Emri İlet" tek tıkla paket iletim butonu — Emirler görünümünde
  - [x] **Açık Emir Düzenleme Modalı**: Açık emirler tablosunda "Düzenle" butonu, fiyat/miktar değiştirme modalı
  - [x] **Dinamik Öneri Motoru Kartları**: Canlı piyasa değişikliklerinde çıkan tavsiye kartları (`✖ Yoksay`) — Dashboard'da



### Adım 6 — Testler
- ❌ `tests/conftest.py` — Shared fixtures & KuCoin mock (henüz yok; mock'lar test dosyalarında yerel)
- ✅ `tests/test_module_1_account.py` (29 test)
- ✅ `tests/test_module_2_market.py` (8 test)
- ✅ `tests/test_module_2_indicators.py` (19 test)
- ✅ `tests/test_module_2_volume_levels.py` (10 test)
- ✅ `tests/test_module_2_phase2c.py` (10 test)
- ✅ `tests/test_module_2_structure.py` (8 test)
- ✅ `tests/test_module_2_analysis.py` (10 test)
- ✅ `tests/test_module_3_orders.py` (16 test)
- ✅ `tests/test_bracket_orders.py` (7 test)
- ✅ `tests/test_settings.py` (6 test)
- ✅ `tests/test_frontend.py` (8 servis testi)
- ✅ `tests/test_utils.py` (14 test — %100 utils coverage)
- ✅ `run_tests.sh` — Tek komut test koşturma ve coverage scripti (145/145 yeşil, %78 coverage)

### Adım 7 — Son Kontroller
### ✅ Adım 7 — Son Kontroller (Doğrulandı)
- ✅ Tüm endpoint'lerin Swagger dokümantasyonu doğrulandı (`/openapi.json` 200, 24 API path + 1 WS; `/docs` & `/redoc` 200)
- ✅ `.gitignore` doğrulandı (`.env`, `.venv/`, `__pycache__`, `test-reports/`, `logs/`, `*.db`); hassas dosya izlenmiyor
- ✅ Git commit disiplini uygulanıyor (Conventional Commits)

---

## 4. Kütlemler (Checklist)

### Modül 1 (Kodlama & Testler %100 Tamamlandı ✅)
- [x] `.env` okuma & yapılandırma (`config.py` — tüm alanlar okunuyor)
- [x] Zaman senkronizasyonu (`time_sync.check_time_sync`, 3sn drift kontrolü, canlı doğrulandı)
- [x] API anahtarı doğrulama ve kimlik bilgisi denetimi
- [x] Yetki kontrolü (Read/Trade/Withdraw denetimi ve güvenlik uyarısı)
- [x] Bakiye sorgulama (free/used/total) — `trade` + `main` hesapları birleştiriliyor
- [x] USDT karşılığı hesaplama — anlık ticker fiyatı + `portfolio_share_percent`
- [x] WebSocket bakiye aboneliği (`ccxt.pro.kucoin` ile arka planda canlı bakiye stream ve önbellek)
- [x] `/api/v1/account/status`
- [x] `/api/v1/account/balances`
- [x] `/api/v1/account/summary`
- [x] `/api/v1/account/test-connection`

> **Test Durumu:** `tests/test_module_1_account.py` → **29/29 test başarıyla geçiyor** (`./run_tests.sh` %100 yeşil). Tüm endpoint'ler ve yetki/websocket akışları doğrulandı.

### Modül 2 — Faz 2a: Çekirdek Piyasa Verisi & Temel İndikatörler (Kodlama & Testler %100 Tamamlandı ✅)
- [x] KuCoin Ticker & L2 Order Book veri akışı (`module2_market.py` — 24s stats, best bid/ask, spread, imbalance)
- [x] Rolling Ring Buffer (500 mum) & Repaint/Lookahead koruması (`confirmed_candle` flag)
- [x] Çekirdek Trend Katmanı: EMA (20/50/100/200), SMA (50/200), Golden/Death Cross (`indicators/trend.py`)
- [x] Çekirdek Momentum Katmanı: RSI 14 (Wilder), MACD (12, 26, 9) (`indicators/momentum.py`)
- [x] Çekirdek Volatilite Katmanı: ATR 14 (Wilder), Normalized ATR %, Dinamik Stop-Loss (`indicators/volatility.py`)
- [x] Faz 2a REST API Endpoint'leri:
  - [x] `/api/v1/market/ticker`
  - [x] `/api/v1/market/orderbook`
  - [x] `/api/v1/market/candles`
  - [x] `/api/v1/market/symbols`
  - [x] `/api/v1/market/analysis/indicators`

> **Modül 2 Faz 2a Test Durumu:** `tests/test_module_2_market.py` (8 test) + `tests/test_module_2_indicators.py` (Faz 2a çekirdek kısmı) → doğrulandı. Güncel proje geneli: **74/74 test %100 yeşil** (bkz. Faz 2b nihai durumu).

### Modül 2 — Faz 2b: İleri Düzey Çok Katmanlı Motor, SMC & Puanlama (Kodlama & Testler %100 Tamamlandı ✅)
- [x] İleri Trend Katmanı: Supertrend (10, 3.0), Ichimoku Kinko Hyo (9/26/52 Kumo), Parabolic SAR (0.02/0.20) (`indicators/trend.py`)
- [x] İleri Momentum & Güç: ADX 14 (Wilder), Aroon 25, Choppiness Index 14 (`indicators/strength.py`)
- [x] İleri Volatilite & Squeeze: Bollinger Bands (20, 2.0), Keltner Channels (EMA20, 1.5*ATR), BB-KC Squeeze (`indicators/volatility.py`)
- [x] Hacim & Sermaye Akışı: RVOL, OBV, VWAP, MFI 14, CMF 20, Volume Profile (POC/VAH/VAL) (`indicators/volume.py`)
- [x] Destek/Direnç Seviyeleri: Pivot Points, Önceki High/Low, Fibonacci Retracement, Donchian (`indicators/levels.py`)
- [x] Market Structure (SMC / Fiyat Hareketi): Lookahead-proof Swings, HH/HL/LH/LL, BOS, CHoCH, FVG, Order Block (`indicators/structure.py`)
- [x] Analiz ve Puanlama Motoru (`analysis/`):
  - [x] Feature Engine (`module2_market.py:_all_features` tüm katmanların birleştirilmesi)
  - [x] Composite Scoring Engine (`analysis/scoring_engine.py` — 0-100 Boğa/Ayı Bileşik Skoru, Hacim katkısı, Net Skor)
  - [x] False Signal & Risk Filtreleri (ADX zayıf trend, Choppiness range, BB-KC Squeeze uyarıları)
  - [x] İnsan Okunabilir Gerekçelendirme & Risk Uyarıları (Explainable AI: `reasons` ve `warnings`)
  - [x] Multi-Timeframe (MTF) Hiyerarşisi (`analysis/mtf_engine.py` — 4H Rejim → 1H Setup → 15m Tetikleyici)
- [x] Faz 2b REST API Endpoint'leri:
  - [x] `/api/v1/market/analysis/structure`
  - [x] `/api/v1/market/analysis/score`
  - [x] `/api/v1/market/analysis/mtf`

> **Modül 2 Nihai Test Durumu:** 55 Modül 2 testi (`market: 8`, `indicators: 19`, `volume_levels: 10`, `structure: 8`, `analysis: 10`). Proje genelinde **84/84 test %100 yeşil**.

### Modül 3 (Kodlama & Testler %100 Tamamlandı ✅)
- [x] Market emir oluşturma (M3-C02 — paper anında dolum / live ccxt)
- [x] Limit emir oluşturma (M3-C03 — açık kalır)
- [x] Açık emir takibi (M3-C04 — sembol filtreli listeleme)
- [x] Emir iptal etme (M3-C05 — tekil iptal)
- [x] Simülasyon/Paper Trading modu (M3-C07 — $10k sanal USDT, canlı fiyat eşleşmesi)
- [x] Panic stop (M3-C06 — tüm emirleri iptal + botu durdur)
- [x] Bakiye limiti kontrolü (M3-C01 — pre-trade risk: bakiye, min notional, bot durumu)
- [x] Mod geçişi (M3-C08 — paper ↔ live)
- [x] `/api/v1/orders/create`
- [x] `/api/v1/orders/open`
- [x] `/api/v1/orders/history`
- [x] `/api/v1/orders/{order_id}` (DELETE)
- [x] `/api/v1/orders/panic-stop`
- [x] `/api/v1/orders/switch-mode`

> **Modül 3 Test Durumu:** `tests/test_module_3_orders.py` → **16 test geçiyor** (M3-C01..C08 kapsandı). Paper trading akışı gerçek BTC/USDT fiyatıyla uçtan uca doğrulandı. Proje genelinde **100/100 test %100 yeşil**.

---

## 5. Standartlar

| Alan | Kurallar |
|------|----------|
| **Backend** | Python 3.14+, FastAPI, Uvicorn |
| **Borsa** | CCXT (async) |
| **Veri Analizi** | Pandas & NumPy |
| **Test** | Pytest + pytest-asyncio + pytest-cov |
| **Veritabanı** | SQLite (sqlite3/aiosqlite) |
| **UI** | Dark Mode, Inter/Outfit font, `#0d1117` |
| **API Yanıt** | `{ success, data, error, timestamp }` JSON envelope |
| **Git** | Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`) |
| **Test** | Her fonksiyon için en az 1 birim test, `tests/` klasöründe |

---

## 6. Geliştirme Sırası

```
[1] İskelet & requirements.txt  →  [2] Modül 1  →  [3] Modül 2  →  [4] Modül 3  →  [5] Frontend  →  [6] Testler  →  [7] Son Kontroller
```

Her adım öncekinin tamamlanmasını bekler. **Modül 1** uygulama için temel oluşturur — o bittiğinde diğer modüller de sırayla eklenir.

---

## 7. Doküman Değişiklik ve Tamamlanma Günlüğü (Change Log)

| Tarih / Saat | Yapılan Değişiklikler ve İşlem Özeti | Durum |
| :--- | :--- | :--- |
| **2026-09-17 21:20:00** | İlk workflow ve geliştirme fazları taslağı oluşturuldu. | Tamamlandı |
| **2026-09-17 21:22:13** | Dizin ağacına `install.sh`, `first_run.sh`, `run.sh`, `run_tests.sh`, `.env.example` eklendi. | Tamamlandı |
| **2026-09-17 21:35:00** | Review bulguları düzeltildi: `.env` durumu gerçeğe göre güncellendi, yanıltıcı checklist başlıkları düzeltildi, tamamlama göstergesi ve footer log eklendi. | Tamamlandı |
| **2026-09-17 22:06:00** | Rozet ayrımı (Tasarım %100 vs Kodlama %20) yapıldı, Mevcut Durum tablosu Coding AI ilerlemesiyle senkronlandı. | Onaylandı & Tamamlandı (%100) |
| **2026-09-17 22:50:00** | Modül 2 geliştirme planı ve checklist'i `crypto_indicators_coding_agent_reference.md` doğrultusunda 10 indikatör katmanı, SMC, Feature & Scoring Engine ve yeni API endpoint'leri ile genişletildi. | Onaylandı & Genişletildi (%100) |
| **2026-09-19 21:37:00** | Workflow gerçek proje durumuyla senkronlandı: Modül 1 çekirdeği çalışır ve **22/22 test geçer** hale geldi (test-connection/balances/summary endpoint hataları ve async kaynak sızıntısı giderildi). Başlık rozeti, Mevcut Durum tablosu, Adım 1 ve Modül 1 checklist'i kanıtlı biçimde güncellendi. Eksikler dürüstçe işaretlendi: WebSocket canlı bakiye ve API yetki (Read/Trade) denetimi henüz yok. | Güncellendi (Kanıta Dayalı) |
| **2026-09-19 22:00:00** | **Modül 1 Tamamlandı & Modül 2 Faz 2a/2b Ayrımı**: Coding AI tarafından WebSocket canlı bakiye stream ve API yetki (Read/Trade/Withdraw) denetimi tamamlandı. Toplam test sayısı 29'a yükseldi ve **29/29 birim test başarıyla geçti** (`run_tests.sh` %100 yeşil). Modül 1 checklist'i %100 tamamlandı. Modül 2 geliştirme planı kapsam riskini önlemek için Faz 2a (Çekirdek Veri & İndikatörler) ve Faz 2b (İleri SMC & Scoring) olarak bölümlendi. | **Modül 1 Tamamlandı (%100)** ✅ |
| **2026-09-19 22:52:00** | **Modül 2 Faz 2a Temel Veri Katmanı Doğrulandı**: Coding AI tarafından `module2_market.py` (ticker, L2 orderbook, ring buffer, repaint guard), `OrderBookResponse` modeli ve 4 API endpoint'i `/api/v1/market/{ticker,orderbook,candles,symbols}` yazıldı. 8 yeni birim test eklendi ve toplam **37/37 birim test başarıyla geçti** (`run_tests.sh` %100 yeşil). | **Faz 2a Veri Katmanı Tamamlandı ✅** |
| **2026-09-19 23:10:00** | **Modül 2 Faz 2a Çekirdek İndikatörler %100 Tamamlandı**: `indicators/trend.py`, `momentum.py`, `volatility.py` ve `/api/v1/market/analysis/indicators` endpoint'i yazıldı. Repaint guard (yalnızca confirmed kapanmış mumlar) ve warm-up (min 250 mum ile DEGRADED/OK data_quality) doğrulandı. 11 yeni birim test eklendi ve toplam **48/48 birim test başarıyla geçti** (`run_tests.sh` %100 yeşil). | **Faz 2a %100 Tamamlandı ✅** |
| **2026-09-19 23:25:00** | **Modül 2 Faz 2b SMC, Scoring ve MTF %100 Tamamlandı**: İleri trend, ADX/Aroon/Choppiness, BB-KC Squeeze, SMC (Swings, BOS, CHoCH, FVG, OB), 0-100 Bileşik Puanlama Motoru ve MTF (4H $\rightarrow$ 1H $\rightarrow$ 15m) tamamlandı. 3 yeni API (`/analysis/structure`, `/analysis/score`, `/analysis/mtf`) devreye alındı. 26 yeni birim test ile Modül 2 toplam 45 teste, proje genelinde **74/74 birim teste** ulaştı. | **Modül 2 Analiz Motoru Tamamlandı ✅** |
| **2026-09-19 23:33:00** | **Sıralı Adımlar checklist'i gerçek durumla işaretlendi**: Adım 2 (Modül 1) ve Adım 3 (Modül 2) alt maddeleri ✅/❌ ile işaretlendi; yazılmayan katmanlar (`volume.py`, `levels.py`, Katman 8-9 türev/piyasa-geneli) ve `analysis/filters.py`→scoring içine gömülü olarak dürüstçe belirtildi. Adım 6 test dosyaları mevcut/eksik olarak işaretlendi. Faz 2a/2b test sayıları dosya bazlı gerçek dağılıma göre (market 8, indicators 19, structure 8, analysis 10 = 45) düzeltildi. | Güncellendi (Kanıta Dayalı) ✅ |
| **2026-09-19 23:48:00** | **Modül 2 Hacim ve Destek/Direnç Seviyeleri Katmanları Tamamlandı**: `indicators/volume.py` (RVOL, OBV, VWAP, MFI, CMF, Volume Profile) ve `indicators/levels.py` (Pivot Points, önceki H/L, Fib retracement, Donchian) yazıldı; `scoring_engine.py` içine hacim katkısı entegre edildi. 10 yeni test (`test_module_2_volume_levels.py`) eklendi ve toplam test sayısı **84/84 birim teste** ulaştı (`run_tests.sh` %100 yeşil). | **Hacim & Seviyeler Tamamlandı ✅** |
| **2026-09-19 23:49:00** | **Modül 2 kapsam durumu dürüstleştirildi**: "Tüm katmanlar %100" ifadesi yanıltıcıydı; başlık rozeti ve Mevcut Durum tablosu düzeltildi. Spot analiz motoru tam (6/7 katman + scoring + MTF, 8 endpoint) ancak Katman 8 (Türev: OI/Funding/CVD), Katman 9 (Piyasa geneli: BTC.D) ve ek momentum indikatörleri (StochRSI/CCI/%R/ROC) kodda **yok** — kanıtla doğrulandı (`grep`) ve **Faz 2c** olarak ertelendi. | Güncellendi (Kanıta Dayalı) ⚠️ |
| **2026-09-20 00:01:00** | **Modül 3 (Al-Sat Emir Yönetimi) %100 Tamamlandı**: `module3_orders.py` yazıldı — Market/Limit emir, açık emir & geçmiş, tekil iptal, Panic Stop, Paper Trading motoru ($10k sanal USDT, canlı fiyat eşleşmesi), pre-trade risk (bakiye/min notional/bot durumu) ve paper↔live mod geçişi (M3-C01..C08). 6 REST endpoint (`/api/v1/orders/*`) eklendi (M3-C09). Varsayılan güvenli `paper` mod. 16 yeni test (`test_module_3_orders.py`) ile proje genelinde **100/100 birim teste** ulaşıldı; paper akışı gerçek BTC/USDT fiyatıyla uçtan uca doğrulandı. Backend (Modül 1-2-3) tamam. | **Modül 3 Tamamlandı (%100) ✅** |
| **2026-09-20 00:06:00** | **Modül 2 Faz 2c Tamamlandı**: Ek momentum osilatörleri (StochRSI 14, CCI 20, Williams %R 14, ROC 9) `momentum.py`'ye; Katman 8 türev veriler (Funding Rate + Open Interest, KuCoin Futures) yeni `indicators/derivatives.py`'ye eklendi (`include_derivatives` flag ile opsiyonel). 10 yeni test (`test_module_2_phase2c.py`) ile proje genelinde **110/110 birim teste** ulaşıldı; gerçek BTC/USDT + Futures verisiyle doğrulandı. Kalan tek kalem Katman 9 (piyasa-geneli, harici API gerektirir). | **Faz 2c Tamamlandı (%100) ✅** |
| **2026-09-20 00:16:00** | **Adım 5 Frontend Dashboard (temel sürüm) Tamamlandı**: `static/` altına dark glassmorphism tek-sayfa dashboard eklendi — Master Layout (header + sol menü + footer + Panic Stop), 4 görünüm (Ana Sayfa/Hesap/Analiz/Emirler), toast bildirimleri, 15sn REST polling. `main.py`'ye StaticFiles mount + root `/` dashboard + `/api` bilgi endpoint'i. 5 servis testi (`test_frontend.py`) ile proje genelinde **115/115 birim teste** ulaşıldı. Sonraki iterasyona bırakılan: SVG candlestick grafikler, WebSocket canlı akış (şu an polling). | **Frontend Temel Sürüm Tamamlandı ✅** |
| **2026-09-20 00:47:00** | **Frontend canlı akış + grafik & Script Senkronizasyonu**: `/ws/live` WebSocket endpoint (ticker+summary+mode push) ve SVG candlestick grafik (`loadChart`) eklendi; WS istemci polling fallback + 5sn reconnect ile (GLOBAL_STANDARDS 4.1). **Script denetimi (GLOBAL_STANDARDS 8.2/8.3):** `requirements.txt`'e eksik `requests` eklendi, `run.sh` dashboard linki + eski fallback mesajı düzeltildi, `run_tests.sh`'e coverage (pytest-cov) ölçümü eklendi. `install.sh`/`first_run.sh` güncel doğrulandı. 115/115 test, **%76 coverage**. | **Frontend Tam Sürüm + Scriptler Senkron ✅** |
| **2026-09-20 00:55:00** | **Yardımcı Fonksiyon Testleri (`tests/test_utils.py`) Tamamlandı**: `crypto.py` (fiyat/miktar formatlama hassasiyeti), `time_sync.py` (timestamp, drift kontrolü ve toleransı), `logger.py` fonksiyonları 14 yeni birim test ile %100 kapsama ulaştı. Proje genelinde **129/129 birim test %100 yeşil** geçti, genel test kapsamı **%77**'ye yükseldi. | **Yardımcı Testler Tamamlandı (%100) ✅** |
| **2026-09-20 00:56:00** | **crypto.py bug fix + Adım 7 Son Kontroller**: `format_price` içindeki `float.quantize` `AttributeError` düzeltildi (fonksiyon hiç çalışmıyordu; artık BTC 2 / SHIB 8 / default 4 basamak doğru). Adım 7 doğrulandı: Swagger `/openapi.json` (20 path), `/docs`, `/redoc` = 200; `.gitignore` hassas dosyaları koruyor, `.env`/`.venv` git'te izlenmiyor. | **Adım 7 Tamamlandı ✅** |
| **2026-09-20 01:05:00** | **Ayarlar, Çoklu Coin, Akıllı Paket Emir & Dinamik Öneri İş Akışı Eklendi**: Kullanıcı gereksinimleri doğrultusunda Adım 4 (Backend) ve Adım 5 (Frontend) kontrol listeleri güncellendi. Ayarlar görünümü (`⚙️ Ayarlar`), çoklu coin/Watchlist desteği, analiz seviyelerinden beslenen otomatik Bracket Order formu (Giriş+TP1+TP2+SL), açık emir düzenleme modalı ve canlı piyasaya göre akıllı güncelleme tavsiyeleri üreten Dinamik Öneri Motoru iş akışına eklendi. | **İş Akışı Genişletildi (%100) ✅** |
| **2026-09-20 01:06:00** | **Kullanım Kılavuzu & Bağlamsal Info Düğmeleri Tamamlandı (Kod)**: `static/index.html`'e Kullanım Kılavuzu görünümü (API kurulumu + withdraw güvenlik uyarısı, işlem modları, analiz göstergeleri, emir & panic rehberi) ve sol menü/header linki eklendi. 7 kritik noktaya (portföy/mod/panic/skor/MTF/SMC/emir) bağlamsal `ℹ️` info düğmesi + glass popover (`app.js` + `style.css`). 2 yeni frontend test ile proje genelinde **131/131 test %100 yeşil**. | **Kılavuz & Info Düğmeleri Tamamlandı ✅** |
| **2026-09-20 01:08:00** | **Ayarlar & Çoklu Coin (Watchlist) Tamamlandı**: `src/modules/settings.py` (`SettingsManager`) — SQLite kalıcılıklı ayarlar (watchlist, varsayılan mod/sembol/timeframe, risk parametreleri), sembol arama. 5 endpoint (`GET/POST /settings`, `GET /settings/symbols`, `POST/DELETE /settings/watchlist`). Frontend `⚙️ Ayarlar` görünümü (mod/sembol/tf/maks-emir formu + watchlist ekle/çıkar). 6 birim test (SQLite kalıcılık dahil) ile proje genelinde **137/137 test %100 yeşil**. | **Ayarlar & Watchlist Tamamlandı ✅** |
| **2026-09-20 01:22:00** | **Akıllı Paket Emir (Bracket Order) Tamamlandı**: Modül 2 `get_trade_setup` (ATR tabanlı Entry/SL/TP1/TP2/R:R, long+short) + `GET /market/trade-setup`. Modül 3 `create_bracket_order` (giriş market + TP1 %50 + TP2 %50 + SL %100 limit emirleri, `bracket_id`, risk/kâr hesabı) + `POST /orders/bracket`. Frontend "🚀 Akıllı Paket Emir" bileşeni (seviye hesapla → USDT gir → tek tık ilet). 8 yeni test ile proje genelinde **145/145 test %100 yeşil**; gerçek BTC/USDT verisiyle uçtan uca doğrulandı. | **Bracket Order Tamamlandı ✅** |
| **2026-09-20 12:38:00** | **Emir Düzenleme + Öneri Motoru + Watchlist Entegrasyonu Tamamlandı**: Modül 3 `amend_order` (`PUT /orders/{id}`, paper güncelle/live cancel-replace). Yeni `recommendations.py` `RecommendationEngine` (SL yakınlık uyarısı, TP realizasyon önerisi) + `GET /orders/recommendations`, `POST /orders/recommendations/apply`. Frontend: emir düzenleme modalı, tıklanabilir Mini Watchlist Widget (aktif coin geçişi + dinamik grafik), dinamik öneri kartları. 9 yeni test ile proje genelinde **153/153 test %100 yeşil**. Kalan: sembol girişlerini watchlist dropdown'a çevirme (sonraki iterasyon), Katman 9 (harici API). | **Emir Yönetimi Tam ✅** |
| **2026-09-20 16:17:00** | **Watchlist Sembol Entegrasyonu Tamamlandı**: Analiz, Emir ve Bracket sembol girişleri watchlist'ten beslenen `datalist` (`symbol-choices`) ile seçilebilir hale getirildi; watchlist değişiminde otomatik yenilenir. 1 yeni test ile **154/154 test %100 yeşil**. Watchlist global entegrasyonu tümüyle tamamlandı. Geriye yalnızca Katman 9 (piyasa-geneli, harici CoinGecko API onayı bekleyen) opsiyonel kalem kaldı. | **Watchlist Entegrasyonu Tam ✅** |
| **2026-09-20 16:40:00** | **Sub-15m (1m/3m/5m), Çoklu Piyasa (Spot/Margin/Futures) & Seviyeli Grafik Tamamlandı**: 15m altı zaman dilimi desteği (`1m`, `3m`, `5m`), KuCoin Futures USDT-M swap mum ve fonlama/OI veri entegrasyonu, spot/marjin/vadeli çoklu analiz ve analiz ekranı seviye bindirmeli (Entry/SL/TP1/TP2/Liq) SVG mum grafiği 11 yeni test (`test_market_types.py`, `test_frontend.py`) ile doğrulanarak tamamlandı (toplam 165/165 test %100 yeşil, %80 coverage). | **Çoklu Piyasa Tamamlandı ✅** |
| **2026-09-20 16:45:00** | **Sade Dil Piyasa Özeti ve 4-Boyutlu Eğitici Gerekçelendirme Motoru Tamamlandı**: Analiz ekranındaki teknik jargon sadeleştirildi; en üste sade durum, eylem tavsiyesi ve risk seviyesi kartı eklendi. Gerekçeler ve uyarılar her biri için "İndikatör", "Neden Oldu?", "Neyi Gösterir?", "Neye Sebep Olur?" ve "Korunma Tavsiyesi" alanlarını içeren eğitici kartlarla donatıldı. Katman 9 (CoinGecko BTC.D/Total MCap/Stablecoin.D) tamamlandı (toplam 169/169 test %100 yeşil, %81 coverage). | **Eğitici Analiz Tamamlandı ✅** |
| **2026-09-20 16:51:00** | **Katman 9 (Piyasa Geneli Rejim) Tamamlandı**: `src/modules/market_regime.py` (`MarketRegime`) — CoinGecko `/api/v3/global` ile BTC Dominance, Total Market Cap, Stablecoin Dominance; risk-on/risk-off ve altseason yorumu. `GET /market/regime` endpoint (asyncio.to_thread), Dashboard'a piyasa rejimi kartı + info düğmesi. 4 birim test (CoinGecko mock'lu) + 1 frontend test ile proje genelinde **174/174 test %100 yeşil**; gerçek veriyle doğrulandı (BTC.D %58.95, RISK_OFF). **MODULE_2_SPEC'teki 10 analiz katmanının tamamı artık kodlandı**. | **Katman 9 Tamamlandı — Analiz Motoru Tam ✅** |
| **2026-09-20 17:15:00** | **Yan Yana 4-Sütunlu Eğitici Gerekçe Tablosu Tamamlandı**: Analiz ekranında listelenen gerekçeler "İndikatör & Sinyal", "Neden Oldu? (Koşul)", "İndikatör Neyi Gösterir?", "Neye Sebep Olur?" başlıklarıyla 4 sütunlu yan yana tablo düzenine kavuşturuldu; `why`, `shows`, `causes` anahtarları ile tam eşleşme sağlandı. (Toplam 174/174 test %100 yeşil, %81 coverage). | **Eğitici Tablo Düzeni Tamamlandı ✅** |
| **2026-09-20 17:35:00** | **Hata Raporlama ve Sorun Takip Sistemi Devreye Alındı & Hata #1 Çözüldü**: Kullanıcı talebiyle bağımsız Hata Raporlama bölümü (`#view-issues`), SQLite kalıcı veri tablosu (`bug_reports`), REST API (`/issues`, `/system/diagnostics`) ve teşhis log konsolu kodlandı. Kullanıcının bildirdiği 1. Hata (Analiz ekranındaki koin combo'sunda yalnızca BTC olması) sisteme tohumlandı ve çözüldü: gerçek açılır kutu (`<select id="analysis-symbol-select">`), Watchlist + Popüler 20 KuCoin çifti optgroup'ları ve tek tıkla analiz yapan hızlı koin çipleri (`quick-chips`) eklendi. (6 yeni test, toplam 180/180 test %100 yeşil, %81 coverage). | **Hata Raporlama ve Koin Combo Tamamlandı ✅** |
| **2026-09-20 18:47:00** | **Hata #9 Çözüldü (Dashboard "Yükleniyor"da Takılma)**: Kullanıcının bildirdiği hata — LIVE modda ana sayfada piyasa geneli rejim ve izleme listesi widget'larının "Yükleniyor"da kalması. Kök neden: `apiGet`/`apiSend` `fetch` veya geçersiz-JSON yanıtında **throw** ediyordu; `refreshDashboard` sıralı `await` kullandığından tek başarısız çağrı (LIVE ticker hatası veya CoinGecko rate-limit) sonraki widget'ları durduruyordu. Çözüm: `apiGet`/`apiSend` `try/catch` + `{success:false,error}` envelope; `refreshDashboard` `Promise.allSettled` ile widget izolasyonu; `loadMiniWatchlist` başarısız/boş durumda açık mesaj gösteriyor. 1 regresyon testi (`test_api_helpers_are_resilient`), toplam **182/182 test %100 yeşil**. | **Hata #9 Çözüldü ✅** |
| **2026-09-20 18:55:00** | **Spot/Margin/Futures Emir Desteği + Açık Emirde Piyasa Türü Gösterimi**: Kullanıcı talebiyle emir verme spot dışında **margin ve futures** piyasalarını da destekliyor. `create_order` `market_type` (spot/margin/futures) parametresi + doğrulama aldı; canlı modda margin `cross` marginMode ile spot uç noktasından, futures ise ayrı `kucoinfutures` borsasından iletiliyor. `get_open_orders` artık spot(+margin) ve futures açık emirlerini **birleştirip her emri `market_type` ile etiketliyor** (KuCoin `tradeType=MARGIN_TRADE` tespiti). Frontend: emir formuna piyasa türü seçici, açık emirler tablosuna **Piyasa kolonu** ve renkli rozetler (spot/margin/futures). `close()` futures borsasını da kapatıyor. 6 yeni test, toplam **188/188 test %100 yeşil**. | **Çoklu Piyasa Emir Tamamlandı ✅** |
| **2026-09-20 19:19:00** | **Akıllı Paket Emirde Spot/Margin/Futures + Ayarlar Kalıcılık Hatası Çözüldü**: (1) `create_bracket_order` `market_type` parametresi aldı; seçilen tür pakete ve tüm bacaklara (giriş/TP1/TP2/SL) yayılıyor, geçersiz tür reddediliyor. `BracketOrderRequest.market_type` eklendi; frontend Akıllı Paket formuna piyasa türü seçici geldi, `trade-setup` ve `submit` çağrıları market_type gönderiyor. (2) **Ayarlar kaydetme hatası çözüldü** — kullanıcı "kaydedildi diyor ama kaydetmiyor" bildirdi. Kök neden: `SettingsManager.save()` her çağrıda `DEFAULT_SETTINGS`'ten başlayıp yalnızca gelen alanları yazıyordu; kısmi güncelleme (ör. yalnızca `default_mode`) `watchlist`/`default_symbol` gibi alanları **DEFAULT'a sıfırlıyordu**. Düzeltme: `save()` artık diskteki mevcut ayarın (`_read_raw`) üzerine merge ediyor, `risk` iç içe dict'i derin birleştiriyor. 5 yeni test (bracket market_type, ayarlar kısmi-güncelleme regresyonu), toplam **193/193 test %100 yeşil**. | **Çoklu Piyasa Paket Emir + Ayarlar Düzeltmesi ✅** |
| **2026-09-20 19:33:00** | **Futures Sembol Formatı Hatası Çözüldü**: Kullanıcı futures paket emrinde `kucoinfutures does not have market symbol PEPE/USDT` hatası aldı. KuCoin Futures dokümanı (docs-new/rest/futures-trading) incelendi: perpetual sözleşmeler **USDT-Margined** (`settle=USDT`) formatında, ccxt'te `BASE/QUOTE:SETTLE` biçiminde (spot `PEPE/USDT` → futures `PEPE/USDT:USDT`). Kod spot sembolünü doğrudan futures borsasına gönderdiğinden hata alınıyordu. Düzeltme: `_normalize_symbol()` futures için `:SETTLE` eki ekliyor ve borsa markets'ında geçerliliği doğruluyor; `_create_live_order` ve `get_open_orders` futures sembolünü normalize ediyor; dönen data'ya `venue_symbol` eklendi. Gerçek `kucoinfutures` markets ile doğrulandı (PEPE/BTC/ETH → `.../USDT:USDT` geçerli). 2 yeni test, toplam **195/195 test %100 yeşil**. | **Futures Sembol Düzeltmesi ✅** |
| **2026-09-20 19:37:00** | **Futures Margin Modu Uyuşmazlığı (330005) Çözüldü**: Kullanıcı futures paket emrinde `330005 - The order's margin mode does not match the selected one` hatası aldı. KuCoin Futures'ta emrin margin modu (cross/isolated) sembolün hesapta ayarlı moduyla eşleşmeli; kod hiç `marginMode` göndermiyordu (ccxt issue #25592 ile aynı durum). Düzeltme: `_create_live_order` futures için `marginMode` (varsayılan `cross`) + opsiyonel `leverage` gönderiyor; **330005 alınırsa diğer modla (isolated) otomatik bir kez daha deniyor**. `create_order`/`create_bracket_order` `margin_mode`+`leverage` parametreleri, `OrderCreateRequest`/`BracketOrderRequest` yeni alanlar aldı; dönen data kullanılan `margin_mode`'u içeriyor. 1 yeni test (330005 fallback), toplam **196/196 test %100 yeşil**. | **Futures Margin Modu Düzeltmesi ✅** |
| **2026-09-20 19:46:00** | **Bakiyelere Tüm Hesap Tipleri Dahil Edildi (Spot/Funding/Margin/Futures)**: Kullanıcı bakiyelerde futures ve margin hesaplarının görünmediğini bildirdi. Önceden yalnızca `trade` (spot) + `main` (funding) çekiliyordu. `get_balances` artık spot uç noktasından `trade`/`main`/`margin`, ayrıca `kucoinfutures` teminat cüzdanını çekip varlık bazında birleştiriyor; her varlığa hangi hesaplarda bulunduğunu gösteren `accounts` etiketi eklendi. `connect()` futures borsasını da kuruyor, `close()` kapatıyor. Frontend bakiye tablosuna **Hesap kolonu** + renkli rozetler (Spot/Funding/Margin/Futures) geldi. 2 yeni test (futures+margin bakiye birleşimi, frontend Hesap kolonu), toplam **198/198 test %100 yeşil**. | **Tüm Hesap Tipleri Bakiye ✅** |
| **2026-09-21 13:32:00** | **Bakiyelerde Hesap Bazlı Kırılım**: Kullanıcı "toplam bakiye yeterli değil, her hesap türünde ne kadar para olduğunu bilmem lazım" dedi. `get_balances` artık `per_account` ile her hesap için ayrı miktar topluyor ve `account_breakdown` listesi döndürüyor (her hesap için `account`, `total_usdt`, `assets`). `get_summary` eklendi `total_by_account` field'ı. `module1_account.py` `per_account`, `account_breakdown`, `_price` helper ekledi, response'a `accounts` field'ı eklendi. 1 test güncellendi (mock'a `accounts` eklendi), toplam **198/198 test %100 yeşil**. | **Hesap Bazlı Bakiye Kırılımı ✅** |
| **2026-09-21 21:30:00** | **Açık Emirlerde Anlık Fiyat & Fiyat Farkı Gösterimi (Analiz & Geliştirme)**: Kullanıcı talebi: "emirler ekranında açık emirler için anlık fiyat bilgisi gösterecek şekilde geliştirme yap". (1) Backend: `KuCoinOrders.get_open_orders` içinde `_attach_current_prices` metodu yazıldı; sembol ve piyasa türüne (spot/margin/futures) göre KuCoin'den anlık piyasa fiyatı (`current_price`), fiyat farkı (`price_diff`) ve yüzde farkı (`price_diff_percent`) hesaplanıp emir nesnelerine eklendi. Ön bellek (cache) ile aynı sembol için mükerrer API sorguları engellendi. (2) Frontend: Açık Emirler tablosuna **"Emir Fiyatı"**, **"Anlık Fiyat"** ve renkli **"Fark (%)"** (diff-badge) kolonları eklendi. Tablo kartı başlığına tek tıkla canlı fiyatları yenileyen **"🔄 Anlık Yenile"** butonu (`#btn-refresh-orders`) konuldu. Dashboard periyodik yenileme döngüsüne emirler ekranı aktifken otomatik yenileme entegre edildi. 4 yeni birim & UI testi eklendi; toplam **202/202 test %100 yeşil, %81 coverage**. | **Açık Emirlerde Anlık Fiyat Tamamlandı ✅** |
| **2026-09-21 21:42:00** | **Giriş Fiyatları, Stop Fiyatları & Açık Pozisyonlar Paneli (Analiz & Geliştirme)**: Kullanıcı talebi: "giriş fiyatlarımızı ve stop fiyatlarımızıda görebilir miyiz?". (1) Backend: `KuCoinOrders` içine `paper_positions` takip motoru ve `get_positions()` metodu eklendi. KuCoin Futures'ta canlı `fetch_positions()`, Paper'da ise bracket ve market emirlerinden üretilen pozisyonlar; `entry_price`, `current_price`, `stop_loss_price`, `tp1_price`, `tp2_price`, `unrealized_pnl`, `pnl_percent` ve `stop_distance_percent` ile hesaplanarak `/api/v1/orders/positions` endpoint'i üzerinden sunuldu. Açık emirler listesine her emrin bağlı olduğu `entry_price`, `stop_loss_price`, `bracket_leg` (🎯 TP1, 🎯 TP2, 🛑 SL, 🚀 Giriş) ve stop mesafesi iliştirildi. (2) Frontend: Emirler ekranına **"🏷️ Açık Pozisyonlar (Aktif İşlemler)"** tablosu ve açık emirler tablosuna **"Rol"**, **"Giriş Fiyatı"** ve **"Stop Fiyatı"** sütunları eklendi. Renkli `.leg-badge` ve `.pnl-badge` rozetleri ile canlı PnL gösterimi sağlandı. 3 yeni test eklendi; toplam **205/205 test %100 yeşil, %80 coverage**. | **Giriş, Stop Fiyatları & Pozisyonlar Tamamlandı ✅** |
| **2026-09-23 19:41:00** | **Kar/Zarar (P&L) Raporu — Emir Geçmişinden Hesaplama**: Kullanıcı talebi: "order history çekip kar zarar hesabı yapar mısın? Ayrı bir başlık altında göster." Backend: `KuCoinOrders.get_pnl_report()` emir geçmişindeki dolan emirleri sembol bazında **ortalama maliyet (average cost)** yöntemiyle işleyip gerçekleşen (realize) kar/zararı hesaplıyor; komisyonlar düşülüyor, açık kalan pozisyon miktarı (`open_qty`) raporlanıyor. `PnLReportResponse` modeli + `GET /api/v1/orders/pnl` endpoint eklendi. Frontend: ayrı **"💰 Kar / Zarar"** navigasyon menüsü ve görünümü; toplam realize K/Z, komisyon ve hacim özet kartları (yeşil/kırmızı) + sembol bazlı tablo (realize K/Z, alış/satış sayısı, komisyon, hacim, açık miktar) + info düğmesi. 5 yeni test (4 P&L hesap: kar/zarar/açık-emir-hariç/komisyon + 1 frontend); datalist sayacı 3→4 güncellendi. Toplam **210/210 test %100 yeşil**. | **Kar/Zarar Raporu Tamamlandı ✅** |









