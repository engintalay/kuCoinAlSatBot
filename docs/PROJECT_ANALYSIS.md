# KuCoin Al-Sat Botu - Proje Analiz ve Tasarım Dokümanı

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

### Modül 2: Anlık Piyasa Verisi Akışı ve Analiz Altyapısı
**Amaca Uygunluk**: KuCoin'den canlı fiyat verilerini çekmek, mum (OHLCV) verilerini toplamak ve gelecekte eklenecek stratejiler için analiz altyapısını hazır tutmak.

#### İşlevsel Gereksinimler:
1. **Canlı Fiyat Akışı (Ticker & WebSocket)**:
   - Seçilen işlem çiftlerinin (Örn: BTC/USDT, ETH/USDT, KCS/USDT) son fiyat, 24s hacim ve değişim oranlarını çekme.
2. **Geçmiş Mum (OHLCV) Verisi Çekme**:
   - Belirlenen zaman dilimlerinde (1m, 5m, 15m, 1h, 4h, 1d) mum verilerinin çekilmesi.
3. **Esnek Analiz Motoru Altyapısı**:
   - Stratejilerin tak-çıkar (pluggable) mimaride çalışabilmesi için analiz veri modülü.
   - *Not: Strateji mantığı ve indikatör detayları bu fazdan sonra belirlenecektir.*

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
