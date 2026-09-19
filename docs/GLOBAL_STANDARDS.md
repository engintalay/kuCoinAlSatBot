# Genel Proje Özellikleri ve Standartlar Spesifikasyonu

> **Tasarım & Spesifikasyon Durumu:** %100 (Ayarlar, Çoklu Coin, Akıllı Paket Emir & Öneri Standartları Eklendi ✅) | **Kodlama & Test Durumu:** Temel Dashboard Tamamlandı (%100, 129/129 Test), Gelişmiş Arayüz Özellikleri Bekleniyor ⏳ | **Son Güncelleme:** 2026-09-20 01:05:00 (+03:00)

## 1. Dokümanın Amacı
Bu doküman, KuCoin Al-Sat Botu uygulamasının **tüm ekranlarında, modüllerinde ve genel yapısında** geçerli olacak standart kuralları, arayüz (UI/UX) standartlarını, genel sistem ayarlarını ve hata yönetim prensiplerini tanımlar.

---

## 2. Genel Uygulama Ayarları ve Temel Özellikler

### 2.1. Arayüz ve Tasarım Sistemi (UI/UX Design System)
Tüm ekranlarda tutarlı, modern ve göz yormayan bir kripto borsa paneli deneyimi sunulacaktır.

* **Tema**: Koyu Tema (Dark Mode) varsayılandır.
  * **Arka Plan**: Derin Koyu Kömür (`#0d1117`, `#161b22`)
  * **Kartlar / Paneller**: Cam efekti (Glassmorphism & Border `#30363d`)
  * **Yükseliş / Alış / Kar (Positive/Buy)**: Canlı Yeşil (`#00e676`)
  * **Düşüş / Satış / Zarar (Negative/Sell)**: Canlı Kırmızı (`#ff5252`)
  * **Vurgu / Bilgi (Accent/Info)**: Neon Mavi (`#2979ff`)
* **Tipografi**: Modern, yüksek okunabilirlikli sans-serif yazı tipleri (`Inter`, `Outfit` veya `Roboto Mono`).
* **Sayısal Formatlama Kuralları**:
  * **Fiyatlar**: Kripto çiftine göre hassas ondalık gösterimi (Örn: BTC için 2 basamak `70,050.50 USDT`, SHIB için 6-8 basamak `0.00001850 USDT`).
  * **Bakiyeler**: USDT tutarları her zaman 2 ondalık basamak ve binlik ayraçlı (`1,250.45 USDT`).

### 2.2. Bildirim ve Uyarı Sistemi (Toast & Modal Alerts)
Ekranın sağ üst köşesinde tüm modüllerden gelen canlı bildirimler gösterilecektir:
* 🟢 **Başarı (Success)**: *Emir gerçekleşti, KuCoin bağlantısı sağlandı.*
* 🟡 **Uyarı (Warning)**: *Bakiye sınırına yaklaşıldı, API yanıt süresi yüksek (High Latency).*
* 🔴 **Hata (Error)**: *API anahtarı geçersiz, İnternet bağlantısı koptu, Emir reddedildi.*

### 2.3. Bağlamsal Bilgilendirme ve Yardım Standartları (Info Düğmeleri & Kullanım Kılavuzu)
Kullanıcının analiz göstergelerini ve bot kontrollerini şeffaf biçimde öğrenmesini sağlamak için:
* **Kullanım Kılavuzu Sekmesi**: Sol gezinme menüsünde ve üst barda daima erişilebilir **"📖 Kullanım Kılavuzu"** bağlantısı bulunacaktır.
* **Bağlamsal Info Düğmeleri (`ℹ️`)**:
  * **Tasarım**: Neon Mavi (`#2979ff`) renkli, yuvarlak şık `ℹ️` butonu (`class="info-btn"`).
  * **Etkileşim**: Tıklandığında veya üzerine gelindiğinde (Hover / Click) açılan cam efektli (`glass`), yüksek kontrastlı bilgi balonu (`tooltip` / `modal popover`).
  * **Zorunlu Konumlar**:
    1. *Portföy / Bakiye Kartı*: Serbest vs kilitli nakit açıklaması.
    2. *İşlem Modu Rozeti*: Sanal (Paper) ile Gerçek (Live) mod farkı.
    3. *⛔ PANIC STOP Butonu*: Acil durum iptal ve kilitleme işlevi.
    4. *0-100 Bileşik Analiz Skoru*: 10 katmanlı ağırlıklandırma ve range filtresi.
    5. *MTF Hiyerarşisi*: 4H Rejim $\rightarrow$ 1H Setup $\rightarrow$ 15m Tetikleyici onay kuralı.
    6. *SMC Yapıları*: BOS, CHoCH ve FVG dengesizlik alanlarının anlamı.
    7. *Emir Formu*: Market/Limit farkı ve minimum işlem tutarı ($5 USDT).

---

## 3. Ekran Düzeni ve Ortak Arayüz İskeleti (Global Layout)

Tüm sayfa ve ekranlarda sabit kalacak **Ortak İskelet (Master Layout)** yapısı:

```
+-----------------------------------------------------------------------------------+
| HEADER: Logo | Portföy Özeti (USDT) | Aktif Koin Dropdown | Mod Switch | [PANİC STOP] |
+-----------------------------------------------------------------------------------+
|               |                                                                   |
|  SOL MENÜ     |                     ANA İÇERİK ALANI                              |
|  / DOCK       |  (Dashboard / Hesap / Analiz / Akıllı Emir / Kılavuz / Ayarlar)   |
|               |                                                                   |
|  - 🏠 Ana Sayfa|                                                                  |
|  - 👛 Hesap   |                                                                   |
|  - 📈 Analiz  |                                                                   |
|  - 📋 Emirler |                                                                   |
|  - 📖 Kılavuz |                                                                   |
|  - ⚙️ Ayarlar |                                                                   |
|               |                                                                   |
+-----------------------------------------------------------------------------------+
| FOOTER: WebSocket: CANLI | Gecikme: 35ms | Son Güncelleme: 20:58:14 | Canlı Log Stream|
+-----------------------------------------------------------------------------------+
```

### 3.1. Üst Bar (Global Header)
* **Logo & Uygulama Adı**: KuCoin Al-Sat Botu
* **Canlı Portföy Özeti**: Toplam Bakiye (USDT) ve serbest nakit
* **Aktif Koin Seçici (Symbol Selector)**: İzleme listesindeki koinler (BTC/USDT, ETH/USDT, SOL/USDT vb.) arasında tek tıkla geçiş sağlayan şık dropdown/hap butonlar.
* **Çalışma Modu Rozeti & Anahtarı**:
  * 🧪 **SIMULATION**: Sanal $10,000 USDT ile güvenli test (Tıklandığında hızlı geçiş onay penceresi açılır).
  * ⚡ **LIVE**: Gerçek KuCoin Spot hesabı ile canlı işlem.
* **Global Acil Durum (Panic Stop) Butonu**: Kırmızı renkte, tek tıkla tüm emirleri durduran ve pozisyonları güvene alan buton.

### 3.2. Alt Bar (Global Footer & Status Bar)
* **Bağlantı Durumu**: WebSocket bağlantı durumu (Yeşil / Kırmızı).
* **Gecikme Süresi (Latency Ping)**: KuCoin API yanıt süresi (ms).
* **Sistem Log Akışı**: Son gerçekleşen işlem veya sistem olayının tek satırlık canlı metin özeti.

### 3.3. Ayarlar Ekranı Standartları (`⚙️ Ayarlar` Görünümü)
Kullanıcının sistem parametrelerini kolayca yapılandırması için ayrılmış merkezi ayarlar paneli:
1. **Kripto Varlık & İzleme Listesi Yönetimi (Watchlist)**:
   - Aktif izlenen koinlerin etiketleri (Tag/Badge) ve yanlarında tek tıkla çıkarma (`✖`) butonu.
   - **Yeni Koin Ekle**: KuCoin spot çiftleri (`/api/v1/settings/symbols`) üzerinden anlık arama (autocomplete) kutusu ve `[ Ekle ]` butonu.
2. **İşlem Modu (Trading Mode)**:
   - Radyo/Switch butonu: `[🧪 SIMULATION (Paper)]` $\longleftrightarrow$ `[⚡ LIVE (KuCoin Real)]`.
   - Gerçek moda geçişte dikkat çekici risk uyarı modalı ("Gerçek para kullanılacaktır. Onaylıyor musunuz?").
3. **Varsayılan Risk ve Para Yönetimi Parametreleri**:
   - İşlem başına varsayılan USDT tutarı (Örn: $100 USDT veya serbest bakiyenin %5'i).
   - Varsayılan Zarar Kes (Stop-Loss) çarpanı (Örn: 1.5x ATR).
   - Varsayılan Kâr Al (Take-Profit) hedefleri (TP1: 1.5R, TP2: 3.0R).
   - Dinamik öneri bildirimlerini açma/kapatma toggle'ı.
4. **Kaydet Butonu**:
   - Değişiklikler tek tıkla kalıcı SQLite veritabanına kaydedilir ve başarı Toast'ı gösterilir.

### 3.4. Akıllı Paket Emir Bileşeni Standartları (Smart Bracket Order Form)
Analiz motorundan beslenen otomatik ve hatasız emir girişi standardı:
1. **Hazır Seviye Kartı (Trade Setup Summary)**:
   - Yön: 🟢 AL (Long) / 🔴 SAT (Short)
   - Giriş Fiyatı (Entry): Canlı tahta fiyatı veya pullback seviyesi.
   - Stop-Loss (SL): Otomatik ATR / Swing low seviyesi (kırmızı metin).
   - Take-Profit 1 (TP1): İlk hedef (%50 pozisyon - yeşil metin).
   - Take-Profit 2 (TP2): İkinci hedef (kalan %50 pozisyon - parlak yeşil metin).
   - Risk:Reward (R:R) Rozeti: Örn. `1:2.5 R:R`.
2. **Kullanıcı Girişi (Sadece USDT Tutarı)**:
   - Kullanıcı karmaşık ondalık miktar hesaplamaz; sadece girmek istediği **USDT Tutarını** yazar.
   - Hızlı seçim butonları: `[%25]`, `[%50]`, `[%100 Serbest Nakit]`.
3. **Canlı Risk / Kazanç Göstergeleri**:
   - Alınacak Kripto Miktarı (Coin Amount).
   - SL tetiklenirse Maksimum Risk ($ Zarar).
   - TP1 ve TP2 gerçekleşirse Potansiyel Net Kazanç ($ Kâr).
4. **Aksiyon Butonu**:
   - **"🚀 Akıllı Emri İlet (Giriş + TP1/TP2 + SL)"** butonu ile tek tıkla atomik paket iletimi.

### 3.5. Dinamik Öneri Motoru ve Bildirim Standartları (Recommendation Engine Cards)
Piyasa koşulları veya pozisyon hedefleri değiştikçe ekranda beliren akıllı tavsiye kutusu:
* **Tasarım**: Cam efektli (`glass`), mavi/mor neon çerçeveli dinamik uyarı kartı.
* **İçerik**:
  * `💡 Dinamik Öneri`: *"BTC/USDT fiyatı TP1 seviyesine ulaştı. Stop-Loss seviyenizi başabaş ($64,200) noktasına çekerek risksiz kâr kilitlemeniz önerilir."*
* **Aksiyonlar**:
  * `[ ✅ Hemen Uygula ]` (Yeşil buton: İlgili emri anında günceller).
  * `[ ✖ Yoksay ]` (Nötr buton: Öneriyi kapatır).

### 3.6. Açık Emir Düzenleme (Order Modification Modal)
Açık emirler tablosundaki her emir için "Düzenle" (Edit) fonksiyonu:
* Açılan modal üzerinde Fiyat, Miktar ve bağlı TP/SL seviyeleri anlık değiştirilebilir.
* "Değişiklikleri Kaydet" tıklandığında borsa üzerinde emir atomik olarak revize edilir.
   - İnternet veya KuCoin API kesintilerinde uygulama çökmeyecek (crash olmayacak).
   - Otomatik yeniden bağlanma (Auto-reconnect) mekanizması çalışacak (Her 5 saniyede bir dene).
2. **Kullanıcı Dostu Hata Mesajları**:
   - Karmaşık yazılım hataları (stack trace) yerine kullanıcıya açık Türkçe açıklama gösterilecek (Örn: `"300001: API saati uyumsuz"` yerine `"Bilgisayarınızın saati ile KuCoin sunucu saati arasında kayma var. Lütfen saatinizi güncelleyin."`).

### 4.2. Günlük Tutma (Logging Standards)
* Tüm uygulama olayları hem ekrandaki canlı konsola hem de yerel `logs/app.log` dosyasına yazılacaktır.
* Log seviyeleri: `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

---

## 5. Yazılım Geliştirme, Versiyon Kontrolü ve Test Standartları

### 5.1. Git Commit Standardı
* **Her Değişiklikte Commit**: Yapılan her mantıksal geliştirme, özellik ekleme veya hata düzeltmesinde mutlaka Git commit yapılacaktır.
* **Commit Mesaj Formatı (Conventional Commits)**:
  * `feat:` Yeni bir özellik eklendiğinde (Örn: `feat: add kucoin time sync check`)
  * `test:` Birim test eklendiğinde veya güncellendiğinde (Örn: `test: add unit test for balance calculator`)
  * `fix:` Hata düzeltildiğinde (Örn: `fix: handle websocket disconnect error`)
  * `docs:` Dokümantasyon değişikliklerinde (Örn: `docs: update module 1 spec`)
  * `refactor:` Kod iyileştirmelerinde (Örn: `refactor: optimize ticker cache`)

### 5.2. Birim Test (Unit Test) Standardı
* **Fonksiyon Başına Test Kuralı**: Geliştirilen her fonksiyonun mutlaka karşılık gelen en az bir birim testi (`unit test`) olacaktır.
* **Ayrı Test Klasörü**: Tüm test dosyaları projenin ana dizininde yer alan bağımsız `tests/` klasöründe tutulacaktır:
  ```
  tests/
  ├── test_module_1_account.py     # Modül 1 testleri (Bakiye, bağlantı, .env)
  ├── test_module_2_market.py      # Modül 2 testleri (Ticker, mum verisi, analiz)
  ├── test_module_3_orders.py      # Modül 3 testleri (Emirler, simülasyon, iptal)
  └── test_utils.py                # Yardımcı fonksiyon testleri
  ```
* **Mock Mekanizması**: Canlı borsa API'si test edilirken gerçek API limitlerini tüketmemek ve ağ kesintilerinden bağımsız test yapabilmek için harici API çağrıları testlerde mock'lanacaktır.

### 5.3. Otomatik Test Prosedürü ve Raporlama
* **Tek Komutla Otomatik Koşum**: Tüm testler tek bir komutla veya test çalıştırıcı script (`run_tests.sh`) ile otomatik koşturulacaktır.
* **Otomatik Raporlama**:
  * Konsol çıktısında geçen/kalan testler renkli olarak özetlenecektir.
  * Test prosedürü kod kapsamını (Coverage %) ölçecek ve test raporunu özetleyecektir.
  * Herhangi bir test başarısız olursa neden başarısız olduğu açık hata detayıyla raporlanacaktır.

---

## 6. Servis Mimarisi, REST API ve Swagger (OpenAPI) Standartları

### 6.1. REST API Standartları
* **Kaynak Odaklı Endpoint Mimarisi**: Tüm servisler standart REST API formatında geliştirilecek ve modüler öneklerle (`/api/v1/...`) ayrılacaktır:
  * `/api/v1/account/*` -> Modül 1 (KuCoin bağlantısı, bakiye ve yetkiler)
  * `/api/v1/market/*`  -> Modül 2 (Canlı ticker, mum verileri ve analiz sinyalleri)
  * `/api/v1/orders/*`  -> Modül 3 (Emir verme, açık emirler, iptal ve simülasyon)
* **Standart HTTP Metodları ve Durum Kodları**:
  * `GET`: Veri sorgulama (`200 OK`)
  * `POST`: Yeni emir veya işlem oluşturma (`201 Created` / `200 OK`)
  * `DELETE`: Açık emir iptali (`200 OK`)
  * Hata Durumları: `400 Bad Request` (geçersiz parametre), `401 Unauthorized` (geçersiz API Key), `429 Too Many Requests` (Rate limit), `500 Internal Server Error`.

### 6.2. Standart JSON Yanıt Şablonu
Tüm API servisleri önceden tahmin edilebilir, standart bir JSON zarfı (envelope) ile yanıt dönecektir:
```json
{
  "success": true,
  "data": {},
  "error": null,
  "timestamp": "2026-09-17T21:04:00Z"
}
```

### 6.3. Swagger (OpenAPI) Entegrasyonu ve Canlı Dokümantasyon
* **İnteraktif Swagger UI**: Servis ayağa kalktığında `/docs` adresinde tam teşekküllü, tarayıcı üzerinden doğrudan test edilebilen Swagger arayüzü sunulacaktır.
* **ReDoc Dokümantasyonu**: Alternatif temiz teknik doküman arayüzü `/redoc` adresinde hazır bulunacaktır.
* **Şema ve Model Doğrulama**: Tüm istek ve yanıt modelleri Pydantic şemaları ile tipleştirilecek; her parametrenin açıklaması, varsayılan değeri ve örnek veri seti (Example Payload) Swagger arayüzünde görünür olacaktır.
* **OpenAPI Şeması**: `/openapi.json` yolu üzerinden ham OpenAPI 3.0+ spesifikasyonu dışa aktarılabilecektir.

---

## 7. Teknoloji Yığını ve Dil Standardı (Backend: Python)

Uygulamanın sunucu ve iş mantığı (backend) katmanında resmi standart olarak **Python** dili ve ekosistemi belirlenmiştir:

* **Programlama Dili**: Python `3.14+`
* **Web / REST API Framework**: `FastAPI` (Yüksek performanslı, asenkron, tip korumalı ve dahili Swagger UI destekli)
* **ASGI Sunucusu**: `Uvicorn` (Standart asenkron web sunucusu)
* **Borsa ve Kripto Entegrasyonu**: `CCXT` (KuCoin REST API ve WebSocket asenkron istemcisi)
* **Veri Doğrulama & Şemalar**: `Pydantic v2` (Katı tip güvenliği ve otomatik API şema üretimi)
* **Veri Analizi & Matematiksel Modelleme**: `Pandas` & `NumPy` (Mum verileri, istatistiksel analizler ve indikatör hesaplamaları)
* **Test Çatısı**: `Pytest` + `pytest-asyncio` + `pytest-cov` (Asenkron birim testleri ve kod kapsamı raporlaması)
* **Paket & Bağımlılık Yönetimi**: `requirements.txt` ve izole Python sanal ortamı (`venv`)

---

## 8. Python Sanal Ortamı (venv), Yönetim Scriptleri ve Bağımlılık Standartları

### 8.1. Sanal Ortam (Virtual Environment - `venv`) Zorunluluğu
* Proje kesinlikle işletim sisteminin global Python ortamında değil, projenin kök dizininde yer alan izole **`.venv`** (veya `venv/`) sanal ortamında çalışacaktır.
* Bu sanal ortam `.gitignore` içerisine dahil edilerek kaynak kod reposundan hariç tutulacaktır.
* Tüm paket kurulumları ve script çalıştırmaları sanal ortam üzerinden yürütülecektir.

### 8.2. Standart Yönetim ve Çalıştırma Scriptleri
Geliştiricinin ve kullanıcının projeyi zahmetsizce kurabilmesi, ilk kez çalıştırabilmesi ve test edebilmesi için kök dizinde çalıştırılabilir kabuk scriptleri (`shell scripts`) bulundurulacaktır:

1. **`install.sh` (Kurulum Scripti)**:
   - Python 3.14+ varlığını doğrular.
   - `venv` sanal ortamını oluşturur (mevcut değilse).
   - Sanal ortamı aktive eder ve `pip` paket yöneticisini en güncel sürüme yükseltir.
   - `requirements.txt` içerisindeki tüm bağımlılıkları sanal ortama kurar.

2. **`first_run.sh` (İlk Çalıştırma ve Hazırlık Scripti)**:
   - İlk kez projeyi açan kullanıcı için tam hazırlık yapar.
   - `.env` dosyasını kontrol eder; yoksa `.env.example` üzerinden otomatik kopyalar ve kullanıcıyı uyarır.
   - `install.sh` scriptini çağırarak bağımlılıkların eksiksiz olduğunu doğrular.
   - Gerekli klasörleri (`logs/`, `tests/` vb.) hazır hale getirir.
   - İlk doğrulama testlerini (`run_tests.sh`) koşturur.

3. **`run.sh` (Uygulamayı Başlatma Scripti)**:
   - Sanal ortamı (`venv`) otomatik aktive eder.
   - `.env` dosyasının mevcudiyetini denetler.
   - FastAPI REST API ve Web Dashboard sunucusunu `uvicorn` ile ayağa kaldırır (Geliştirme modunda hot-reload aktif).
   - Terminalde kullanıcıya Swagger UI (`http://127.0.0.1:8000/docs`) ve Dashboard bağlantı linklerini gösterir.

4. **`run_tests.sh` (Otomatik Test ve Raporlama Scripti)**:
   - Sanal ortamı aktive eder.
   - `tests/` klasöründeki tüm birim testleri `pytest` ile çalıştırır.
   - Test başarı oranını, hata ayrıntılarını ve kod kapsamını (Coverage %) terminalde renkli olarak raporlar.

> [!IMPORTANT]
> **Scriptlerin Güncel Tutulması Kuralı**: Projenin her yeni aşamasında (Modül 1, 2, 3 ve sonrası) bu scriptlerin çalışırlığı kontrol edilecek, yeni ortam değişkenleri veya adımlar eklendiğinde scriptler eşzamanlı olarak güncellenecektir.

### 8.3. Bağımlılık (`requirements.txt`) Senkronizasyon Kuralı
* Projeye yeni bir Python kütüphanesi eklendiğinde, kütüphane sürümü güncellendiğinde veya bir kütüphane projeden çıkarıldığında **`requirements.txt` dosyası anında güncellenecektir**.
* Hiçbir kod değişikliği, `requirements.txt` güncellenmeden tamamlanmış sayılmayacaktır.

### 8.4. Çevre Değişkenleri (`.env`) ve Yapılandırma (`config.py`) Senkronizasyon Kuralı
* `.env.example` şablon dosyasında tanımlanan tüm konfigürasyon değişkenleri (`DEFAULT_TRADING_MODE`, `SIMULATION_INITIAL_BALANCE_USDT`, `HOST`, `PORT`, `LOG_LEVEL`, `LOG_TO_FILE`, `DEFAULT_SYMBOL`, `DEFAULT_TIMEFRAME` vb.) zorunlu olarak `src/config.py` içerisinde bir alan olarak okunmalı ve doğrulanmalıdır.
* `src/config.py` içerisinde `HOST` varsayılan değeri güvenlik standardı gereği `"127.0.0.1"` olarak ayarlanmalıdır (dış ağa kontrolsüz açılmayı önlemek için).
* Yapılandırmaya yeni bir değişken eklendiğinde hem `.env.example` hem de `src/config.py` eşzamanlı olarak güncellenecektir.

---


## 9. Eşzamanlı Geliştirme ve Çoklu AI (Multi-Agent) Koordinasyon Standartları

Bu projede birden fazla yapay zeka veya geliştirici eşzamanlı olarak çalışabileceğinden aşağıdaki çakışma önleme kuralları zorunludur:

1. **Değişiklik Öncesi Güncel Durum Kontrolü (Read Before Write)**:
   - Herhangi bir dosya değiştirilmeden önce dosyanın diskteki en son içeriği okunacak ve kontrol edilecektir.
   - Diğer AI'ın veya geliştiricinin eklediği işlevler, dosyalar (örn. `workflow.md`) ya da yapılandırmalar asla izinsiz silinmeyecek veya üzerine körü körüne yazılmayacaktır (no destructive overwrite).
2. **Git Durumu ve Çakışma Yönetimi**:
   - Her işlemden önce `git status` denetlenerek çalışma ağacında harici bir değişiklik olup olmadığı izlenecektir.
   - Harici bir değişiklik tespit edilirse bu değişiklik korunacak, yeni özellikler onunla uyumlu biçimde birleştirilecektir.
3. **Atomik ve Küçük Adımlarla İlerleme**:
   - Değişiklikler tek bir devasa blok halinde değil, izole ve doğrulanabilir küçük adımlarla yapılarak çakışma riski en aza indirilecektir.

---

## 10. Markdown (.md) Dokümantasyon Tamamlanma ve Loglama Standardı

Onaylanan, düzenlenen ve tamamlanan tüm Markdown (`.md`) dosyaları için aşağıdaki takip ve loglama kuralları zorunludur:

1. **İlk Satır / Başlık Göstergesi (Tamamlanma Yüzdesi ve Zamanı)**:
   - Her `.md` dosyasının ilk satırında (başlığın hemen altında veya ilk satırda) dokümanın yüzde kaç tamamlandığı (`%`) ve tamamlanma/onaylanma zamanı (`Tarih/Saat`) mutlaka belirtilecektir:
     ```markdown
     > **Tamamlanma Durumu:** %100 | **Son Güncelleme:** 2026-09-17 21:35:00 (+03:00)
     ```
2. **Dosya Sonu Detaylı İşlem ve Değişiklik Özeti (Footer Change Log)**:
   - Dokümanın en altında, o doküman için neler yapıldığı, hangi maddelerin eklendiği veya düzeltildiği adım adım detaylı olarak listelenecektir.

---

## 11. İnceleme (Review) Süreci ve `review/` Klasörü Standartları

Projenin kalitesini, mimari tutarlılığını ve kod güvenliğini denetlemek için bağımsız inceleme süreçleri uygulanır:

1. **`review/` Klasörü Standartı**:
   - Tüm inceleme, denetim ve geri bildirim raporları projenin kök dizinindeki `review/` klasöründe tutulacaktır.
   - Dosya adlandırma şablonu: `{rol}-AI_review_{YYYY-MM-DD_HH-mm-ss}.md` (Örn: `analiz-AI_review_2026-09-17_21-28-17.md`, `coding-AI_review_2026-09-17_21-28-17.md`).
2. **Roller ve Sorumluluk Alanları (Kalıcı Rol Ayrımı)**:
   - **Analiz AI (Bu Agent)**: Süreç boyunca **daima Analiz AI olarak kalacaktır**. Görevleri; mimari tasarım, analiz dokümantasyonu (`docs/`), veri modelleri, iş akışı ve küresel standartların yönetimi ve denetimidir. Kesinlikle doğrudan kaynak kod implementasyonu yapmaz.
   - **Coding AI (Diğer Agent)**: Projenin tüm kaynak kodlama (`src/`), birim test yazımı (`tests/`), çalıştırma betikleri (`scripts`) ve teknik implementasyonunu yürütür. Kod yazarken Analiz AI'ın belirlediği mimari ve spesifikasyonlara sadık kalır.
3. **Review Bulgularının Hayata Geçirilmesi Prosedürü**:
   - **Adım 1 (Oku)**: İlgili AI `review/` klasöründeki kendi raporunu dikkatle okur.
   - **Adım 2 (Planı Sun)**: Yapacağı düzeltmeleri açık ve net bir eylem planı olarak kullanıcıya sunar.
   - **Adım 3 (Onay Al)**: Kullanıcıdan açık onay almadan kesinlikle hiçbir dosyada değişiklik yapmaz.
   - **Adım 4 (Uygula & Commit)**: Onay alındıktan sonra düzeltmeleri uygular, doğrular ve Git'e commit eder.
4. **Doküman ve Rapor Dokunulmazlığı**:
   - Hiçbir geliştirici veya yapay zeka `review/` altındaki raporları izinsiz silemez veya değiştiremez.
5. **Kullanıcı 'review' Komutu Tetikleyicisi (Review Command Trigger)**:
   - Kullanıcı 'review' mesajı gönderdiğinde:
     - **Adım A**: Analiz AI, doğrudan `review/` klasöründeki dosyaları kontrol eder.
     - **Adım B**: Analiz AI'ın görev alanına giren (dokümantasyon, mimari, veri modelleri, standartlar, iş akışı) tüm review bulgularını inceler.
     - **Adım C**: Tespit edilen aksiyonları kullanıcıya maddeler halinde sunar ve onay ister.
     - **Adım D**: Kullanıcı onayından sonra düzeltmeleri uygular ve Git commit yapar.
6. **Aynı Review Dosyası Üzerinde Çalışma Kuralı (In-Place Review Update)**:
   - Yeni bir review raporu dosyası türetilmez; ilgili agent doğrudan **aynı mevcut review dosyası** üzerinde işlem yapar.
   - Dosyanın en üst satırına tamamlanma oranı ve zaman bilgisi yazılır:
     `> **Tamamlanma Durumu:** %100 | **Son Güncelleme:** 2026-09-17 21:45:00 (+03:00) | **Onay Durumu:** Onaylandı & Uygulandı ✅`
   - Dosyanın en altına yapılan işlemler, düzeltilen tutarsızlıklar ve çözüm detayları adım adım detaylı olarak eklenir.



---

## 12. Doküman Değişiklik ve Tamamlanma Günlüğü (Change Log)

| Tarih / Saat | Yapılan Değişiklikler ve Eklenen Standartlar | Durum |
| :--- | :--- | :--- |
| **2026-09-17 20:58:24** | Genel proje özellikleri, Master Layout, Dark Theme renk paleti, Toast ve hata yönetim standartları tanımlandı. | Tamamlandı |
| **2026-09-17 21:02:19** | Git commit zorunluluğu, fonksiyon başına unit test kuralı ve otomatik test raporlama standartları eklendi. | Tamamlandı |
| **2026-09-17 21:04:04** | REST API standartları, `/docs` Swagger UI ve ReDoc entegrasyon kuralları eklendi. | Tamamlandı |
| **2026-09-17 21:07:49** | Backend resmi dili olarak Python (FastAPI, CCXT, Pandas, Pytest) standardı tescillendi. | Tamamlandı |
| **2026-09-17 21:20:29** | Python sanal ortamı (`.venv`), yönetim scriptleri (`install.sh`, `first_run.sh`, `run.sh`, `run_tests.sh`) ve `requirements.txt` senkronizasyonu eklendi. | Tamamlandı |
| **2026-09-17 21:23:55** | Eşzamanlı geliştirme ve çoklu AI (multi-agent) çakışma önleme koordinasyon kuralları eklendi. | Tamamlandı |
| **2026-09-17 21:35:00** | Markdown (`.md`) dosyaları için ilk satır tamamlanma yüzdesi ve dosya sonu detaylı işlem logu standardı eklendi. | Tamamlandı |
| **2026-09-17 21:38:00** | İnceleme (Review) süreci, `review/` klasörü işleyişi ve kullanıcı onay prosedürü kuralları eklendi. | Tamamlandı |
| **2026-09-17 21:40:00** | Kullanıcı 'review' komutu tetikleyicisi ve Analiz AI otomatik kontrol protokolü eklendi. | Tamamlandı |
| **2026-09-19 22:00:00** | Modül 1 kodlama ve testleri tamamlandı (29/29 birim test başarıyla geçti). Rozet güncellendi. | Onaylandı & Tamamlandı (%100) |
| **2026-09-19 22:52:00** | Modül 2 Faz 2a temel veri katmanı tamamlandı (8 yeni test, toplam 37/37 test geçti). Rozet güncellendi. | Onaylandı & Tamamlandı (%100) |
| **2026-09-19 23:10:00** | Modül 2 Faz 2a çekirdek indikatörler tamamlandı (11 yeni test, toplam 48/48 test geçti). Rozet güncellendi. | Onaylandı & Tamamlandı (%100) |
| **2026-09-19 23:25:00** | Modül 2 Faz 2b analiz motoru, SMC, 0-100 puanlama ve MTF tamamlandı (26 yeni test, toplam 74/74 test geçti). Rozet güncellendi. | Onaylandı & Tamamlandı (%100) |
| **2026-09-19 23:48:00** | Modül 2 Hacim (RVOL, OBV, VWAP, MFI, CMF) ve Seviyeler (Pivots, Fib, Donchian) katmanları ile hacim puanlaması tamamlandı (10 yeni test, toplam 84/84 test geçti). Rozet güncellendi. | Onaylandı & Tamamlandı (%100) |
| **2026-09-20 00:10:00** | Modül 3 Emir Yönetimi & Paper Trading (16 test) ve Modül 2 Faz 2c ek momentum/türev katmanları (10 test) tamamlandı. Toplam **110/110 birim test %100 yeşil** geçti. Backend tamamen tamamlandı. | Onaylandı & Tamamlandı (%100) |
| **2026-09-20 00:40:00** | Adım 5 Frontend Dashboard (Dark glassmorphism SPA, `static/{index.html,css/style.css,js/app.js}`) ve 5 frontend testi tamamlandı. Toplam **115/115 birim test %100 yeşil** geçti. | Onaylandı & Tamamlandı (%100) |
| **2026-09-20 00:50:00** | Canlı WebSocket akışı (`/ws/live`), interaktif SVG mum grafiği, script senkronizasyonu ve `pytest-cov` (%76 coverage) eklendi. | Onaylandı & Tamamlandı (%100) |
| **2026-09-20 01:00:00** | Kullanıcı Talebi Standartları: Kullanım kılavuzu bağlantısı ve 7 kritik arayüz noktasına bağlamsal Info (`ℹ️`) düğmeleri standardı eklendi. | Onaylandı & Genişletildi (%100) |
| **2026-09-20 01:05:00** | **Ayarlar, Çoklu Coin, Akıllı Paket Emir & Dinamik Öneri Standartları Eklendi**: Master Layout'a `⚙️ Ayarlar` sekmesi eklendi. Çoklu coin yönetimi, simülasyon mod anahtarı, hazır seviyeli Smart Bracket Order formu, dinamik öneri kartları (`[ Uygula ]` / `[ Yoksay ]`) ve açık emir düzenleme modalı UI/UX standartları tanımlandı. | Onaylandı & Genişletildi (%100) |








