# Modül 2 Spesifikasyonu: Anlık Fiyat Verileri ve Analiz Altyapısı

> **Tamamlanma Durumu:** %100 (Modül 2 Tasarım & Spesifikasyon Fazı) | **Son Güncelleme:** 2026-09-17 21:35:00 (+03:00) | **Onay Durumu:** Kullanıcı Tarafından Onaylandı ✅

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

---

## 4. Modül 2 REST API Endpoint'leri ve Swagger Spesifikasyonu

Swagger Tag: `Market Data & Analysis`

| Metod | Endpoint | Açıklama | Swagger Yanıt Modeli |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/market/ticker` | Belirtilen sembolün (örn. `BTC-USDT`) anlık fiyat ve 24s verilerini getirir. | `TickerResponse` |
| `GET` | `/api/v1/market/candles` | Belirtilen zaman dilimindeki (`1m`, `5m`, `15m`, `1h`, `1d`) geçmiş mum verilerini getirir. | `CandlesResponse` |
| `GET` | `/api/v1/market/symbols` | KuCoin'de işlem gören aktif ve geçerli kripto işlem çiftlerini listeler. | `SymbolListResponse` |
| `GET` | `/api/v1/market/analysis` | Canlı mum verileri üzerinden hesaplanan analiz çıktısını ve sinyali (`BUY`/`SELL`/`HOLD`) döner. | `AnalysisSignalResponse` |

---

## 5. Doküman Değişiklik ve Tamamlanma Günlüğü (Change Log)

| Tarih / Saat | Yapılan Değişiklikler ve İşlem Özeti | Durum |
| :--- | :--- | :--- |
| **2026-09-17 20:53:20** | Modül 2 ilk spesifikasyonu (Ticker, OHLCV, tak-çıkar analiz motoru) hazırlandı. | Tamamlandı |
| **2026-09-17 21:04:23** | REST API endpoint tablosu ve Swagger modelleri tanımlandı. | Tamamlandı |
| **2026-09-17 21:35:00** | Tamamlanma rozeti ve detaylı işlem günlüğü eklendi. | Onaylandı & Tamamlandı (%100) |

