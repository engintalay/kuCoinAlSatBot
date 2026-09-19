# Modül 3 Spesifikasyonu: Al-Sat Emir Entegrasyonu, Akıllı Paket Emir ve Yönetimi

> **Tasarım & Spesifikasyon Durumu:** %100 (Akıllı Paket Emir, Düzenleme, Öneri Motoru ve Ayarlar Eklendi ✅) | **Kodlama & Test Durumu:** Temel Emirler Tamamlandı (%100, 16/16 Test), Gelişmiş Paket & Öneri Özellikleri Bekleniyor ⏳ | **Son Güncelleme:** 2026-09-20 01:05:00 (+03:00)

## 1. Modülün Amacı
Bu modül; gelen al-sat sinyallerine ve analiz motorundan türetilen hazır seviyelere (Giriş, TP1, TP2, Stop-Loss) göre KuCoin veya Simülasyon ortamında otomatik hesaplamalı **Akıllı Paket Emirler (Bracket Orders)** oluşturur; açık emirleri dinamik olarak düzenler, piyasa şartları değiştikçe kullanıcıya anlık güncelleme tavsiyeleri (Öneri Motoru) sunar ve çoklu koin destekli ayarlar altyapısını yönetir.

---

## 2. İşlevsel Detaylar

### 2.1. Temel Emir Türleri ve Parametreleri
* **Piyasa Emri (Market Order)**: Anlık tahta fiyatından hızlı alış veya satış.
* **Limit Emri (Limit Order)**: Belirlenen hedef fiyattan emir tahtasına girilen alış veya satış emri.

### 2.2. Emir Takibi ve Yönetimi
* **Aktif / Açık Emirler**: Emrin ID'si, sembolü, yönü, türü, hedef fiyatı, doluluk oranı (%).
* **İptal İşlemleri**:
  * İstenilen bir emri tekil olarak iptal etme (`DELETE /api/v1/orders/{order_id}`).
  * **Tüm Açık Emirleri İptal Etme** (veya sembol bazlı toplu iptal).
* **İşlem Geçmişi (Trade History)**: Gerçekleşen emirlerin dolma fiyatı, ödenen komisyon (fee) ve gerçekleşme zamanı loglanır.

### 2.3. Simülasyon / Test Modu (Paper Trading)
* Gerçek API emri vermeden önce botu ve stratejileri sanal bakiye ($10,000 USDT sanal bakiye) ile güvenle test etme imkanı.
* Canlı tahta fiyat verilerini kullanarak limit ve stop emir eşleşmelerini gerçekçi simüle eder.

### 2.4. Güvenlik ve Risk Kontrolleri
* **Bakiye Kontrolü**: Serbest nakitten fazla tutarda emir verilmesini engelleme.
* **Acil Durum Butonu (Panic Stop)**: Tek tıkla tüm açık emirleri iptal etme ve bot çalışmasını derhal durdurma.

### 2.5. Otomatik Seviyeli Akıllı Paket Emir (Smart Bracket Order)
* Analiz motorunun (`trade_setup`) ürettiği seviyeler doğrudan formda hazır sunulur:
  * `entry_price`: Optimal giriş seviyesi (anlık piyasa veya limit pullback).
  * `tp1_price`: Pozisyonun %50'sini kapatacak ilk kâr hedefi (R:R 1:1.5 veya Pivot R1 / Fib 0.618).
  * `tp2_price`: Pozisyonun kalan %50'sini kapatacak nihai kâr hedefi (R:R 1:3.0 veya Pivot R2 / Fib 1.0).
  * `stop_loss_price`: Volatilite/ATR veya son Swing Low tabanlı zarar kes seviyesi (`Entry - 1.5 * ATR`).
  * `risk_reward_ratio`: Risk / Ödül oranı (Örn: 1:2.4).
* **Kullanıcı Etkileşimi**: Kullanıcı yalnızca yatırmak istediği **USDT Tutarını** girer (veya `%25`, `%50`, `%100` bakiye butonuna tıklar).
* **Otomatik Hesaplama**:
  * `amount = usdt_amount / entry_price` (Kripto hassasiyetine göre formatlanır).
  * Maksimum Risk Tutarı: `risk_usdt = amount * (entry_price - stop_loss_price)`.
  * Potansiyel Kâr Tutarı: `gain_tp1_usdt` ve `gain_tp2_usdt`.
* **Tek Tıkla Paket İletim (`POST /api/v1/orders/bracket`)**:
  * Ana Giriş Emri iletilir.
  * Bağlı olarak %50 miktar için TP1 Limit emri, %50 miktar için TP2 Limit emri ve %100 pozisyon için Stop-Loss emri tek bir paket (`bracket_id`) olarak borsa/simülatöre kaydedilir.

### 2.6. Açık Emir Güncelleme ve Düzenleme (Order Modification / Amend)
* Açık emirler tablosunda "Düzenle" (Edit) fonksiyonu sunulur.
* Kullanıcı emri iptal edip yeniden yazmak zorunda kalmadan:
  * Hedef Fiyat (Price)
  * Miktar (Amount)
  * Bağlı TP1, TP2 veya SL seviyelerini güncelleyebilir.
* Endpoint: `PUT /api/v1/orders/{order_id}`.
* Borsa üzerinde KuCoin Amend API'si veya atomik cancel-replace mantığıyla güvenle icra edilir.

### 2.7. Dinamik Güncelleme Öneri Motoru (Dynamic Recommendation Engine)
* Sistem arka planda canlı fiyatı, göstergeleri ve açık emirleri periyodik olarak denetler:
  1. **Başabaş / Trailing Stop Önerisi**: Fiyat TP1 hedefine ulaştığında veya kâra geçtiğinde:
     * *"💡 Fiyat TP1 hedefine ulaştı. Stop seviyesini giriş fiyatına çekerek işlemi başabaş (Breakeven) yapmanız önerilir."*
  2. **Giriş Fiyatı Revizyon Önerisi**: Bekleyen limit alış emrinde fiyat yukarı kırılım (BOS) yapıp uzaklaşırsa:
     * *"💡 Fiyat yukarı kırıldı. Giriş fiyatını $X seviyesine revize etmeniz önerilir."*
  3. **Erken Çıkış / Stop Daraltma Önerisi**: Karşıt yönde güçlü CHoCH dönüşümü tespit edildiğinde:
     * *"⚠️ 15m zaman diliminde trend dönüşü (CHoCH) saptandı. Stop seviyesini daraltmanız önerilir."*
* Endpoint'ler:
  * `GET /api/v1/orders/recommendations`: Sistem tarafından üretilen bekleyen önerileri döner.
  * `POST /api/v1/orders/recommendations/{id}/apply`: Kullanıcının tek tıkla öneriyi emre uygulamasını sağlar.

### 2.8. Ayarlar ve Çoklu Kripto Varlık Yapılandırması (Settings & Multi-Coin)
* Sistem birden çok kripto parayı (Watchlist) destekler.
* Varsayılan koin BTC/USDT olmakla birlikte ETH/USDT, SOL/USDT, AVAX/USDT gibi tüm KuCoin USDT çiftleri dinamik olarak yönetilebilir.
* Endpoint'ler:
  * `GET /api/v1/settings`: İzleme listesi, varsayılan mod (paper/live), varsayılan risk parametrelerini döner.
  * `POST /api/v1/settings`: Ayarları kaydeder ve SQLite `settings` tablosunda kalıcı kılar.
  * `GET /api/v1/settings/symbols`: KuCoin üzerindeki geçerli sembolleri arama ve listeleme imkanı sunar.

---

## 3. Modül 3 REST API Endpoint'leri ve Swagger Spesifikasyonu

Swagger Tag: `Orders & Execution`

| Metod | Endpoint | Açıklama | Swagger Yanıt Modeli |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/orders/create` | Yeni Market veya Limit Al/Sat emri iletir. | `OrderCreateResponse` |
| `POST` | `/api/v1/orders/bracket` | **Akıllı Paket Emir**: Giriş + TP1 (%50) + TP2 (%50) + SL seviyelerini tek seferde iletir. | `BracketOrderResponse` |
| `GET` | `/api/v1/orders/open` | Borsada dolmayı bekleyen açık emirleri listeler. | `OpenOrdersResponse` |
| `PUT` | `/api/v1/orders/{order_id}` | Açık emrin fiyat, miktar veya TP/SL parametrelerini günceller. | `OrderModifyResponse` |
| `DELETE` | `/api/v1/orders/{order_id}` | Belirtilen açık emri iptal eder. | `OrderCancelResponse` |
| `GET` | `/api/v1/orders/history` | Geçmişte dolan veya kapanan emir geçmişini döner. | `OrderHistoryResponse` |
| `GET` | `/api/v1/orders/recommendations` | Canlı piyasaya göre üretilen dinamik güncelleme önerilerini listeler. | `RecommendationsResponse` |
| `POST` | `/api/v1/orders/recommendations/{id}/apply` | Seçilen güncelleme önerisini doğrudan ilgili emre uygular. | `ApplyRecommendationResponse` |
| `POST` | `/api/v1/orders/panic-stop` | **Acil Durum**: Tüm açık emirleri anında iptal eder ve botu durdurur. | `PanicStopResponse` |
| `POST` | `/api/v1/orders/switch-mode` | Gerçek KuCoin modu ile Simülasyon (Paper Trading) modu arasında geçiş yapar. | `SwitchModeResponse` |
| `GET` | `/api/v1/settings` | Çoklu coin izleme listesi, mod ve risk ayarlarını döner. | `SettingsResponse` |
| `POST` | `/api/v1/settings` | Çoklu coin listesi, mod ve risk ayarlarını günceller ve kaydeder. | `SettingsResponse` |
| `GET` | `/api/v1/settings/symbols` | KuCoin aktif işlem çiftlerini arar ve listeler. | `SymbolsListResponse` |

---

## 4. Spesifikasyon ↔ Uygulama (Kod) İzlenebilirlik Tablosu

Bu bölüm, **Coding AI** tarafından Modül 3 kodlama aşamasında eksiksiz takip edilecek ve her alt bileşenin birim test dosyasıyla doğrulanmasını sağlayacaktır:

| Gereksinim Kodu | Aşama | Bileşen / Özellik | Hedef Kaynak Dosya | Doğrulama Test Dosyası | Durum |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M3-C01** | Ön Koşul | Pre-Trade Risk & Bakiye Doğrulama (Yetersiz bakiye engeli, min notional kontrolü) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | ✅ Tamamlandı (5 test geçiyor) |
| **M3-C02** | Temel İcra | Market Order (Anlık tahta fiyatından Alış/Satış, slippage koruması) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | ✅ Tamamlandı (2 test geçiyor) |
| **M3-C03** | Temel İcra | Limit Order (Hedef fiyat, miktar, GTC time-in-force) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | ✅ Tamamlandı (2 test geçiyor) |
| **M3-C04** | Takip | Açık Emirleri Listeleme & Sorgulama (`fetch_open_orders`, doluluk %) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | ✅ Tamamlandı (1 test geçiyor) |
| **M3-C05** | İptal | Tekil ve Toplu Emir İptali (`cancel_order`, `cancel_all_orders`) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | ✅ Tamamlandı (2 test geçiyor) |
| **M3-C06** | Güvenlik | Panic Stop (Tek çağrıda tüm emirleri iptal etme & bot acil durdurma) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | ✅ Tamamlandı (1 test geçiyor) |
| **M3-C07** | Simülasyon | Paper Trading Motoru ($10,000 USDT sanal bakiye, canlı tahta eşleşmesi, SQLite) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | ✅ Tamamlandı (1 test geçiyor) |
| **M3-C08** | Mod Yönetimi | Dinamik Mod Geçişi (`REAL` $\leftrightarrow$ `SIMULATION` switch) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | ✅ Tamamlandı (3 test geçiyor) |
| **M3-C09** | Entegrasyon | Temel REST API Endpoint'leri (6 adet FastAPI rotası & Swagger) | `src/main.py` | `tests/test_module_3_orders.py` | ✅ Tamamlandı (6 endpoint aktif) |
| **M3-C10** | Akıllı İcra | Akıllı Paket Emir (Bracket Order: Giriş + TP1 %50 + TP2 %50 + SL paketi) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | ⏳ Bekliyor |
| **M3-C11** | Düzenleme | Açık Emir Güncelleme / Revizyon (`modify_order`, fiyat/miktar/SL/TP değişimi) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | ⏳ Bekliyor |
| **M3-C12** | Akıllı Öneri | Dinamik Öneri Motoru (Breakeven trailing, giriş revizyonu, ters yapı uyarısı & apply) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | ⏳ Bekliyor |
| **M3-C13** | Ayarlar | Ayarlar ve Çoklu Coin Yönetimi (Watchlist, işlem modu, risk parametreleri, SQLite) | `src/modules/settings.py` / `src/main.py` | `tests/test_settings.py` | ⏳ Bekliyor |

---

## 5. Doküman Değişiklik ve Tamamlanma Günlüğü (Change Log)

| Tarih / Saat | Yapılan Değişiklikler ve İşlem Özeti | Durum |
| :--- | :--- | :--- |
| **2026-09-17 20:53:23** | Modül 3 ilk spesifikasyonu (Emir türleri, açık emir takibi, iptal, risk kontrolleri) hazırlandı. | Tamamlandı |
| **2026-09-17 21:04:30** | REST API endpoint tablosu ve Swagger modelleri tanımlandı. | Tamamlandı |
| **2026-09-17 21:35:00** | Tamamlanma rozeti ve detaylı işlem günlüğü eklendi. | Onaylandı & Tamamlandı (%100) |
| **2026-09-19 23:30:00** | Spesifikasyon ↔ Uygulama İzlenebilirlik Tablosu Eklendi: Coding AI için 9 alt maddelik izlenebilirlik tablosu (M3-C01 ... M3-C09) hazırlandı. | Tamamlandı |
| **2026-09-20 00:10:00** | **Modül 3 Kodlama ve Testleri %100 Tamamlandı**: `src/modules/module3_orders.py` ve 6 REST API endpoint'i yazıldı. Pre-trade risk, market/limit emirler, açık emir takibi, iptal, Panic Stop ve Paper Trading simülasyonu 16 yeni birim test ile doğrulandı. Toplam test sayısı 110/110'a ulaştı. | **Modül 3 Tamamlandı (%100) ✅** |
| **2026-09-20 01:05:00** | **Akıllı Paket Emir, Düzenleme, Öneri Motoru ve Ayarlar Eklendi**: Analiz motorundan otomatik seviye hesaplamalı paket emirler (Giriş + TP1 + TP2 + SL), açık emir düzenleme (`modify_order`), canlı piyasa durumuna göre akıllı tavsiyeler üreten Dinamik Öneri Motoru ve Çoklu Coin Ayarlar yapısı spesifikasyona ve izlenebilirlik tablosuna (M3-C10..M3-C13) dahil edildi. | **Onaylandı & Genişletildi (%100) ✅** |




