# KuCoin Al-Sat Botu — Workflow & Geliştirme Planı

> **Tamamlanma Durumu:** %100 (Tasarım ve Planlama Fazı) | **Son Güncelleme:** 2026-09-17 21:35:00 (+03:00) | **Onay Durumu:** Kullanıcı Tarafından Onaylandı ✅

---

## 1. Mevcut Durum

| Öğe | Durum |
|-----|-------|
| Tasarım Dokümantasyonu | ✅ Tamamlandı (`docs/`) |
| `.env` Yapılandırma Dosyası | ✅ Oluşturuldu (Kök dizinde mevcut) |
| Sanal Ortam & Yönetim Scriptleri | ✅ Tamamlandı (`install.sh`, `first_run.sh`, `run.sh`, `run_tests.sh`) |
| `requirements.txt` | ✅ Oluşturuldu & Sanal ortama kuruldu |
| Proje İskeleti (`src/`) | ⏳ Kodlama fazında oluşturulacak |
| Kaynak Kod | ⏳ Kodlama fazında yazılacak |
| Test Dosyaları (`tests/`) | ⏳ Kodlama fazında eklenecek |

---

## 2. Proje Yapısı

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

### ⏳ Adım 1 — Proje İskeleti & Ortam Hazırlığı
- ✅ `requirements.txt` yazıldı ve sanal ortama kuruldu
- ✅ `.env.example` şablonu ve kök dizinde `.env` dosyası oluşturuldu
- ✅ Yönetim betikleri (`install.sh`, `first_run.sh`, `run.sh`, `run_tests.sh`) hazırlandı
- ⏳ `src/` alt dizinleri ve `__init__.py` dosyalarının oluşturulması (Kodlama fazında)

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

### Adım 3 — Modül 2: Piyasa Verileri & Analiz Altyapısı
- `models/market.py` — Pydantic şemaları (`TickerResponse`, `CandlesResponse`, `SymbolListResponse`, `AnalysisSignalResponse`)
- `module2_market.py` — Piyasa veri çekme
  - REST ticker & candle çekme
  - WebSocket canlı fiyat
  - Önbellek sistemi
- `main.py` — `/api/v1/market/*` endpoint'leri

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

### Modül 1 (Tasarım Hazır / Kodlama Bekliyor ⏳)
- [ ] `.env` okuma & yapılandırma
- [ ] Zaman senkronizasyonu
- [ ] API anahtarı doğrulama (HMAC-SHA256)
- [ ] Yetki kontrolü (Read/Trade)
- [ ] Bakiye sorgulama (free/used/total)
- [ ] USDT karşılığı hesaplama
- [ ] WebSocket bakiye aboneliği
- [ ] `/api/v1/account/status`
- [ ] `/api/v1/account/balances`
- [ ] `/api/v1/account/summary`
- [ ] `/api/v1/account/test-connection`

### Modül 2 (Tasarım Hazır / Kodlama Bekliyor ⏳)
- [ ] REST ticker & candle çekme
- [ ] WebSocket canlı fiyat
- [ ] Önbellek sistemi
- [ ] `/api/v1/market/ticker`
- [ ] `/api/v1/market/candles`
- [ ] `/api/v1/market/symbols`
- [ ] `/api/v1/market/analysis`

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
| **2026-09-17 21:35:00** | Review bulguları düzeltildi: `.env` durumu gerçeğe göre güncellendi, yanıltıcı checklist başlıkları düzeltildi, tamamlama göstergesi ve footer log eklendi. | Onaylandı & Tamamlandı (%100) |

