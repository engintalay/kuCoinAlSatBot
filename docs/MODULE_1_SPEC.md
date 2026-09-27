# Modül 1 Spesifikasyonu: KuCoin Bağlantısı ve Hesap Durumu

> **Tasarım & Spesifikasyon Durumu:** %100 (Onaylandı ✅) | **Kodlama & Test Durumu:** %100 (Çoklu Cüzdan, Bakiye Kırılımı, İç Transfer, Varlık Maliyetleri & Şifreli Kasa Dahil, 330/330 Test Geçiyor ✅) | **Son Güncelleme:** 2026-09-27 14:20:00 (+03:00)

## 1. Modülün Amacı
Bu modül, kullanıcının KuCoin API kimlik bilgilerini yerel `.env` dosyasından veya çok kullanıcılı şifreli kasadan (`CryptoVault`) güvenli bir şekilde okur, KuCoin sunucularına bağlanarak kimlik ve yetki doğrulamasını yapar, hesaptaki varlıkların (Spot, Funding, Margin, Futures) detaylı durumunu sunar ve hesaplar arası iç transferleri gerçekleştirir.

---

## 2. Kimlik Bilgileri ve Güvenlik (.env & CryptoVault Yönetimi)

### 2.1. Yapılandırma Dosyası (`.env`) ve Şifreli Kasa (`CryptoVault`)
Tüm hassas API erişim şifreleri ve gizli anahtarlar projenin ana dizininde bulunacak `.env` dosyasında veya `auth.db` içerisindeki şifreli kasada (`CryptoVault`, AES-128 Fernet) kullanıcı bazlı saklanır. Kod içerisinde hiçbir şifre veya API key açık halde (hardcoded) yer almayacaktır.

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
1. **`.gitignore` Entegrasyonu**: `.env` ve `.master_key` dosyaları kesinlikle `.gitignore` dosyasına eklenerek Git versiyon kontrol sistemine aktarılması engellenmiştir.
2. **Kullanıcı Bazlı API İzolasyonu**: `ExchangeClientFactory` ile her kullanıcı kendi şifreli API anahtarlarıyla request-scoped borsa istemcisine sahiptir.

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
* **Hesap Türleri**: KuCoin Spot (`trade`), Ana Cüzdan (`main`/funding), Kaldıraçlı İşlemler (`margin`) ve Vadeli İşlemler (`future`/futures).
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

### 3.4. Tüm Hesap Tiplerinin Birleşimi ve Hesap Kırılımı (Multi-Account Breakdown)
* `get_balances` uç noktası Spot (`trade`), Funding (`main`), Margin (`margin`) ve KuCoin Futures teminat cüzdanını sorgulayıp varlık bazında tek bir listede birleştirir.
* Her varlığa ait hangi cüzdanlarda bulunduğu `accounts: ["spot", "futures", "funding", "margin"]` rozetleriyle sunulur.
* `account_breakdown` listesi ile her hesap tipinde (Spot, Funding, Margin, Futures) toplam kaç USDT varlık bulunduğu ve içerdiği coin listesi döndürülür.

### 3.5. Eldeki Varlıkların Ağırlıklı Alış Maliyeti ve Kâr/Zarar Gösterimi
* Dolan geçmiş emirlerden ağırlıklı ortalama alış maliyeti (`avg_cost`) ve eldeki varlığın toplam maliyeti (`total_cost`) hesaplanır.
* Anlık fiyat (`price_usdt`) ile maliyet karşılaştırılarak gerçekleşmemiş kâr/zarar tutarı (`unrealized_pnl`) ve yüzdesi (`pnl_percent`) hesap tablosuna iliştirilir.

### 3.6. Hesaplar Arası İç Para Transferi (Internal Transfer Motoru)
* Spot (`trade`), Ana Cüzdan (`main`), Marjin (`margin`) ve Vadeli İşlemler (`future`) arasında para birimi ve miktar bazında iki yönlü serbest transfer yapılabilir.
* Endpoint: `POST /api/v1/account/transfer`
* Transfer tamamlandığında borsa bakiyeleri ve hesap bazlı kırılım anında taze olarak kullanıcıya sunulur.

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
| `GET` | `/api/v1/account/balances` | Tüm kripto varlıkların serbest, kilitli, USDT karşılığı, hesap etiketleri ve maliyetlerini listeler. | `AccountBalancesResponse` |
| `GET` | `/api/v1/account/summary` | Toplam portföy değeri, hesap bazlı bakiye kırılımı (`total_by_account`) ve serbest nakit özetini döndürür. | `PortfolioSummaryResponse` |
| `POST` | `/api/v1/account/test-connection` | Kullanıcının şifreli veya .env anahtarlarını test eder ve doğrular. | `TestConnectionResponse` |
| `POST` | `/api/v1/account/transfer` | Spot, Funding, Margin ve Futures hesapları arasında iç para transferi gerçekleştirir. | `TransferResponse` |
| `GET` | `/api/v1/settings/api-keys` | Kullanıcının kayıtlı borsa anahtarlarının maskeli durumunu döner. | `APIKeysStatusResponse` |
| `POST` | `/api/v1/settings/api-keys` | Kullanıcı borsa API anahtarını şifreleyerek (`CryptoVault`) kalıcı kaydeder. | `APIKeysSaveResponse` |

---

## 7. Spesifikasyon ↔ Uygulama (Kod) İzlenebilirlik Tablosu (Traceability Matrix)

Bu tablo, Analiz AI tarafından tanımlanan spesifikasyon maddeleri ile Coding AI tarafından yazılan gerçek kodun (`src/`) uyum durumunu denetler:

| Spesifikasyon Gereksinimi | Doküman Referansı | Kod Konumu | Uygulama Durumu | Not / Doğrulama Kanıtı |
| :--- | :--- | :--- | :---: | :--- |
| **KuCoin Borsa Bağlantısı** | Bölüm 1 & 2.1 | `src/modules/module1_account.py` | ✅ Tamamlandı | `ccxt.async_support.kucoin` başarıyla bağlandı. |
| **Async / Await Entegrasyonu** | GLOBAL_STANDARDS | `src/modules/module1_account.py` | ✅ Tamamlandı | Tüm I/O işlemleri asenkron yapıda `await` ile çağrılıyor. |
| **Zaman Senkronizasyonu (3sn Drift)** | Bölüm 3.1 | `src/utils/time_sync.py` | ✅ Tamamlandı | KuCoin sunucu zamanı ile yerel saat arasındaki 3000ms kayma kontrolü çalışıyor. |
| **Bakiye Sorgulama Veri Yapısı** | Bölüm 3.2 | `src/modules/module1_account.py` | ✅ Tamamlandı | `free`, `used`, `total` dict yapısıyla doğrulanarak alınıyor. |
| **Toplam Portföy (USDT) & Pay Hesabı** | Bölüm 3.2 | `src/modules/module1_account.py` | ✅ Tamamlandı | USDT toplamı ve her varlık için `portfolio_share_percent` hesaplanıyor. |
| **WebSocket Canlı Bakiye Akışı** | Bölüm 3.3 | `src/modules/module1_account.py` | ✅ Tamamlandı | `ccxt.pro.kucoin` ile arka planda canlı bakiye stream ve önbellek desteği sağlandı. |
| **API Yetki Denetimi (Permissions)** | Bölüm 3.1 | `src/modules/module1_account.py` | ✅ Tamamlandı | Read/Trade yetkisi denetleniyor, Withdrawal yetkisinde güvenlik uyarısı veriliyor. |
| **Tüm Hesap Tipleri Bakiyesi (Spot/Margin/Futures/Funding)** | Bölüm 3.4 | `src/modules/module1_account.py` | ✅ Tamamlandı | `trade`, `main`, `margin` ve `kucoinfutures` cüzdanları tek listede birleştirildi. |
| **Hesap Bazlı Bakiye Kırılımı** | Bölüm 3.4 | `src/modules/module1_account.py` | ✅ Tamamlandı | `account_breakdown` ve `total_by_account` ile her hesap türünün toplam USDT'si ayrıştırıldı. |
| **Hesap İçi Transfer Motoru** | Bölüm 3.6 | `src/modules/module1_account.py` | ✅ Tamamlandı | Spot↔Futures↔Margin her yöne serbest transfer `POST /api/v1/account/transfer` ile doğrulandı. |
| **Şifreli Kasa & Kullanıcı İzolasyonu** | Bölüm 2.1 | `src/auth/crypto_vault.py`, `src/exchanges/factory.py` | ✅ Tamamlandı | AES-128 Fernet şifreleme ve request-scoped kullanıcı borsa fabrikası kuruldu. |
| **Eldeki Varlık Maliyetleri (Holding Costs)** | Bölüm 3.5 | `src/modules/module1_account.py`, `src/modules/module3_orders.py` | ✅ Tamamlandı | Dolan emirlerden `avg_cost`, `total_cost`, `unrealized_pnl` portföye entegre edildi. |
| **Birim Test Kapsamı & Doğruluğu**| GLOBAL_STANDARDS | `tests/test_module_1_account.py`, `tests/test_account_transfer.py` | ✅ Tamamlandı | **Tüm hesap testleri başarıyla geçiyor** (330/330 test %100 yeşil). |

---

## 8. Doküman Değişiklik ve Tamamlanma Günlüğü (Change Log)

| Tarih / Saat | Yapılan Değişiklikler ve İşlem Özeti | Durum |
| :--- | :--- | :--- |
| **2026-09-17 20:53:10** | Modül 1 ilk spesifikasyonu (Kimlik doğrulama, bakiye, veri modeli) hazırlandı. | Tamamlandı |
| **2026-09-17 20:57:22** | `.env` dosya güvenliği, zaman senkronizasyonu ve yetki denetimi detaylandırıldı. | Tamamlandı |
| **2026-09-17 21:04:11** | REST API endpoint tablosu ve Swagger modelleri eklendi. | Tamamlandı |
| **2026-09-17 21:14:23** | `.env.example` senkronizasyonu tamamlandı. | Tamamlandı |
| **2026-09-17 21:35:00** | Tamamlanma rozeti ve detaylı işlem günlüğü eklendi. | Tamamlandı |
| **2026-09-17 22:06:00** | Rozet ayrımı (Spec %100 vs Kod %20) yapıldı ve Spesifikasyon ↔ Kod İzlenebilirlik Tablosu eklendi. | Onaylandı |
| **2026-09-19 22:00:00** | **Kodlama & Test Doğrulaması**: Coding AI tarafından kucoin async, drift kontrolü, bakiye dict, websocket stream ve yetki denetimi tamamlandı. 29/29 birim test geçti. | **Kodlama & Test Tamamlandı (%100)** ✅ |
| **2026-09-20 19:46:00** | **Bakiyelere Tüm Hesap Tipleri Dahil Edildi**: Spot (`trade`), Funding (`main`), Margin (`margin`) ve KuCoin Futures cüzdanları tek portföyde birleştirildi ve arayüze `Hesap` sütunu eklendi. | **Onaylandı & Tamamlandı (%100) ✅** |
| **2026-09-21 13:32:00** | **Hesap Bazlı Kırılım**: `account_breakdown` ve `total_by_account` alanları eklenerek her cüzdan türünün USDT varlığı ayrıştırıldı. | **Onaylandı & Tamamlandı (%100) ✅** |
| **2026-09-25 16:30:00** | **Eldeki Varlıkların Alış Maliyeti**: `avg_cost`, `total_cost`, `unrealized_pnl` ve `pnl_percent` portföy varlıklarına entegre edildi. | **Onaylandı & Tamamlandı (%100) ✅** |
| **2026-09-27 00:48:00** | **Çok Kullanıcılı Şifreli Kasa & Request-Scoped Client**: Borsa anahtarları `CryptoVault` ile şifrelendi, `ExchangeClientFactory` ile request-scoped mimariye geçildi. | **Onaylandı & Tamamlandı (%100) ✅** |
| **2026-09-27 02:05:00** | **Kullanıcı Borsa API Anahtarı Yönetimi**: `GET/POST /api/v1/settings/api-keys` ile web üzerinden şifreli anahtar yönetimi tamamlandı. | **Onaylandı & Tamamlandı (%100) ✅** |
| **2026-09-27 03:33:00** | **Hesap İçi Transfer Motoru Tamamlandı**: `transfer_funds` ve `POST /api/v1/account/transfer` ile Spot, Funding, Margin ve Futures arasında çift yönlü transfer devreye alındı (toplam 326/326 test). | **Onaylandı & Tamamlandı (%100) ✅** |
| **2026-09-27 13:40:00** | **Futures Pozisyon ve Bakiye Senkronizasyonu**: KuCoin Futures borsa kaldıracı ve marjin modu yapılandırması tamamlandı; toplam 330/330 test %100 yeşil. | **Onaylandı & Tamamlandı (%100) ✅** |



