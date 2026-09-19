# Modül 3 Spesifikasyonu: Al-Sat Emir Entegrasyonu ve Emir Yönetimi

> **Tasarım & Spesifikasyon Durumu:** %100 (Onaylandı & İzlenebilirlik Matrisi Eklendi ✅) | **Kodlama & Test Durumu:** %0 (Modül 2 Tamamlandı, Kodlama Başlamaya Hazır ⏳) | **Son Güncelleme:** 2026-09-19 23:30:00 (+03:00)

## 1. Modülün Amacı
Bu modül, gelen al-sat sinyallerine veya kullanıcının manuel komutlarına göre KuCoin üzerinde emniyetli alış/satış emirleri oluşturur, emir durumlarını izler ve risk kontrollerini yürütür.

---

## 2. İşlevsel Detaylar

### 2.1. Emir Türleri ve Parametreleri
* **Piyasa Emri (Market Order)**:
  * Anlık tahta fiyatından hızlı alış veya satış.
  * Parametreler: Sembol (örn. BTC/USDT), Yön (BUY/SELL), Miktar/Tutar.
* **Limit Emri (Limit Order)**:
  * Belirlenen hedef fiyattan emir tahtasına emir girilmesi.
  * Parametreler: Sembol, Yön, Hedef Fiyat, Miktar.

### 2.2. Emir Takibi ve Yönetimi
* **Aktif / Açık Emirler**: Emrin ID'si, hedef fiyatı, doluluk oranı (%).
* **İptal İşlemleri**:
  * İstenilen bir emri tekil olarak iptal etme.
  * **Tüm Açık Emirleri İptal Etme** seçeneği.
* **İşlem Geçmişi (Trade History)**: Gerçekleşen emirlerin dolma fiyatı, ödenen komisyon (fee) ve gerçekleşme zamanı loglanır.

### 2.3. Simülasyon / Test Modu (Paper Trading)
* Gerçek API emri vermeden önce botu ve stratejileri sanal bakiye ($10,000 USDT sanal bakiye) ile güvenle test etme imkanı.
* Canlı fiyat verilerini kullanarak emir eşleşmesini gerçekçi şekilde simüle eder.

### 2.4. Güvenlik ve Risk Kontrolleri
* **Bakiye Kontrolü**: Bakiyeden fazla tutarda emir verilmesini engelleme.
* **Acil Durum Butonu (Panic Stop)**: Tek tıkla tüm açık emirleri iptal etme ve bot çalışmasını durdurma.

---

## 3. Modül 3 REST API Endpoint'leri ve Swagger Spesifikasyonu

Swagger Tag: `Orders & Execution`

| Metod | Endpoint | Açıklama | Swagger Yanıt Modeli |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/orders/create` | Yeni Market veya Limit Al/Sat emri iletir (Gerçek veya Sanal). | `OrderCreateResponse` |
| `GET` | `/api/v1/orders/open` | Borsada dolmayı bekleyen açık emirleri listeler. | `OpenOrdersResponse` |
| `GET` | `/api/v1/orders/history` | Geçmişte dolan veya kapanan emir geçmişini döner. | `OrderHistoryResponse` |
| `DELETE` | `/api/v1/orders/{order_id}` | Belirtilen açık emri iptal eder. | `OrderCancelResponse` |
| `POST` | `/api/v1/orders/panic-stop` | **Acil Durum**: Tüm açık emirleri anında iptal eder ve botu durdurur. | `PanicStopResponse` |
| `POST` | `/api/v1/orders/switch-mode` | Gerçek KuCoin modu ile Simülasyon (Paper Trading) modu arasında geçiş yapar. | `SwitchModeResponse` |

---

## 4. Spesifikasyon ↔ Uygulama (Kod) İzlenebilirlik Tablosu

Bu bölüm, **Coding AI** tarafından Modül 3 kodlama aşamasında eksiksiz takip edilecek ve her alt bileşenin birim test dosyasıyla doğrulanmasını sağlayacaktır:

| Gereksinim Kodu | Aşama | Bileşen / Özellik | Hedef Kaynak Dosya | Doğrulama Test Dosyası | Durum |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M3-C01** | Ön Koşul | Pre-Trade Risk & Bakiye Doğrulama (Yetersiz bakiye engeli, min notional kontrolü) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | Bekliyor ⏳ |
| **M3-C02** | Temel İcra | Market Order (Anlık tahta fiyatından Alış/Satış, slippage koruması) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | Bekliyor ⏳ |
| **M3-C03** | Temel İcra | Limit Order (Hedef fiyat, miktar, GTC time-in-force) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | Bekliyor ⏳ |
| **M3-C04** | Takip | Açık Emirleri Listeleme & Sorgulama (`fetch_open_orders`, doluluk %) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | Bekliyor ⏳ |
| **M3-C05** | İptal | Tekil ve Toplu Emir İptali (`cancel_order`, `cancel_all_orders`) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | Bekliyor ⏳ |
| **M3-C06** | Güvenlik | Panic Stop (Tek çağrıda tüm emirleri iptal etme & bot acil durdurma) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | Bekliyor ⏳ |
| **M3-C07** | Simülasyon | Paper Trading Motoru ($10,000 USDT sanal bakiye, canli tahta eşleşmesi, SQLite) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | Bekliyor ⏳ |
| **M3-C08** | Mod Yönetimi | Dinamik Mod Geçişi (`REAL` $\leftrightarrow$ `SIMULATION` switch) | `src/modules/module3_orders.py` | `tests/test_module_3_orders.py` | Bekliyor ⏳ |
| **M3-C09** | Entegrasyon | REST API Endpoint'leri (6 adet FastAPI rotası & Swagger) | `src/main.py` | `tests/test_module_3_orders.py` | Bekliyor ⏳ |

---

## 5. Doküman Değişiklik ve Tamamlanma Günlüğü (Change Log)

| Tarih / Saat | Yapılan Değişiklikler ve İşlem Özeti | Durum |
| :--- | :--- | :--- |
| **2026-09-17 20:53:23** | Modül 3 ilk spesifikasyonu (Emir türleri, açık emir takibi, iptal, risk kontrolleri) hazırlandı. | Tamamlandı |
| **2026-09-17 21:04:30** | REST API endpoint tablosu ve Swagger modelleri tanımlandı. | Tamamlandı |
| **2026-09-17 21:35:00** | Tamamlanma rozeti ve detaylı işlem günlüğü eklendi. | Onaylandı & Tamamlandı (%100) |
| **2026-09-19 23:30:00** | **Spesifikasyon ↔ Uygulama İzlenebilirlik Tablosu Eklendi**: Modül 2'nin %100 tamamlanması üzerine Coding AI için 9 alt maddelik izlenebilirlik tablosu (M3-C01 ... M3-C09) hazırlandı. | **Tasarım Hazır, Kodlama Bekleniyor ⏳** |



