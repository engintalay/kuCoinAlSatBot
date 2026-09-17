# Modül 1 Spesifikasyonu: KuCoin Bağlantısı ve Hesap Durumu

> **Tasarım & Spesifikasyon Durumu:** %100 (Onaylandı ✅) | **Kodlama & Test Durumu:** %20 (Coding AI Test Düzeltmesi Bekleniyor ⚠️) | **Son Güncelleme:** 2026-09-17 22:06:00 (+03:00)

## 1. Modülün Amacı
Bu modül, kullanıcının KuCoin API kimlik bilgilerini yerel `.env` dosyasından güvenli bir şekilde okur, KuCoin sunucularına bağlanarak kimlik ve yetki doğrulamasını yapar ve hesaptaki varlıkların (Spot/Trade hesabı) detaylı durumunu sunar.

---

## 2. Kimlik Bilgileri ve Güvenlik (.env Yönetimi)

### 2.1. Yapılandırma Dosyası (`.env`)
Tüm hassas API erişim şifreleri ve gizli anahtarlar projenin ana dizininde bulunacak `.env` dosyasında saklanacaktır. Kod içerisinde hiçbir şifre veya API key açık halde (hardcoded) yer almayacaktır.

#### Örnek `.env` Dosyası Formatı:
```env
# KuCoin API Yapılandırma Bilgileri
KUCOIN_API_KEY=your_api_key_here
KUCOIN_API_SECRET=your_api_secret_here
KUCOIN_API_PASSPHRASE=your_api_passphrase_here

# Çalışma Modu (false: Canlı Borsa, true: Sandbox)
KUCOIN_IS_SANDBOX=false

# Bot Varsayılan İşlem Modu ('paper': Sanal Simülasyon, 'live': Gerçek API)
DEFAULT_TRADING_MODE=paper
SIMULATION_INITIAL_BALANCE_USDT=10000.0

# Sunucu & REST API (Host & Port)
HOST=127.0.0.1
PORT=8000

# Log Detay Seviyesi (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO
LOG_TO_FILE=true

# Varsayılan Piyasa & Mum Periyodu (1m, 5m, 15m, 1h, 4h, 1d)
DEFAULT_SYMBOL=BTC-USDT
DEFAULT_TIMEFRAME=15m
```
*(Detaylı seçenekler ve açıklamalar `.env.example` dosyasında yer almaktadır).*

#### Güvenlik Standartları:
1. **`.gitignore` Entegrasyonu**: `.env` dosyası kesinlikle `.gitignore` dosyasına eklenerek Git versiyon kontrol sistemine veya kaynak kod depolarına (GitHub vb.) aktarılması engellenecektir.
2. **`.env.example` Şablonu**: Projede şifre içermeyen bir `.env.example` örnek dosyası bulundurulacak, kullanıcı kendi bilgisayarında bunu `.env` olarak kopyalayıp kendi bilgilerini dolduracaktır.

---

## 3. İşlevsel Detaylar ve Bağlantı Yaşam Döngüsü

### 3.1. Bağlantı Sağlık Kontrolü (Health Checks)
Bot başlatıldığında sırasıyla şu adımları kontrol eder:
1. **Zaman Senkronizasyonu (Time Sync Check)**:
   - Yerel bilgisayar saati ile KuCoin sunucu saati arasındaki fark kontrol edilir. (Fark 3 saniyeden fazla ise KuCoin API isteği `Timestamp Expired` hatası verir. Bu durum tespit edilip kullanıcı uyarılır).
2. **Kimlik Doğrulama (Credentials Audit)**:
   - `KUCOIN_API_KEY`, `KUCOIN_API_SECRET`, ve `KUCOIN_API_PASSPHRASE` ile KuCoin API'sine imzalı (HMAC-SHA256) istek atılarak anahtarlar doğrulanır.
3. **Yetki Kontrolü (Permission Audit)**:
   - API anahtarının **Okuma (Read)** ve **İşlem (Trade)** yetkilerine sahip olduğu doğrulanır.
   - *Güvenlik Uyarısı*: API anahtarında **Para Çekme (Withdrawal)** yetkisi tespit edilirse kullanıcıya güvenlik uyarısı gösterilir.

### 3.2. Bakiye Sorgulama ve USDT Karşılığı Hesaplama
* **Hesap Türü**: KuCoin Spot (Trade) Hesabı ve Ana (Main) Hesap.
* **Bakiye Çekimi**:
  * Serbest Bakiye (`free`): İşleme hazır kullanılabilir miktar.
  * Kilitli Bakiye (`used`): Açık limit emirlerinde bekleyen miktar.
  * Toplam Bakiye (`total`): `free + used`.
* **USDT Karşılığı Hesaplama**:
  * USDT dışındaki her bir kripto varlığın (örn. BTC, ETH, KCS) anlık fiyatı Modül 2'den çekilerek USDT cinsinden değeri hesaplanır:
    $$\text{Varlık Değeri (USDT)} = \text{Toplam Miktar} \times \text{Anlık Fiyat (USDT)}$$
  * Tüm varlıklar toplanarak **Toplam Portföy Değeri (USDT)** elde edilir.

### 3.3. Canlı Bakiye Güncellemesi (WebSocket Integration)
* İlk açılışta REST API ile bakiye çekilir.
* Ardından KuCoin Private WebSocket kanalına (`/account/balance`) abone olunarak, bir alış/satış gerçekleştiğinde bakiyelerin anlık olarak güncellenmesi sağlanır.

---

## 4. Veri Modeli (Örnek Döküm)

```json
{
  "connection": {
    "status": "CONNECTED",
    "is_sandbox": false,
    "latency_ms": 42,
    "permissions": ["read", "trade"]
  },
  "summary": {
    "total_portfolio_usdt": 1250.45,
    "free_usdt": 500.00,
    "in_orders_usdt": 750.45
  },
  "assets": [
    {
      "symbol": "USDT",
      "free": 500.00,
      "used": 100.00,
      "total": 600.00,
      "price_usdt": 1.0,
      "usdt_value": 600.00,
      "portfolio_share_percent": 47.98
    },
    {
      "symbol": "BTC",
      "free": 0.005,
      "used": 0.001,
      "total": 0.006,
      "price_usdt": 70050.00,
      "usdt_value": 420.30,
      "portfolio_share_percent": 33.61
    },
    {
      "symbol": "KCS",
      "free": 20.0,
      "used": 0.0,
      "total": 20.0,
      "price_usdt": 11.50,
      "usdt_value": 230.15,
      "portfolio_share_percent": 18.41
    }
  ]
}
```

---

## 5. Kullanıcı Arayüzü (Arayüz Paneli) Bileşenleri
* **Bağlantı Rozeti**: 🟢 **KuCoin Canlı Bağlı** (`.env` Başarılı) / 🔴 **Bağlantı Hatası** (API Şifreleri Geçersiz veya Zaman Kayması Var).
* **Portföy Özet Kartları**:
  1. Toplam Portföy Değeri ($ USDT)
  2. Kullanılabilir Serbest Nakit ($ USDT)
  3. Açık Emirlerde Kilitli Tutar ($ USDT)
* **Varlık Dağılım Tablosu**: Kripto Çifti, Serbest, Kilitli, Toplam Miktar, Birim Fiyat (USDT), Toplam USDT Değeri ve Portföy Yüzdesi (%).

---

## 6. Modül 1 REST API Endpoint'leri ve Swagger Spesifikasyonu

Swagger Tag: `Account & Connection`

| Metod | Endpoint | Açıklama | Swagger Yanıt Modeli |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/account/status` | KuCoin API bağlantı durumu, gecikme süresi (ms) ve yetkileri döndürür. | `ConnectionStatusResponse` |
| `GET` | `/api/v1/account/balances` | Tüm kripto varlıkların serbest, kilitli ve USDT karşılığı bakiyelerini listeler. | `AccountBalancesResponse` |
| `GET` | `/api/v1/account/summary` | Toplam portföy değeri ve serbest nakit özetini döndürür. | `PortfolioSummaryResponse` |
| `POST` | `/api/v1/account/test-connection` | `.env` dosyasındaki şifreleri anlık olarak test eder ve doğrular. | `TestConnectionResponse` |

---

## 7. Spesifikasyon ↔ Uygulama (Kod) İzlenebilirlik Tablosu (Traceability Matrix)

Bu tablo, Analiz AI tarafından tanımlanan spesifikasyon maddeleri ile Coding AI tarafından yazılan gerçek kodun (`src/`) uyum durumunu denetler:

| Spesifikasyon Gereksinimi | Doküman Referansı | Kod Konumu | Uygulama Durumu | Not / Aksiyon |
| :--- | :--- | :--- | :--- | :--- |
| **KuCoin Borsa Bağlantısı** | Bölüm 1 & 2.1 | `src/modules/module1_account.py` | ❌ Hatalı | `ccxt.binance` yazılmış; `ccxt.async_support.kucoin` yapılmalı. |
| **Async / Await Entegrasyonu** | GLOBAL_STANDARDS | `src/modules/module1_account.py` | ❌ Hatalı | Metodlar async ama ccxt senkron çağrılıyor ve testlerde await eksik. |
| **Zaman Senkronizasyonu (3sn Drift)** | Bölüm 3.1 | `src/utils/time_sync.py` | ❌ Eksik | Sadece ping ölçüyor; yerel saat ile sunucu saati arasındaki fark (drift) hesaplanmalı. |
| **Bakiye Sorgulama Veri Yapısı** | Bölüm 3.2 | `src/modules/module1_account.py` | ❌ Hatalı | ccxt `fetch_balance()` dict yapısı yerine liste formatında taranıyor. |
| **Toplam Portföy (USDT) Hesabı** | Bölüm 3.2 | `src/modules/module1_account.py` | ❌ Eksik | Sadece USDT toplanıyor; diğer kriptoların USDT karşılıkları hesaba katılmalı. |
| **WebSocket Canlı Bakiye** | Bölüm 3.3 | `src/modules/module1_account.py` | ⏳ Bekliyor | REST sonrası WebSocket aboneliği eklenecek. |
| **.env ↔ config.py Uyumu** | Bölüm 2.1 | `src/config.py` | ❌ Eksik | `DEFAULT_TRADING_MODE`, `DEFAULT_SYMBOL` vb. alanlar config'te tanımlanmamış. |
| **Birim Test Kapsamı & Doğruluğu**| GLOBAL_STANDARDS | `tests/test_module_1_account.py` | ❌ Başarısız | 17 testten 7'si mantık/async/mock hatasıyla kalıyor. Düzeltilmeli. |

---

## 8. Doküman Değişiklik ve Tamamlanma Günlüğü (Change Log)

| Tarih / Saat | Yapılan Değişiklikler ve İşlem Özeti | Durum |
| :--- | :--- | :--- |
| **2026-09-17 20:53:10** | Modül 1 ilk spesifikasyonu (Kimlik doğrulama, bakiye, veri modeli) hazırlandı. | Tamamlandı |
| **2026-09-17 20:57:22** | `.env` dosya güvenliği, zaman senkronizasyonu ve yetki denetimi detaylandırıldı. | Tamamlandı |
| **2026-09-17 21:04:11** | REST API endpoint tablosu ve Swagger modelleri eklendi. | Tamamlandı |
| **2026-09-17 21:14:23** | `.env.example` senkronizasyonu tamamlandı. | Tamamlandı |
| **2026-09-17 21:35:00** | Tamamlanma rozeti ve detaylı işlem günlüğü eklendi. | Tamamlandı |
| **2026-09-17 22:06:00** | Rozet ayrımı (Spec %100 vs Kod %20) yapıldı ve Spesifikasyon ↔ Kod İzlenebilirlik Tablosu (Bölüm 7) eklendi. | Onaylandı & Tamamlandı (%100) |



