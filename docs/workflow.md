# KuCoin Al-Sat Botu — Workflow & Geliştirme Planı

> **Tasarım & Spesifikasyon Durumu:** %100 (Onaylandı & Genişletildi ✅) | **Kodlama & Test Durumu:** Modül 1 & Modül 2 Analiz Motoru %100 Tamamlandı (74/74 Test Geçiyor ✅) | **Son Güncelleme:** 2026-09-19 23:25:00 (+03:00)

---

## 1. Mevcut Durum

| Öğe | Durum |
|-----|-------|
| Tasarım Dokümantasyonu | ✅ Tamamlandı (`docs/`) |
| `.env` Yapılandırma Dosyası | ✅ Oluşturuldu (Kök dizinde mevcut) |
| Sanal Ortam & Yönetim Scriptleri | ✅ Tamamlandı (`install.sh`, `first_run.sh`, `run.sh`, `run_tests.sh`) |
| `requirements.txt` | ✅ Güncellendi (`aiosqlite` dahil) & Sanal ortama kuruldu |
| Proje İskeleti (`src/`) | ✅ Oluşturuldu (`config`, `database`, `utils`, `models`, `modules`, `indicators`, `analysis`) |
| Modül 1 (Hesap & Bağlantı) | ✅ **%100 Tamamlandı** (Bağlantı, bakiye, portföy payı, yetki denetimi, WebSocket stream) — 29 test |
| Modül 2 — Faz 2a (Veri & Çekirdek İndikatörler) | ✅ **%100 Tamamlandı** (Ticker, L2 Order Book, Ring Buffer, Repaint Guard, Trend, Momentum, Volatilite, 5 REST endpoint'i) — 19 test |
| Modül 2 — Faz 2b (İleri SMC, Scoring & MTF) | ✅ **%100 Tamamlandı** (Supertrend, Ichimoku, Parabolic SAR, ADX, Aroon, Choppiness, Squeeze, SMC Swings/BOS/CHoCH/FVG/OB, 0-100 Puanlama Motoru, MTF Hiyerarşisi, 3 REST endpoint'i) — 26 test |
| Modül 3 (Emir Yönetimi & Simülasyon) | ⏳ Tasarım %100 hazır; Modül 2 analiz motoru üzerine başlanacak |
| Toplam Birim Test Durumu | ✅ **74/74 test başarıyla geçiyor** (`run_tests.sh` %100 yeşil) |


---

## 2. Proje Yapısı

> **Not:** Aşağıdaki ağaç **hedef (nihai) yapıdır**. Şu an fiilen mevcut olanlar: `src/config.py`, `src/database.py`, `src/main.py`, `src/utils/*`, `src/models/*`, `src/modules/module1_account.py`, `src/modules/module2_market.py`, `src/modules/indicators/{trend,momentum,strength,volatility,structure}.py`, `src/modules/analysis/{scoring_engine,mtf_engine}.py` ve `tests/test_module_1_account.py`, `tests/test_module_2_market.py`, `tests/test_module_2_indicators.py`, `tests/test_module_2_structure.py`, `tests/test_module_2_analysis.py`. Henüz oluşturulmayanlar: `module3_orders.py`, `indicators/volume.py`, `indicators/levels.py`, `analysis/feature_engine.py`, `analysis/filters.py`, `conftest.py`, `test_module_3_orders.py`, `test_utils.py` ve türev/piyasa-geneli (Katman 8-9) katmanları.

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

### Adım 2 — Modül 1: KuCoin Bağlantısı & Hesap Durumu
- `config.py` — `.env` okuma, yapılandırma
- `utils/logger.py` — Logging ayarları
- `utils/time_sync.py` — KuCoin zaman senkronizasyonu
- `models/account.py` — Pydantic şemaları (`ConnectionStatusResponse`, `AccountBalancesResponse`, `PortfolioSummaryResponse`, `TestConnectionResponse`)
- `module1_account.py` — KuCoin API entegrasyonu
  - Bağlantı doğrulama (HMAC-SHA256)
  - Yetki kontrolü (Read/Trade)
  - Bakiye sorgulama (free/used/total)
  - USDT karşılığı hesaplama
  - WebSocket bakiye aboneliği
- `main.py` — `/api/v1/account/*` endpoint'leri

### Adım 3 — Modül 2: Çok Katmanlı Piyasa Verileri & Analiz Motoru
- `models/market.py` — Pydantic veri sözleşmeleri (`TickerData`, `Candle`, `IndicatorLayersData`, `MarketStructureData`, `SignalEvaluation`, `MTFAnalysisResponse`)
- `module2_market.py` — Ticker, L2 Derinlik, OHLCV verisi & Ring Buffer (300-500 mum)
- `indicators/` — Modüler indikatör katmanları:
  - `trend.py` (EMA 20/50/100/200, SMA, Supertrend, Ichimoku, SAR)
  - `momentum.py` (RSI, StochRSI, MACD, CCI, %R, ROC)
  - `strength.py` (ADX, Aroon, Choppiness Index)
  - `volume.py` (RVOL, OBV, VWAP, Anchored VWAP, MFI, CMF, Volume Profile)
  - `volatility.py` (ATR, Bollinger Bands, Keltner Channels, Squeeze)
  - `levels.py` (Pivot Points, PDH/PDL, Fibonacci, Donchian)
  - `structure.py` (Swing High/Low, HH/HL/LH/LL, BOS, CHoCH, FVG, Order Block)
- `analysis/` — Analiz motoru ve strateji:
  - `feature_engine.py` (Normalize özellik vektörü çıkarımı)
  - `scoring_engine.py` (0-100 Bileşik Puanlama & İnsan Okunabilir Gerekçelendirme)
  - `filters.py` (Düşük Hacim, Düşük ADX, Overextended, MTF çelişki filtreleri)
  - `mtf_engine.py` (4H Rejim → 1H Setup → 15m Tetikleyici)
- `main.py` & `routes/market.py` — `/api/v1/market/*` endpoint'leri

### Adım 4 — Modül 3: Al-Sat Emir Yönetimi
- `models/orders.py` — Pydantic şemaları (`OrderCreateResponse`, `OpenOrdersResponse`, `OrderHistoryResponse`, `OrderCancelResponse`, `PanicStopResponse`, `SwitchModeResponse`)
- `module3_orders.py` — Emir yönetimi
  - Market & Limit emir oluşturma
  - Açık emir takibi
  - Simülasyon (Paper Trading) modu
  - Panic stop
  - Bakiye limiti kontrolü
- `main.py` — `/api/v1/orders/*` endpoint'leri

### Adım 5 — Frontend Dashboard (HTML5/CSS3/JS)
- Dark mode tema (koyu kömür `#0d1117`)
- Glassmorphism kartlar
- SVG candlestick grafikler
- WebSocket canlı veri akışı
- Toast bildirimleri (başarı/uyarı/hata)
- Sol menü & üst bar & alt bar (GLOBAL_STANDARDS.md)

### Adım 6 — Testler
- `tests/conftest.py` — Shared fixtures & KuCoin mock
- `tests/test_module_1_account.py`
- `tests/test_module_2_market.py`
- `tests/test_module_3_orders.py`
- `tests/test_utils.py`
- `run_tests.sh` — Tek komut test koşturma scripti

### Adım 7 — Son Kontroller
- Tüm endpoint'lerin Swagger dokümantasyonu doğrulanması
- `.gitignore` güncellenmesi
- İlk Git commit (`feat: initial project setup`)

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

> **Modül 2 Test Durumu:** `tests/test_module_2_market.py` (8 test) + `tests/test_module_2_indicators.py` (11 test) → **19/19 test geçiyor**. Toplam proje genelinde **48/48 test %100 yeşil**.

### Modül 2 — Faz 2b: İleri Düzey Çok Katmanlı Motor, SMC & Puanlama (Kodlama & Testler %100 Tamamlandı ✅)
- [x] İleri Trend Katmanı: Supertrend (10, 3.0), Ichimoku Kinko Hyo (9/26/52 Kumo), Parabolic SAR (0.02/0.20) (`indicators/trend.py`)
- [x] İleri Momentum & Güç: ADX 14 (Wilder), Aroon 25, Choppiness Index 14 (`indicators/strength.py`)
- [x] İleri Volatilite & Squeeze: Bollinger Bands (20, 2.0), Keltner Channels (EMA20, 1.5*ATR), BB-KC Squeeze (`indicators/volatility.py`)
- [x] Market Structure (SMC / Fiyat Hareketi): Lookahead-proof Swings, HH/HL/LH/LL, BOS, CHoCH, FVG, Order Block (`indicators/structure.py`)
- [x] Analiz ve Puanlama Motoru (`analysis/`):
  - [x] Feature Engine (`module2_market.py:_all_features` tüm katmanların birleştirilmesi)
  - [x] Composite Scoring Engine (`analysis/scoring_engine.py` — 0-100 Boğa/Ayı Bileşik Skoru, Net Skor)
  - [x] False Signal & Risk Filtreleri (ADX zayıf trend, Choppiness range, BB-KC Squeeze uyarıları)
  - [x] İnsan Okunabilir Gerekçelendirme & Risk Uyarıları (Explainable AI: `reasons` ve `warnings`)
  - [x] Multi-Timeframe (MTF) Hiyerarşisi (`analysis/mtf_engine.py` — 4H Rejim → 1H Setup → 15m Tetikleyici)
- [x] Faz 2b REST API Endpoint'leri:
  - [x] `/api/v1/market/analysis/structure`
  - [x] `/api/v1/market/analysis/score`
  - [x] `/api/v1/market/analysis/mtf`

> **Modül 2 Nihai Test Durumu:** 45 Modül 2 testi (`market: 8`, `indicators: 19`, `structure: 8`, `analysis: 10`). Proje genelinde **74/74 test %100 yeşil**.

### Modül 3 (Tasarım Hazır / Kodlama Bekliyor ⏳)
- [ ] Market emir oluşturma
- [ ] Limit emir oluşturma
- [ ] Açık emir takibi
- [ ] Emir iptal etme
- [ ] Simülasyon/Paper Trading modu
- [ ] Panic stop
- [ ] Bakiye limiti kontrolü
- [ ] `/api/v1/orders/create`
- [ ] `/api/v1/orders/open`
- [ ] `/api/v1/orders/history`
- [ ] `/api/v1/orders/{order_id}` (DELETE)
- [ ] `/api/v1/orders/panic-stop`
- [ ] `/api/v1/orders/switch-mode`

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


