# KuCoin Al-Sat Botu — Workflow & Geliştirme Planı

> **Tasarım & Spesifikasyon Durumu:** %100 (Onaylandı & Genişletildi ✅) | **Kodlama & Test Durumu:** Modül 1 çekirdeği çalışıyor, 22/22 test geçiyor ✅ (WebSocket/yetki denetimi eksik) | **Son Güncelleme:** 2026-09-19 21:37:00 (+03:00)

---

## 1. Mevcut Durum

| Öğe | Durum |
|-----|-------|
| Tasarım Dokümantasyonu | ✅ Tamamlandı (`docs/`) |
| `.env` Yapılandırma Dosyası | ✅ Oluşturuldu (Kök dizinde mevcut) |
| Sanal Ortam & Yönetim Scriptleri | ✅ Tamamlandı (`install.sh`, `first_run.sh`, `run.sh`, `run_tests.sh`) |
| `requirements.txt` | ✅ Güncellendi (`aiosqlite` dahil) & Sanal ortama kuruldu |
| Proje İskeleti (`src/`) | ✅ Oluşturuldu (`config`, `database`, `utils`, `models`, `modules/module1_account`) |
| Modül 1 Kaynak Kodu (`module1_account.py`) | ✅ Çekirdek çalışıyor (bağlantı, bakiye, portföy özeti, 4 endpoint) |
| Modül 1 Testleri (`test_module_1_account.py`) | ✅ 22/22 test geçiyor (`run_tests.sh` yeşil) |
| Modül 1 — Eksik Alt Özellikler | ⏳ WebSocket canlı bakiye aboneliği, API yetki (Read/Trade) denetimi, `portfolio_share_percent` dışı ince ayarlar |
| Modül 2 & Modül 3 | ❌ Kodlama başlamadı (`module2_market.py`, `module3_orders.py` yok) |


---

## 2. Proje Yapısı

> **Not:** Aşağıdaki ağaç **hedef (nihai) yapıdır**. Şu an fiilen mevcut olanlar: `src/config.py`, `src/database.py`, `src/main.py`, `src/utils/*`, `src/models/*`, `src/modules/module1_account.py` ve `tests/test_module_1_account.py`. Modül 2/3 dosyaları, `conftest.py`, `test_module_2/3`, `test_utils.py` ve `indicators/`, `analysis/` dizinleri henüz oluşturulmadı.

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

### Modül 1 (Çekirdek Çalışıyor ✅ / Bazı Alt Özellikler Eksik ⏳)
- [x] `.env` okuma & yapılandırma (`config.py` — tüm alanlar okunuyor)
- [x] Zaman senkronizasyonu (`time_sync.check_time_sync`, 3sn drift kontrolü, canlı doğrulandı)
- [ ] API anahtarı doğrulama (HMAC-SHA256) — *ccxt otomatik imzalıyor; ayrı imza denetimi eklenmedi*
- [ ] Yetki kontrolü (Read/Trade) — *permission audit henüz yok*
- [x] Bakiye sorgulama (free/used/total) — `trade` + `main` hesapları birleştiriliyor
- [x] USDT karşılığı hesaplama — anlık ticker fiyatı + `portfolio_share_percent`
- [ ] WebSocket bakiye aboneliği — *henüz yok (REST çalışıyor)*
- [x] `/api/v1/account/status`
- [x] `/api/v1/account/balances`
- [x] `/api/v1/account/summary`
- [x] `/api/v1/account/test-connection`

> **Test Durumu:** `tests/test_module_1_account.py` → **22/22 test geçiyor** (`./run_tests.sh` yeşil). Endpoint'ler canlı KuCoin hesabına karşı doğrulandı (bakiye başarıyla çekildi).

### Modül 2 (Tasarım Genişletildi / Kodlama Bekliyor ⏳)
- [ ] KuCoin Ticker & L2 Order Book veri akışı (`module2_market.py`)
- [ ] Rolling Ring Buffer (300-500 mum) & Repaint koruması (`confirmed_candle`)
- [ ] Modüler İndikatör Katmanları (`indicators/`):
  - [ ] Trend Katmanı: EMA (20/50/100/200), SMA, Supertrend, Ichimoku, Parabolic SAR
  - [ ] Momentum Katmanı: RSI, StochRSI, MACD, CCI, Williams %R, ROC
  - [ ] Trend Gücü: ADX, Aroon, Choppiness Index
  - [ ] Hacim ve Akış: RVOL, OBV, VWAP, AVWAP, MFI, CMF, Volume Profile (POC/VAH/VAL)
  - [ ] Volatilite: ATR, Bollinger Bands, Keltner Channels, BB-KC Squeeze
  - [ ] Seviyeler: Pivot Points, PDH/PDL, Fibonacci Retracement, Donchian
  - [ ] Fiyat Hareketi / SMC: Swing tespiti (lookahead-proof), HH/HL/LH/LL, BOS, CHoCH, FVG, Order Block
- [ ] Analiz ve Puanlama Motoru (`analysis/`):
  - [ ] Feature Engine (Normalize JSON özellik seti)
  - [ ] Composite Scoring Engine (0-100 Boğa/Ayı Skoru)
  - [ ] False Signal & Risk Filtreleri (Düşük Hacim, Range Trap, Overextended)
  - [ ] İnsan Okunabilir Gerekçelendirme & Risk Uyarıları (Explainable AI)
  - [ ] Multi-Timeframe (MTF) Hiyerarşisi (4H Rejim → 1H Setup → 15m Tetikleyici)
- [ ] Modül 2 REST API Endpoint'leri:
  - [ ] `/api/v1/market/ticker`
  - [ ] `/api/v1/market/orderbook`
  - [ ] `/api/v1/market/candles`
  - [ ] `/api/v1/market/symbols`
  - [ ] `/api/v1/market/analysis/indicators`
  - [ ] `/api/v1/market/analysis/structure`
  - [ ] `/api/v1/market/analysis/score`
  - [ ] `/api/v1/market/analysis/mtf`

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


