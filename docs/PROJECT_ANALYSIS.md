# KuCoin Al-Sat Botu - Proje Analiz ve Tasarım Dokümanı

> **Tasarım & Spesifikasyon Durumu:** %100 (Yeni Gereksinimler: Kullanım Kılavuzu & Info Düğmeleri Eklendi ✅) | **Kodlama & Test Durumu:** %100 (129/129 Test Geçiyor, Yeni UI Özellikleri Kodlanmayı Bekliyor ⏳) | **Son Güncelleme:** 2026-09-20 01:00:00 (+03:00)

## 1. Proje Genel Bakışı
Bu doküman, KuCoin kripto para borsasında çalışacak modüler **Al-Sat Botu** uygulamasının mimarisini, veri akışını ve modül detaylarını içerir. 

Proje, gelecekte yeni stratejiler ve özellikler eklenebilecek esnek ve modüler bir yapıda tasarlanmıştır.

---

## 2. Modüler Yapı ve Faz Planı

```
+-----------------------------------------------------------------------+
|                         KULLANICI ARAYÜZÜ / PANEL                     |
+-----------------------------------------------------------------------+
        |                                   |                    |
        v                                   v                    v
+-----------------------+   +-----------------------+   +-----------------------+
|       MODÜL 1         |   |       MODÜL 2         |   |       MODÜL 3         |
| KuCoin Bağlantısı &   |   |  Anlık Piyasa Verisi  |   |   Al-Sat Emirleri     |
|    Hesap Durumu       |   |     ve Analiz         |   |     Entegrasyonu      |
+-----------------------+   +-----------------------+   +-----------------------+
        |                                   |                    |
        +-----------------------------------+--------------------+
                                            |
                                            v
                                 [ KuCoin API & WebSocket ]
```

---

### Modül 1: KuCoin API Entegrasyonu & Hesap Durumu
**Amaca Uygunluk**: Kullanıcının KuCoin hesabını güvenli bir şekilde bağlamak ve bakiye/hesap durumunu anlık olarak görüntülemek.

#### İşlevsel Gereksinimler:
1. **API Anahtarı Yönetimi (.env Saklama)**:
   - KuCoin `API Key`, `API Secret` ve `API Passphrase` bilgileri projenin kök dizinindeki `.env` dosyasında saklanacaktır.
   - `.env` dosyası kesinlikle `.gitignore` içerisine dahil edilecek ve kod reposuna aktarılmayacaktır.
   - Şifre içermeyen bir `.env.example` dosyası proje reposuna eklenerek şablon sağlanacaktır.
   - Bağlantı ve yetki doğrulaması (Read ve Trade izinleri) otomatik yapılacaktır.
2. **Hesap Bakiye Sorgulama**:
   - Spot (Trade) hesabı toplam ve kullanılabilir varlıkların çekilmesi.
   - Varlıkların USDT karşılığı toplam değerinin hesaplanması.
3. **Hesap Durumu & Sağlık Göstergesi**:
   - API yanıt süreleri ve bağlantı durumu (Bağlı / Bağlantı Koptu / Hatalı Key).
   - Rate Limit (İstek kotası) takibi.

---

### Modül 2: Anlık Piyasa Verisi Akışı ve Çok Katmanlı Analiz Motoru
**Amaca Uygunluk**: KuCoin'den canlı fiyat (ticker), L2 derinlik ve mum (OHLCV) verilerini toplamak; 10 katmanlı indikatör ve Market Structure (SMC) feature'larını hesaplayarak çoklu zaman dilimi (MTF) destekli 0-100 Bileşik Puanlama Motoru (Composite Scoring Engine) ile doğrulanmış sinyaller üretmek.

#### İşlevsel Gereksinimler:
1. **Canlı Fiyat ve Derinlik Akışı (Ticker & L2 Order Book)**:
   - Seçilen işlem çiftlerinin (BTC-USDT vb.) son fiyat, 24s hacim, değişim oranları ve alış-satış spread dengesizliğinin takibi.
2. **Geçmiş Mum (OHLCV) Yönetimi & Rolling Ring Buffer**:
   - Belirlenen zaman dilimlerinde (1m, 5m, 15m, 1h, 4h, 1d) 300-500 mumluk kayan önbellek.
   - Kapanmış mum (confirmed candle) ile geçici mum (intrabar provisional) ayrımı ve repainting/lookahead koruması.
3. **10 Katmanlı Analiz Motoru & Feature Engine**:
   - Trend (EMA, Supertrend, Ichimoku), Momentum (RSI, StochRSI, MACD), Güç (ADX, Choppiness), Hacim (RVOL, VWAP, CMF), Volatilite (ATR, Bollinger, Squeeze), Seviyeler (Pivots, Fib), Fiyat Hareketi/SMC (BOS, CHoCH, FVG, OB), Türevler (OI, Funding, CVD) ve MTF (4H rejim → 1H setup → 15m tetikleyici).
4. **Bileşik Puanlama (0-100 Score) & Gerekçelendirme Motoru**:
   - Boğa/Ayı puanlaması, sahte sinyal filtreleri ve insan tarafından okunabilir gerekçe/risk uyarısı çıktıları.

---

### Modül 3: Al-Sat Emirleri Entegrasyonu ve Emir Yönetimi
**Amaca Uygunluk**: Analiz çıktıklarına veya kullanıcı komutlarına göre KuCoin üzerinde emniyetli biçimde alış ve satış emirleri vermek ve emir durumlarını yönetmek.

#### İşlevsel Gereksinimler:
1. **Emir Türleri**:
   - **Market Emri**: Anlık piyasa fiyatından hızlı Al/Sat.
   - **Limit Emri**: Belirlenen hedef fiyattan Al/Sat.
2. **Emir Durumu Takibi**:
   - Açık emirlerin listelenmesi ve anlık durumunun (Bekliyor / Doldu / Kısmen Doldu / İptal) takibi.
   - İstendiğinde açık emirleri tek tıkla veya otomatik iptal edebilme.
3. **Güvenlik ve Risk Önlemleri**:
   - Yanlışlıkla yüksek tutarlı işlem yapılmasını önlemek için maks bakiye limiti kontrolü.
   - **Acil Durum (Panic Button)**: Tüm açık emirleri iptal etme ve pozisyonları kapatma işlevi.
   - **Simülasyon / Test Modu**: Gerçek emir vermeden önce mantığı test edebilmek için sanal işlem katmanı.

---

### Kullanıcı Deneyimi & Rehberlik: Kullanım Kılavuzu Sayfası ve Bağlamsal Info Düğmeleri
**Amaca Uygunluk**: Kullanıcının botu, risk parametrelerini ve analiz göstergelerini kolayca kavramasını sağlamak, hatalı emir iletimini önlemek ve arayüzün her noktasında şeffaf, bağlamsal rehberlik sunmak.

#### İşlevsel Gereksinimler:
1. **Ana Sayfadan Bağlantılı Kullanım Kılavuzu Sayfası (`/guide` veya Kılavuz Görünümü)**:
   - Dashboard ana sayfasında (Header ve Sol Menü gezinme çubuğunda) dikkat çekici bir **"📖 Kullanım Kılavuzu"** veya **"Nasıl Kullanılır?"** bağlantısı/sekmesi bulunacaktır.
   - Bu rehber sayfasında aşağıdaki konular sade ve anlaşılır bir dille adım adım açıklanacaktır:
     - **Başlangıç & API Kurulumu**: `.env` dosyasına KuCoin anahtarlarının girilmesi, borsa üzerinde kesinlikle para çekme (Withdraw) yetkisinin verilmemesi gerektiği güvenlik uyarısı.
     - **İşlem Modları Arasındaki Fark**:
       * `🧪 SIMULATION (Paper Trading)`: Canlı tahta fiyatıyla eşleşen, $10,000 sanal USDT ile çalışan, komisyon ve bakiye düşümünü gerçekçi simüle eden sıfır riskli test ortamı.
       * `🟢 LIVE (Gerçek Mod)`: Doğrudan KuCoin spot hesabındaki gerçek bakiyeyle emir ileten canlı işlem modu.
     - **Çok Katmanlı Analiz Motorunun Okunması**: 0-100 Boğa/Ayı Bileşik Skoru ne anlama gelir? Hangi puan aralıklarında güçlü alım/satım veya nötr kalınır? MTF hiyerarşisinin (4H rejim $\rightarrow$ 1H setup $\rightarrow$ 15m tetikleyici) kuralı nedir?
     - **Market Structure (SMC) & İndikatörler**: BOS (Trend devam kırılımı), CHoCH (Karakter/Trend dönüşümü), FVG (Dengesizlik boşlukları), Supertrend ve Squeeze kavramları.
     - **Emir Verme & Takip**: Market ve Limit emirlerin farkı, KuCoin minimum işlem tutarı ($5 USDT) kuralı.
     - **Acil Durum (⛔ PANIC STOP)**: Butona tıklandığında sistemin tüm açık emirleri nasıl anında iptal ettiği ve botu nasıl korumaya aldığı.

2. **Kritik Arayüz Bileşenlerinde Bağlamsal "Info" (ℹ️) Düğmeleri**:
   - Kullanıcının teknik terimleri veya fonksiyonları sayfadan ayrılmadan anlamasını sağlamak için önemli arayüz noktalarının yanına interaktif `ℹ️` (Info) butonları yerleştirilecektir.
   - Butona tıklandığında veya fare üzerine getirildiğinde (Hover Tooltip veya Tıklamalı Popover) kısa, net ve öğretici açıklamalar gösterilecektir:
     * **Portföy Kartı (Toplam / Serbest Nakit)**: `ℹ️` *"Serbest nakit hemen harcanabilir bakiyenizdir; emirlerde kilitli tutarlar bu tutara dahil değildir."*
     * **Mod Butonu (`SIMULATION` / `LIVE`)**: `ℹ️` *"Simülasyon modunda sanal 10,000 USDT ile risksiz deneme yaparsınız. Canlı mod KuCoin hesabınızdaki gerçek bakiyeyi kullanır."*
     * **⛔ PANIC STOP Butonu**: `ℹ️` *"Acil Durum: Tek tıkla borsadaki tüm açık emirlerinizi derhal iptal eder ve botun yeni işlem açmasını kilitler."*
     * **0-100 Bileşik Analiz Skoru**: `ℹ️` *"Trend, momentum, volatilite, hacim ve SMC katmanlarının ağırlıklı puanıdır. Choppiness yüksekse piyasa yatay kabul edilip skor nötrlenir."*
     * **MTF Analizi**: `ℹ️` *"4 saatlik ana trend, 1 saatlik hazırlık ve 15 dakikalık tetikleyici uyumlu olduğunda işlem sinyali verilir."*
     * **SMC Market Structure**: `ℹ️` *"Kurumsal fiyat hareketleri: BOS trend devamını, CHoCH trend dönüşünü, FVG ise fiyatın geri çekilebileceği dengesizlik alanını gösterir."*
     * **Emir Formu (Market / Limit)**: `ℹ️` *"Market emri anlık tahta fiyatından hemen gerçekleşir. Limit emri belirlediğiniz fiyata gelene kadar bekler. Min. tutar 5 USDT'dir."*


---

## 3. Kesinleşen Teknoloji Yığını

| Katman | Seçilen Teknoloji | Versiyon / Kütüphaneler | Belirlenme Nedeni |
| :--- | :--- | :--- | :--- |
| **Backend Dili** | **Python** | Python `3.14+` | Yerel ortamda kurulu, veri analizi ve borsa entegrasyonunda sektör standardı. |
| **Web / REST Framework** | **FastAPI + Uvicorn** | FastAPI v0.110+ | Asenkron mimari, katı tip denetimi ve yerleşik interaktif Swagger UI (`/docs`). |
| **Borsa Entegrasyonu** | **CCXT** | ccxt (async) | KuCoin REST API ve WebSocket akışlarını resmi ve standart yönetir. |
| **Veri Analizi & Hesaplama** | **Pandas & NumPy** | Son stabil sürüm | OHLCV mum verileri, teknik indikatörler ve hızlı matris hesaplamaları. |
| **Test Altyapısı** | **Pytest** | pytest, pytest-cov | Fonksiyon bazlı bağımsız birim testleri ve otomatik test raporlama. |
| **Veritabanı** | **SQLite** | Dahili Python sqlite3 / aiosqlite | Emir geçmişi, bakiye logları ve yapılandırma için hafif ve kurulumsuz. |
| **Kullanıcı Arayüzü** | **Modern Web Dashboard** | HTML5 / CSS3 / JavaScript | Canlı grafikler, bakiye paneli ve kolay yönetim için responsive karanlık tema. |


---

## 4. Proje Dokümantasyon İndeksi (`docs/`)
- [PROJECT_ANALYSIS.md](file:///home/engintalay/projects/kuCoinAlSatBot/docs/PROJECT_ANALYSIS.md): Genel proje mimarisi ve 3 modülün işlevsel özet analizi.
- [GLOBAL_STANDARDS.md](file:///home/engintalay/projects/kuCoinAlSatBot/docs/GLOBAL_STANDARDS.md): Tüm ekranlarda geçerli genel arayüz (UI/UX) düzeni, tema, bildirimler ve ortak hata yönetim standartları.
- [MODULE_1_SPEC.md](file:///home/engintalay/projects/kuCoinAlSatBot/docs/MODULE_1_SPEC.md): Modül 1 (KuCoin Bağlantısı, .env Saklama ve Hesap Durumu) detaylı spesifikasyonu.
- [MODULE_2_SPEC.md](file:///home/engintalay/projects/kuCoinAlSatBot/docs/MODULE_2_SPEC.md): Modül 2 (Canlı Piyasa Fiyatları ve Strateji Analiz Altyapısı) detaylı spesifikasyonu.
- [MODULE_3_SPEC.md](file:///home/engintalay/projects/kuCoinAlSatBot/docs/MODULE_3_SPEC.md): Modül 3 (Al-Sat Emir Entegrasyonu, Risk ve Simülasyon) detaylı spesifikasyonu.
- [workflow.md](file:///home/engintalay/projects/kuCoinAlSatBot/docs/workflow.md): Proje iş akışı, geliştirme fazları ve kontrol listesi.

---

## 5. Doküman Değişiklik ve Tamamlanma Günlüğü (Change Log)

| Tarih / Saat | Yapılan Değişiklikler ve İşlem Özeti | Durum |
| :--- | :--- | :--- |
| **2026-09-17 20:52:48** | İlk 3 modüllü genel proje mimarisi ve analiz dokümanı hazırlandı. | Tamamlandı |
| **2026-09-17 20:57:40** | Modül 1 için .env dosyasında anahtar saklama kuralı eklendi. | Tamamlandı |
| **2026-09-17 20:58:43** | GLOBAL_STANDARDS.md referansı dokümantasyon indeksine dahil edildi. | Tamamlandı |
| **2026-09-17 21:07:56** | Kesinleşen teknoloji yığını tablosunda Python FastAPI standart olarak tescillendi. | Tamamlandı |
| **2026-09-17 21:35:00** | Review düzeltmeleri tamamlandı, proje iskeleti standardı `src/` olarak teyit edildi, tamamlama rozeti ve log tablosu eklendi. | Tamamlandı |
| **2026-09-17 22:06:00** | Rozet ayrımı (Tasarım %100 vs Kodlama %20) yapıldı ve güncellendi. | Onaylandı & Tamamlandı (%100) |
| **2026-09-17 22:50:00** | Modül 2 analizi `crypto_indicators_coding_agent_reference.md` doğrultusunda 10 katmanlı indikatör mimarisi, SMC, MTF ve 0-100 composite scoring motoru ile senkronize edilerek genişletildi. | Onaylandı & Genişletildi (%100) |
| **2026-09-20 01:00:00** | **Kullanım Kılavuzu Sayfası ve Bağlamsal Info Düğmeleri Eklendi**: Kullanıcı gereksinimi doğrultusunda ana sayfadan erişilebilir rehber sayfası/görünümü ve kritik arayüz öğelerine (Portföy, Mod, Panic Stop, Scoring, MTF, SMC, Emirler) öğretici `ℹ️` (Info) düğmeleri gereksinimi analiz dokümanına eklendi. | **Onaylandı & Genişletildi (%100) ✅** |


