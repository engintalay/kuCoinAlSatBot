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
Proje; hesap doğrulama ve bakiye takibinden, canlı piyasa analizi ve göstergelere, akıllı otomatik seviye hesaplamalı paket emir yönetimine, çoklu kripto para (multi-coin) desteğine ve kapsamlı ayarlar paneline kadar uçtan uca bir al-sat otomasyonu sunar.

---

## 2. Modüler Mimari ve İşlevsel Kapsam

### Modül 1: KuCoin Bağlantısı, Kimlik Doğrulama ve Hesap Yönetimi
**Amaca Uygunluk**: Borsa API'sine güvenli bağlanmak, yetkileri doğrulamak, hesap bakiyesini ve portföy dağılımını canlı olarak sorgulamak.

#### İşlevsel Gereksinimler:
1. **API Anahtarı Güvenliği**:
   - KuCoin API Key, API Secret ve Passphrase bilgileri `.env` dosyasında saklanacaktır.
   - Kod içine veya versiyon kontrol sistemine (git) asla açık anahtar yazılmayacaktır.
2. **Bağlantı & İzin Doğrulama**:
   - API anahtarlarının geçerliliği (Ping/Time Sync) kontrol edilecek.
   - Hesabın işlem (Trade) ve bakiye okuma (General) izinlerine sahip olduğu teyit edilecek; güvenlik amacıyla Para Çekme (Withdraw) izninin **kapalı** olması gerektiği uyarısı verilecektir.
3. **Bakiye & Portföy Sorgulama**:
   - KuCoin Spot hesabındaki tüm kripto varlıklar (BTC, USDT, ETH vb.) listelenecektir.
   - Her varlık için `Serbest (Free)`, `Kilitli (Locked/In Orders)` ve `Toplam (Total)` miktarlar gösterilecektir.
   - Her varlığın anlık USDT karşılığı ve toplam portföy içindeki yüzdesel payı (`%`) hesaplanacaktır.

---

### Modül 2: Anlık Piyasa Verisi Akışı ve Çok Katmanlı Analiz Motoru
**Amaca Uygunluk**: KuCoin'den canlı fiyat (ticker), L2 derinlik ve mum (OHLCV) verilerini toplamak; 10 katmanlı indikatör ve Market Structure (SMC) feature'larını hesaplayarak çoklu zaman dilimi (MTF) destekli 0-100 Bileşik Puanlama Motoru (Composite Scoring Engine) ile doğrulanmış sinyaller ve otomatik işlem kurguları üretmek.

#### İşlevsel Gereksinimler:
1. **Canlı Fiyat ve Derinlik Akışı (Ticker & L2 Order Book)**:
   - Ayarlar/İzleme listesinde seçilen işlem çiftlerinin (BTC/USDT, ETH/USDT, SOL/USDT vb.) son fiyat, 24s hacim, değişim oranları ve alış-satış spread dengesizliğinin takibi.
2. **Geçmiş Mum (OHLCV) Yönetimi & Rolling Ring Buffer**:
   - Belirlenen zaman dilimlerinde (1m, 5m, 15m, 1h, 4h, 1d) 300-500 mumluk kayan önbellek.
   - Kapanmış mum (confirmed candle) ile geçici mum (intrabar provisional) ayrımı ve repainting/lookahead koruması.
3. **10 Katmanlı Analiz Motoru & Feature Engine**:
   - Trend (EMA, Supertrend, Ichimoku), Momentum (RSI, StochRSI, MACD), Güç (ADX, Choppiness), Hacim (RVOL, VWAP, CMF), Volatilite (ATR, Bollinger, Squeeze), Seviyeler (Pivots, Fib), Fiyat Hareketi/SMC (BOS, CHoCH, FVG, OB), Türevler (OI, Funding, CVD) ve MTF (4H rejim → 1H setup → 15m tetikleyici).
4. **Bileşik Puanlama (0-100 Score) & Gerekçelendirme Motoru**:
   - Boğa/Ayı puanlaması, sahte sinyal filtreleri ve insan tarafından okunabilir gerekçe/risk uyarısı çıktıları.
5. **Otomatik İşlem Kurgusu ve Seviye Hesaplama Motoru (Trade Setup Engine)**:
   - Analiz motoru sinyal ürettiğinde yalnızca skor değil, doğrudan emir formuna hazır seviye şablonu türetir:
     * **İşlem Yönü (Direction)**: Sinyale göre AL (Buy/Long) veya SAT (Sell/Short).
     * **Giriş Fiyatı (Entry Price)**: Anlık piyasa fiyatı (Market) veya en yakın FVG/EMA20/Pivot seviyesine geri çekilme (Limit Pullback).
     * **Zarar Kes (Stop-Loss - SL)**: Volatilite ve piyasa yapısına göre otomatik: `Entry - (1.5 * ATR_14)` veya son Swing Low / Donchian alt bandı.
     * **Kâr Al 1 (Take-Profit 1 - TP1)**: %50 pozisyon kapatma hedefi: `Entry + 1.5 * Risk` veya Pivot R1 / Fibonacci 0.618 seviyesi.
     * **Kâr Al 2 (Take-Profit 2 - TP2)**: Kalan %50 nihai hedef: `Entry + 3.0 * Risk` veya Pivot R2 / Fibonacci 1.0 seviyesi.
     * **Risk:Reward (R:R) Oranı**: Otomatik hesaplanır (örn. 1:2.4 R:R) ve arayüzde açıkça gösterilir.

---

### Modül 3: Akıllı Paket Emir Entegrasyonu, Emir Yönetimi ve Dinamik Öneri Motoru
**Amaca Uygunluk**: Manuel ve karmaşık emir girişleri yerine; analiz motorunun hazır seviyeleri üzerinden tek tıkla paket emir (Bracket Order: Giriş + TP1 + TP2 + SL) iletimi sağlamak, açık emirleri dinamik olarak düzenleyebilmek ve piyasa değişimlerinde akıllı güncelleme önerileri sunmak.

#### İşlevsel Gereksinimler:
1. **Otomatik Seviyeli Akıllı Paket Emir (Smart Bracket Order Execution)**:
   - Kullanıcı emir girişinde karmaşık fiyat veya miktar hesabı yapmak zorunda kalmaz.
   - Analiz motorunun belirlediği Giriş, TP1, TP2 ve Stop-Loss seviyeleri hazır olarak forma yüklenir.
   - **Kullanıcı Girdisi**: Kullanıcı yalnızca yatırmak istediği **USDT Tutarını** girer (veya `%25`, `%50`, `%100` bakiye butonlarını kullanır).
   - **Otomatik Miktar ve Risk/Kazanç Hesabı**:
     * Kripto Miktarı: `Amount = USDT_Tutarı / Giriş_Fiyatı` (KuCoin hassasiyetine göre formatlanır).
     * Maksimum Risk Tutarı: SL tetiklendiğinde kaybedilecek net USDT tutarı (`Risk = Amount * (Entry - SL)`).
     * Potansiyel Kâr Tutarı: TP1 ve TP2 gerçekleştiğinde kazanılacak net USDT tutarı.
   - **Tek Tıkla Paket İletim ("🚀 Akıllı Emri İlet")**:
     * Giriş emri (Market veya Limit) iletilir.
     * Giriş gerçekleştiğinde veya eşzamanlı olarak %50 pozisyon için TP1 Limit emri, %50 pozisyon için TP2 Limit emri ve tüm pozisyon için SL Stop-Market/Stop-Limit emri tek bir paket halinde borsaya ve simülatöre iletilir.
2. **Açık Emir Güncelleme ve Düzenleme (Order Modification / Amend)**:
   - Açık emirler listesinde her emrin yanında "İptal" butonunun yanı sıra **"Düzenle" (Edit)** butonu bulunur.
   - Kullanıcı emri iptal edip yeniden yazmak zorunda kalmadan fiyatı, miktarı veya bağlı TP/SL seviyelerini anında güncelleyebilir.
   - Borsa üzerinde KuCoin Amend API'si veya atomik iptal+yeniden iletim mekanizmasıyla icra edilir.
3. **Dinamik Güncelleme Öneri Motoru (Dynamic Order Recommendation Engine)**:
   - Sistem arka planda açık emirleri ve pozisyonları canlı fiyat ve analiz göstergelerine göre sürekli denetler.
   - Gerekli görüldüğünde kullanıcı arayüzüne anlık akıllı bildirim ve tek tıkla onaylama butonu sunar:
     * **Başabaş / Trailing Stop Önerisi**: Fiyat TP1 hedefine ulaştığında veya 1R kâra geçtiğinde: *"💡 Dinamik Öneri: BTC/USDT TP1 hedefine ulaştı. Stop-Loss seviyesini giriş fiyatına çekerek işlemi risksiz (Breakeven) hale getirmeniz önerilir. [Hemen Güncelle]"*.
     * **Giriş Fiyatı Revizyon Önerisi**: Bekleyen limit alış emrinde fiyat yukarı kırılım (Bullish BOS) yapıp uzaklaşırsa: *"💡 Dinamik Öneri: Piyasa yukarı yönlü kırıldı. Giriş seviyesini $X seviyesine revize etmeniz önerilir. [Hemen Güncelle]"*.
     * **Erken Çıkış / Stop Daraltma Önerisi**: Piyasa karakterinde tersine dönüş (CHoCH) veya aşırı şişme görülürse: *"⚠️ Risk Uyarısı: 15m zaman diliminde CHoCH (trend dönüşü) tespit edildi. Stop seviyesini daraltmanız önerilir. [Hemen Güncelle]"*.
     * Kullanıcı tek tıkla öneriyi emre uygulayabilir veya yoksayabilir.
4. **Emir Durumu Takibi & Geçmiş**:
   - Açık emirlerin doluluk oranı, gerçekleşen fiyatı ve durumu anlık izlenir.
   - Kapanan/dolan tüm emirler işlem geçmişinde (Order History) kâr/zarar ve komisyon bilgisiyle arşivlenir.
5. **Güvenlik, Panic Stop ve Simülasyon**:
   - **⛔ PANIC STOP**: Tek tıkla borsadaki tüm açık emirleri iptal eder, botun yeni işlem açmasını kilitler.
   - **Simülasyon Modu (Paper Trading)**: $10,000 sanal USDT ile gerçek tahta fiyatları üzerinde sıfır riskli test imkanı.

---

### Ayarlar ve Çoklu Kripto Varlık Yönetimi (Settings & Multi-Coin Management)
**Amaca Uygunluk**: Uygulamanın yalnızca tek bir koin (BTC) ile sınırlı kalmasını önlemek; kullanıcının dilediği kripto işlem çiftlerini izleme ve işlem listesine eklemesini sağlamak, simülasyon/canlı modunu kolayca değiştirebilmesini ve risk parametrelerini merkezi olarak yapılandırabilmesini sağlamak.

#### İşlevsel Gereksinimler:
1. **Ayarlar Ekranı (`⚙️ Ayarlar` Görünümü)**:
   - Sol menüde ve üst gezinme çubuğunda müstakil bir **"⚙️ Ayarlar"** sekmesi bulunacaktır.
   - Ayarlar paneli tüm yapılandırma tercihlerini kullanıcı dostu form elemanlarıyla sunacaktır.
2. **Çoklu Coin & İzleme Listesi Yönetimi (Multi-Coin Watchlist)**:
   - Sistem dinamik olarak birden çok işlem çiftini (Örn: BTC/USDT, ETH/USDT, SOL/USDT, AVAX/USDT, XRP/USDT vb.) destekleyecektir.
   - **Yeni Coin Ekleme**: KuCoin `/api/v1/market/symbols` listesinden arama ve seçim yapılarak izleme listesine yeni çiftler eklenebilecektir.
   - **Coin Silme / Düzenleme**: Kullanıcı istemediği çiftleri listeden çıkarabilecektir.
   - **Aktif İşlem Çifti Seçimi**: Kullanıcı arayüzün her yerinde (Dashboard, Analiz, Emirler) tek bir tıkla veya açılır menüden (Dropdown/Pills) aktif koini değiştirebilecek; mum grafiği, canlı fiyat ve analiz göstergeleri seçilen koine anında senkronize olacaktır.
3. **Simülasyon / Canlı Mod Geçişi (Trading Mode Switcher)**:
   - Ayarlar ekranında ve Header alanında açık, görsel bir mod değiştirici anahtar (Switch / Toggle) yer alacaktır.
   - `🧪 SIMULATION (Paper Trading)` ile `⚡ LIVE (Gerçek KuCoin Hesabı)` modları arasında kolayca geçiş yapılabilecektir.
   - Canlı moda geçerken kullanıcının gerçek parayla işlem yapılacağını onayladığı güvenlik uyarısı (Confirmation Dialog) görüntülenecektir.
4. **Risk ve Para Yönetimi Parametreleri**:
   - Varsayılan işlem tutarı (USDT veya portföy %'si, örn. %5).
   - Varsayılan Stop-Loss ATR çarpanı (Örn: 1.5x ATR).
   - Varsayılan Kâr Al (Take-Profit) hedefleri (TP1 için 1.5R, TP2 için 3.0R).
   - Dinamik öneri motoru bildirimlerinin açılıp kapatılması.
5. **Kalıcılık (Persistence)**:
   - Kullanıcının kaydettiği ayarlar SQLite veritabanında (`settings` tablosu) saklanacak ve uygulama yeniden başlatıldığında aynen korunacaktır.

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
| **2026-09-20 01:05:00** | **Ayarlar Ekranı, Çoklu Coin, Akıllı Paket Emir & Dinamik Öneri Motoru Eklendi**: Ayarlar sekmesi (`⚙️ Ayarlar`), dinamik çoklu coin izleme/işlem listesi (Watchlist & KuCoin symbols), analiz motorundan otomatik Entry/TP1/TP2/SL seviye hesaplamalı akıllı paket emir iletimi ("🚀 Akıllı Emri İlet"), açık emir düzenleme (Edit/Amend) ve canlı piyasa durumuna göre akıllı güncelleme tavsiyeleri üreten Dinamik Öneri Motoru gereksinimleri analiz dokümanına eklendi. | **Onaylandı & Genişletildi (%100) ✅** |



