# Modül 2 Spesifikasyonu: Anlık Fiyat Verileri ve Analiz Altyapısı

## 1. Modülün Amacı
Bu modül, KuCoin borsasından canlı ticker fiyatlarını ve mum (OHLCV) verilerini toplar. Gelecekte tanımlanacak al-sat stratejilerinin (indikatörler, formasyonlar vb.) sorunsuz entegre edilebileceği modüler bir analiz altyapısı sağlar.

---

## 2. İşlevsel Detaylar

### 2.1. Canlı Piyasa Veri Akışı
* **Piyasa Ticker Verisi**:
  * Anlık fiyat (Last Price)
  * 24 Saatlik En Yüksek / En Düşük (High / Low)
  * 24 Saatlik Hacim (Volume)
  * 24 Saatlik Yüzdesel Değişim (%)
* **Veri Getirme Yöntemleri**:
  * **REST API**: Periyodik sorgulama (polling).
  * **WebSocket**: Anlık (real-time) canlı fiyat güncellemeleri.

### 2.2. Mum (OHLCV) Verisi Yönetimi
* **Zaman Dilimleri (Timeframes)**: `1m`, `5m`, `15m`, `1h`, `4h`, `1d`.
* **Veri Yapısı**: `[Zaman Damgası (Timestamp), Açılış (Open), Yüksek (High), Düşük (Low), Kapanış (Close), Hacim (Volume)]`.
* **Veri Önbellekleme (Caching)**: Son N adet mum verisi hafızada tutularak analiz motoruna hızlı erişim sağlanır.

### 2.3. Analiz Motoru Mimari Yapısı (Strateji Altyapısı)
* Strateji motoru **Modüler / Eklenti (Plugin)** mimarisinde olacaktır.
* **Girdi**: Anlık fiyatlar + Geçmiş Mum Verileri.
* **Çıktı**: Strateji Sinyali (`BUY`, `SELL`, `NEUTRAL/HOLD`) + Sinyal Gücü/Skoru.
* *Not: Belirli bir indikatör veya kural takımı (RSI, MA, Grid vb.) kullanıcının isteği doğrultusunda bu altyapıya daha sonra eklenecektir.*

---

## 3. Akış Şeması

```
+------------------+         +------------------+         +-----------------------+
|  KuCoin Market   | ------> | Veri Toplayıcı   | ------> | Önbellek & Mum        |
| (WebSocket/REST) |         | (Stream & Fetch) |         | Geçmişi (OHLCV Buffer)|
+------------------+         +------------------+         +-----------------------+
                                                                      |
                                                                      v
                                                          +-----------------------+
                                                          |  Analiz Motoru        |
                                                          | (Strateji Arayüzü)    |
                                                          +-----------------------+
                                                                      |
                                                                      v
                                                          [ Sinyal: AL / SAT / BEKLE ]
```
