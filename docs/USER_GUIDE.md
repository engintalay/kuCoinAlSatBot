# KuCoin Al-Sat Botu — Kapsamlı Kullanım Kılavuzu & Sistem Analizi

> **Sürüm:** 2.1 (Çok Kullanıcılı Kimlik Doğrulama, TOTP 2FA, Şifreli Kasa, Çoklu Piyasa & Gelişmiş SMC Entegreli)  
> **Erişim Adresi:** `http://localhost:9876` (veya `http://0.0.0.0:9876`)  
> **Temel İlke:** *"Geliştirme ve Analiz Beraberdir."* Tüm algoritmik kararlar, mimari gerekçeleri ve piyasa dinamikleriyle açıklanır.

---

## İçindekiler
1. [Sistem Mimarisi ve Tasarım İlkeleri](#1-sistem-mimarisi-ve-tasarım-ilkeleri)
2. [Hızlı Başlangıç ve İlk Admin Kullanıcı Kurulumu](#2-hızlı-başlangıç-ve-ilk-admin-kullanıcı-kurulumu)
3. [Kimlik Doğrulama, 2FA (TOTP) ve Kasa (CryptoVault) Mimarisi](#3-kimlik-doğrulama-2fa-totp-ve-kasa-cryptovault-mimarisi)
4. [İşlem Modları (Simülasyon vs. Canlı)](#4-işlem-modları-simülasyon-vs-canlı)
5. [Çoklu Piyasa Desteği: Spot, Margin ve Futures](#5-çoklu-piyasa-desteği-spot-margin-ve-futures)
6. [Çoklu Cüzdan, Kullanıcı İzolasyonu ve Bakiye Kırılımı](#6-çoklu-cüzdan-kullanıcı-izolasyonu-ve-bakiye-kırılımı)
7. [Çoklu Zaman Dilimi (MTF) ve Sub-15m Motoru](#7-çoklu-zaman-dilimi-mtf-ve-sub-15m-motoru)
8. [Teknik ve Kurumsal Piyasa Analizi (SMC & 10 Katman)](#8-teknik-ve-kurumsal-piyasa-analizi-smc--10-katman)
9. [Eğitici 4-Boyutlu Analiz Tablosu](#9-eğitici-4-boyutlu-analiz-tablosu)
10. [Dinamik Mum Grafiği ve Otomatik Seviyeler](#10-dinamik-mum-grafiği-ve-otomatik-seviyeler)
11. [Akıllı Paket Emir (Bracket Order) ve R:R Risk Yönetimi](#11-akıllı-paket-emir-bracket-order-ve-rr-risk-yönetimi)
12. [Açık Pozisyonlar ve Canlı Emir Takip Ekranı](#12-açık-pozisyonlar-ve-canlı-emir-takip-ekranı)
13. [Acil Durum (Panic Stop) ve Hata Teşhis & Raporlama](#13-acil-durum-panic-stop-ve-hata-teşhis--raporlama)
14. [Yönetici Konsol Komutları Referansı (CLI)](#14-yönetici-konsol-komutları-referansı-cli)

---

## 1. Sistem Mimarisi ve Tasarım İlkeleri

KuCoin Al-Sat Botu; modern, asenkron ve yüksek performanslı Python (FastAPI + AsyncIO + CCXT) altyapısı üzerine inşa edilmiş, hafif ve hızlı çalışan dark glassmorphism arayüze (Vanilla HTML5/CSS3/ES6+) sahip profesyonel bir ticaret ve analiz terminalidir.

```
                    ┌────────────────────────────────────────────────────────┐
                    │            Kullanıcı Arayüzü (Web Dashboard)          │
                    │   HTML5 / Glassmorphism CSS3 / ES6+ Responsive SPA     │
                    │           [ /login  ──►  / (Korumalı Panel) ]          │
                    └───────────────┬────────────────────────┬───────────────┘
                                    │ REST API               │ WebSocket
                                    ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                FastAPI Uygulama Çekirdeği                              │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│  [Auth Guard Middleware] ──► Oturum Doğrulama (HttpOnly Session Cookie)                 │
│  [CryptoVault & UserStore] ──► AES-128 (Fernet) ile Şifrelenmiş Borsa API Anahtarları   │
│  [ExchangeClientFactory] ──► Her Kullanıcı İçin İzole Account / Orders İstemcileri      │
├──────────────────────────┬─────────────────────────────┬────────────────────────────────┤
│    Modül 1: Hesap        │     Modül 2: Piyasa & SMC   │      Modül 3: Emir Motoru      │
│  - Çoklu Cüzdan Denetimi │  - 10 Katmanlı Puanlama     │  - Spot / Margin / Futures     │
│  - Yetki & Güvenlik      │  - MTF (1m -> 1d) Hiyerarşi │  - Akıllı Paket (Bracket)      │
│  - Canlı Bakiye & Pay    │  - Dinamik Seviye Motoru    │  - Pre-Trade Risk Denetimi     │
│  - Simülasyon Cüzdanı    │  - Eğitici Karar Tablosu    │  - Canlı PnL & Pozisyon Takibi │
└─────────────┬────────────┴──────────────┬──────────────┴────────────────┬───────────────┘
              │                           │                               │
              ▼                           ▼                               ▼
       KuCoin REST/WS             KuCoin Tahta / Ticker            KuCoin Trading Gateway
      (ccxt.pro / async)         (Spot / Margin / Futures)         (Limit / Market / Cancel)
```

### Temel Tasarım İlkeleri:
1. **Çok Kullanıcılı İzolasyon (Tenant Isolation):** Her kullanıcının borsa anahtarları, emirleri, açık pozisyonları ve izleme listesi (`settings`) birbirinden tamamen izoledir.
2. **Kriptografik Güvenlik (Master Key & Fernet):** Borsa API anahtarları veritabanında asla açık metin tutulmaz; simetrik master key kasası (`CryptoVault`) ile şifrelenir.
3. **Önce Sermaye Güvenliği (Capital Protection First):** Para çekme (Withdraw) yetkisi sistem tarafından kesinlikle engellenir ve reddedilir. Pre-trade risk kontrolleri bakiyenizi aşan veya kontrolsüz emirleri bloklar.
4. **Geliştirme ve Analiz Birlikteliği:** Sistemdeki hiçbir gösterge veya emir tek başına kuru bir sayıdan ibaret değildir; gerekçesi, sebebi, olası piyasa sonucu ve korunma tavsiyesiyle birlikte sunulur.
5. **Sıfır Dış Bağımlılık (Frontend):** Ağır JavaScript framework'leri (React, Angular, Vue vb.) yerine doğrudan optimize edilmiş, tarayıcıda anında yüklenen ve WebSocket ile hafif haberleşen yerel ES6 mimarisi kullanılmıştır.

---

## 2. Hızlı Başlangıç ve İlk Admin Kullanıcı Kurulumu

### Adım 1: Gereksinimler
- Python 3.10 veya üzeri (Sistemde Python 3.11+ tavsiye edilir)
- Linux / macOS / WSL2 ortamı
- Terminal ve Git

### Adım 2: Kurulum
Proje kök dizininde bulunan kurulum scriptini çalıştırın:
```bash
chmod +x install.sh first_run.sh run.sh run_tests.sh
./install.sh
```
Bu script sanal ortamı (`.venv`) kurar ve tüm bağımlılıkları (`requirements.txt`) yükler.

### Adım 3: `.env` Yapılandırması
Proje kök dizinindeki `.env` dosyasını oluşturun veya düzenleyin:
```env
# İsteğe bağlı: Sabit bir Master Key belirlemek isterseniz (boş bırakılırsa '.master_key' otomatik üretilir)
MASTER_KEY=

# KuCoin API Anahtarlarınız (İsteğe bağlı - Admin oluşturulurken otomatik aktarılabilir)
KUCOIN_API_KEY="api_anahtariniz"
KUCOIN_API_SECRET="api_gizli_anahtariniz"
KUCOIN_API_PASSPHRASE="api_parolaniz"
DEFAULT_TRADE_MODE="paper"  # "paper" (varsayılan) veya "live"
PORT=9876
```

> [!CAUTION]
> **Kritik Güvenlik Kuralı:** KuCoin API anahtarınızı oluştururken **"Withdrawal (Para Çekme)" iznini KESİNLİKLE İŞARETLEMEYİN**. Botun çalışması için sadece **"General" (Görüntüleme)** ve **"Spot/Margin/Futures Trade" (İşlem)** yetkileri yeterlidir. Ayrıca KuCoin panelinden sabit IP adresinizi beyaz listeye (IP Whitelist) ekleyin.

### Adım 4: İlk Admin Kullanıcısını Oluşturma
Sistemde self-registration (dışarıdan rastgele kayıt) kapalıdır. İlk yönetici hesabı sunucu terminalinden oluşturulur:
```bash
source .venv/bin/activate
python -m src.auth.cli setup
```
1. Konsolda **kullanıcı adı** ve **şifre** (en az 8 karakter) belirleyin.
2. Sistem şifrenizi `bcrypt` ile hash'leyip `role="admin"` olarak kaydeder.
3. Varsa `.env` dosyasındaki KuCoin anahtarlarınız master key ile şifrelenerek doğrudan bu admin hesabına aktarılır.
4. Çıktıda verilen **2FA (TOTP) Secret** kodunu veya `otpauth://` bağlantısını Google Authenticator, Authy veya 1Password uygulamanıza ekleyin.

### Adım 5: Botu Başlatma ve Giriş
```bash
./run.sh
```
Tarayıcınızda `http://localhost:9876` adresini açın:
1. Sistem sizi otomatik olarak `http://localhost:9876/login` sayfasına yönlendirir.
2. Kullanıcı adı, şifre ve Authenticator uygulamanızın ürettiği 6 haneli 2FA kodunu girin.
3. 12 saatlik güvenli HttpOnly oturumu ile kontrol paneline erişin.

---

## 3. Kimlik Doğrulama, 2FA (TOTP) ve Kasa (CryptoVault) Mimarisi

Bot, finansal varlıkları yöneten bir yazılım olduğu için kurumsal düzeyde çok katmanlı savunma mimarisiyle donatılmıştır:

```
[İstemci / Tarayıcı] 
        │ (POST /api/v1/auth/login)
        ▼
[AuthManager]
        ├── 1. Parola Kontrolü (bcrypt hash doğrulama)
        ├── 2. Kademeli Brute-Force Denetimi (LockoutManager)
        ├── 3. İki Faktörlü Doğrulama (pyotp RFC 6238 TOTP)
        └── 4. HttpOnly Session Cookie (XSS korumalı opak ID)
                 │
                 ▼
[UserStore & CryptoVault (Fernet AES-128)]
        ├── users tablosu: Kullanıcı kimliği & TOTP secret
        ├── sessions tablosu: Aktif 12 saatlik oturumlar
        └── user_api_keys tablosu: Şifreli KuCoin API Anahtarları
```

### 1. Parola Güvenliği ve 2FA (TOTP)
- Kullanıcı parolaları geri döndürülemez `bcrypt` tuzlamasıyla (salt) saklanır.
- RFC 6238 standardına uygun 30 saniyelik zaman tabanlı tek kullanımlık şifreler (TOTP) zorunludur.

### 2. Kademeli Brute-Force Koruması (Lockout Stages)
Kötü niyetli parola denemelerine karşı `LockoutManager` 3 aşamalı savunma uygular:
- **Aşama 1 (3-4 Hatalı Deneme):** Cevap süresi yapay olarak geciktirilir (progressive sleep).
- **Aşama 2 (5-9 Hatalı Deneme):** Hesap geçici olarak 15 dakika kilitlenir.
- **Aşama 3 (10+ Hatalı Deneme):** Hesap güvenlik amacıyla tamamen devre dışı bırakılır (`is_disabled = 1`). Yalnızca sunucu yöneticisi CLI üzerinden kilidi kaldırabilir.
*(Not: Geliştirme kolaylığı için `127.0.0.1` yerel ağ isteklerinde lockout kilit süresi esnetilir).*

### 3. Master Key ve Kripto Kasa (`CryptoVault`)
Kullanıcıların borsa anahtarları veritabanında asla açık tutulmaz.
- Kök dizindeki `.master_key` dosyasında saklanan 32 baytlık Fernet anahtarı kullanılır.
- Bu anahtar dosyasının dosya izinleri `0600` (sadece sahip okuyabilir) olarak kilitlenir.
- `.master_key` dosyasını mutlaka güvenli bir yerde yedekleyiniz; bu dosya kaybolursa veritabanındaki borsa anahtarları çözülemez.

---

## 4. İşlem Modları (Simülasyon vs. Canlı)

Sistem iki ayrı operasyonel çalışma modunu destekler:

| Özellik | 🧪 SIMULATION (Paper Trading) | ⚡ LIVE KUCOIN |
|---------|------------------------------|----------------|
| **Risk Seviyesi** | Sıfır Risk | Gerçek Sermaye Riski |
| **Bakiye** | $10,000 Sanal USDT | KuCoin Hesabınızdaki Gerçek Bakiye |
| **Piyasa Fiyatı** | KuCoin Canlı L1/L2 Tahtası | KuCoin Canlı L1/L2 Tahtası |
| **Emir Eşleşmesi** | Gerçekçi Spread ve Komisyon Simülasyonu | Borsada Gerçek Emir İletimi |
| **Varsayılan Durum**| Evet (Sistem bu modda açılır) | Kullanıcı Onayı Gerektirir |

### Güvenli Mod Değiştirme Kalkanı:
Kazara canlı moda geçişi önlemek için arayüzde çift aşamalı onay penceresi bulunur:
1. Header'daki `🧪 SIMULATION` rozetine veya `⚙️ Ayarlar` sekmesindeki mod seçicisine tıklayın.
2. Açılan onay penceresinde uyarıyı onayladığınızda sistem canlı moda geçer.
3. Mod değişimi gerçekleştiğinde açık emir ve bakiye panelleri anında ilgili ortama adapte edilir.

---

## 5. Çoklu Piyasa Desteği: Spot, Margin ve Futures

Bot, KuCoin'in sunduğu üç farklı piyasa yapısıyla tam entegre çalışır:

### 1. Spot Piyasa
- **İşlem Mantığı:** Doğrudan baz para birimini (örn. BTC) quote para birimi (USDT) karşılığında takas eder.
- **Risk:** Kaldıraç yoktur, tasfiye (likidasyon) riski bulunmaz.
- **Kullanım:** Uzun vadeli spot yatırımlar ve risksiz akıllı bracket testleri için idealdir.

### 2. Margin (Marjin) Piyasa (Cross & Isolated)
- **İşlem Mantığı:** Teminatınız karşılığında borsadan borç alınarak kaldıraçlı spot işlem yapılır.
- **Özellik:** Düşen piyasada borçlanarak açığa satış (Short) veya yükselen piyasada borçlanarak kaldıraçlı alış (Long) açılabilir.
- **Güvenlik:** Teminat oranı KuCoin risk protokolleri çerçevesinde izlenir.

### 3. Futures (Vadeli İşlemler - USDT-M)
- **İşlem Mantığı:** KuCoin sürekli vadeli işlem sözleşmeleridir. Standart sembol biçimi `BASE/QUOTE:SETTLE` (örnek: `BTC/USDT:USDT`) şeklindedir.
- **Özellikler:**
  - **Kaldıraç:** Sözleşme büyüklüğüne göre seçilen kaldıraç oranı (1x - 100x).
  - **Fonlama Oranı (Funding Rate):** Spot ve vadeli fiyat farkını dengeleyen 8 saatlik fonlama ödemeleri analiz motoruna dahil edilir.
  - **Açık Pozisyon (Open Interest):** Vadeli tahtadaki açık kontrat sayısı ve kurumsal likidite yoğunluğu takip edilir.
  - **Tasfiye Fiyatı (Liquidation Price):** Teminatın sıfırlanacağı risk sınırı mum grafiğinde mor çizgiyle net olarak gösterilir.

---

## 6. Çoklu Cüzdan, Kullanıcı İzolasyonu ve Bakiye Kırılımı

KuCoin borsasında tek bir hesap altında bağımsız cüzdan hesapları bulunur. Sistem, oturum açan kullanıcının şifreli anahtarlarını çözerek yalnızca o kullanıcıya ait bakiye kırılımını listeler:

```
┌─────────────────────────────────────────────────────────────┐
│               KuCoin Varlık Cüzdanları Dağılımı             │
├─────────────────┬──────────────────┬────────────────────────┤
│ Ana Hesap       │ Funding Account  │ Para yatırma / çekme   │
│ İşlem Hesabı    │ Trade Account    │ Spot emir bakiyeleri   │
│ Marjin Hesabı   │ Margin Account   │ Borç & teminat fonları │
│ Vadeli Hesabı   │ Futures Account  │ Vadeli sözleşme teminat│
└─────────────────┴──────────────────┴────────────────────────┘
```

Arayüzdeki **"Detaylı Hesap Kırılımı"** paneli sayesinde:
- Hangi cüzdanda kaç USDT serbest (free), kaç USDT emirde kilitli (used) olduğu anlık listelenir.
- Bir piyasada emir verirken yetersiz bakiye uyarısı alırsanız, varlıklarınızın hangi cüzdanda kaldığını tek bakışta görebilirsiniz.
- Kullanıcı İzolasyonu sayesinde bir kullanıcının emirleri ve bakiyesi diğer kullanıcılar tarafından kesinlikle görüntülenemez.

---

## 7. Çoklu Zaman Dilimi (MTF) ve Sub-15m Motoru

Tek bir zaman dilimine bakarak işlem yapmak en sık karşılaşılan tuzaklardan biridir. Bot, 8 farklı zaman diliminde (`1m, 3m, 5m, 15m, 30m, 1h, 4h, 1d`) piyasayı tarar ve hiyerarşik MTF prensibini uygular:

```
[1D / 4H]  Makro Rejim Katmanı     ──►  Piyasa trendi (Boğa / Ayı / Yatay)
   │
[1H / 30m] Kurulum Katmanı (Setup) ──►  Likidite havuzları, FVG & Destek/Direnç
   │
[15m / 5m] Tetikleyici (Trigger)   ──►  CHoCH, swing kırılımları & Giriş sinyali
   │
[3m / 1m]  Mikro Scalp Katmanı    ──►  Hassas giriş optimizasyonu & Spread takibi
```

> [!TIP]
> **Altın Kural:** 4 saatlik trend düşüş yönündeyken 5 dakikalık grafikte gelen alım sinyali sadece zayıf bir tepki yükselişidir. Sistem, üst zaman dilimleri onay vermediğinde skorunu düşürerek sizi ters pozisyonda kalmaktan korur.

---

## 8. Teknik ve Kurumsal Piyasa Analizi (SMC & 10 Katman)

Analiz motoru, fiyatı 10 bağımsız analitik katmanda inceler ve 0-100 arasında normalize edilmiş bileşik skor üretir:

1. **Trend Katmanı:** EMA 20 / 50 / 200 dizilimi, Supertrend, Ichimoku Kumo Bulutu ve Parabolic SAR.
2. **Momentum Katmanı:** RSI (14), MACD histogramı, StochRSI, ROC ve Williams %R.
3. **Volatilite Katmanı:** Bollinger Bant genişliği, Keltner Kanalları ve TTM Squeeze tespiti.
4. **Güç Katmanı:** ADX (Trend gücü), Aroon Osilatörü ve Choppiness Index (Trend vs. Yatay piyasa).
5. **Kurumsal Piyasa Yapısı (SMC - Smart Money Concepts):**
   - **BOS (Break of Structure):** Trend yönündeki yeni tepe veya dip kırılımı.
   - **CHoCH (Change of Character):** Trend dönüşünün ilk teknik habercisi.
   - **FVG (Fair Value Gap):** Fiyatın dengesiz hareket ettiği ve sonradan doldurulmak istenen kurumsal fiyat boşlukları.
   - **Order Block (OB):** Kurumsal alım veya satım emirlerinin kümelendiği bloklar.
6. **Hacim Dinamikleri:** RVOL (Göreceli hacim patlaması), OBV, MFI (Money Flow), CMF (Chaikin Money Flow) ve Volume Profile POC.
7. **Kritik Seviyeler:** Klasik Pivot Noktaları, Fibonacci Düzeltme Seviyeleri ve Donchian Kanalları.
8. **Türev Katmanı:** KuCoin Futures Funding Rate (Fonlama), Open Interest (OI) ve Long/Short likidasyon yoğunluğu.
9. **Makro Piyasa Rejimi (Katman 9):** CoinGecko entegrasyonu ile BTC Dominansı (BTC.D), Toplam Kripto Piyasa Değeri (Total MCap), Stablecoin Dominansı ve Altseason Index.
10. **Duyarlılık ve Risk Süzgeci:** Aşırı alım/satım tuzakları ve ani haber riskleri filtresi.

---

## 9. Eğitici 4-Boyutlu Analiz Tablosu

Klasik analiz araçları yalnızca "RSI: 78" gibi teknik rakamlar verip yatırımcıyı yalnız bırakır. KuCoin Al-Sat Botu ise her sinyali 4 temel boyutta açıklar:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        Eğitici Karar Tablosu (Analiz Ekranı)                           │
├──────────────────┬─────────────────┬──────────────────┬────────────────┬───────────────┤
│ İndikatör &      │ Neden Oldu?     │ İndikatör Neyi   │ Neye Sebep     │ Korunma       │
│ Sinyal           │                 │ Gösterir?        │ Olur?          │ Tavsiyesi     │
├──────────────────┼─────────────────┼──────────────────┼────────────────┼───────────────┤
│ RSI: 78.4        │ Son 14 mumda    │ Alıcı ve satıcı  │ Kâr realizas-  │ Yeni long     │
│ (Aşırı Alım)     │ agresif alım    │ güç dengesini    │ yonu ve geri   │ açmayın, stop │
│                  │ ile tepe yapıldı│ 0-100 ölçer      │ çekilme dalgası│ seviyesini çek│
├──────────────────┼─────────────────┼──────────────────┼────────────────┼───────────────┤
│ SMC: CHoCH       │ Yükselen trend- │ Fiyat yapısının  │ Kısa vadeli    │ Alış pozisyo- │
│ (Düşüş Yönlü)    │ teki son dip    │ karakter değiş-  │ düşüş trendinin│ nunu kapatın  │
│                  │ aşağı kırıldı   │ tirdiğini gösterir│ başlaması     │ veya hedge et │
└──────────────────┴─────────────────┴──────────────────┴────────────────┴───────────────┘
```

Bu yapı sayesinde hem acemi kullanıcılar indikatörlerin piyasadaki gerçek karşılığını öğrenir hem de tecrübeli trader'lar gerekçelendirilmiş verilerle karar alır.

---

## 10. Dinamik Mum Grafiği ve Otomatik Seviyeler

Analiz ekranındaki interaktif SVG grafiği, seçilen sembolün ve zaman diliminin son mumlarını çizer. Aynı zamanda sistemin algoritmik olarak belirlediği seviyeleri görselleştirir:

- 🔵 **Giriş Seviyesi (Entry Price):** Fiyat yapısı ve kırılım teyidine göre işleme girilecek seviye.
- 🟢 **Hedef 1 (TP1 - Take Profit %50):** İlk direnç veya likidite havuzu. Pozisyonun yarısı burada realize edilerek işlem risksiz hale getirilir.
- 🟢 **Hedef 2 (TP2 - Take Profit %50):** Trendin ana hedefi. Kalan %50 pozisyon burada kapatılır.
- 🔴 **Stop Loss (SL - %100):** Analizin geçersiz kaldığı nokta. Sermayeyi korumak adına tüm pozisyon burada stop edilir.
- 🟣 **Tasfiye Fiyatı (Liq Price):** Vadeli işlemlerde kaldıraç kaynaklı marjin sıfırlanma eşiği.

Grafiğin hemen altındaki **"🚀 Akıllı Pakete Aktar"** butonu, bu koordinatları tek bir dokunuşla Akıllı Paket Emir formuna aktarır.

---

## 11. Akıllı Paket Emir (Bracket Order) ve R:R Risk Yönetimi

Disiplinli ticaretin en kritik bileşeni **Bracket Order (Paket Emir)** mimarisidir. Bir işleme girerken çıkış planı önceden belirlenmemişse o işlem bir kumardır.

```
                    ┌────────────────────────────┐
                    │      GİRİŞ EMRİ (100%)     │  (Limit veya Market)
                    └──────────────┬─────────────┘
                                   │
                 ┌─────────────────┴─────────────────┐
                 ▼                                   ▼
   ┌───────────────────────────┐       ┌───────────────────────────┐
   │    HEDEF 1 (TP1 - %50)    │       │    ZARAR DURDUR (SL %100) │
   │ İlk Kârı Kasaya Koy       │       │ Sermayeyi Koru            │
   └─────────────┬─────────────┘       └───────────────────────────┘
                 ▼
   ┌───────────────────────────┐
   │    HEDEF 2 (TP2 - %50)    │
   │ Kalan Pozisyonla Trendi Sür│
   └───────────────────────────┘
```

### Risk / Kazanç (R:R) Oranı Kriteri:
Paket emir formunda tahmini R:R oranı anlık hesaplanır:
$$\text{R:R Oranı} = \frac{\text{Beklenen Ortalama Kazanç}}{\text{Göze Alınan Risk}}$$
- **R:R < 1:1.5:** Yüksek riskli, tavsiye edilmez.
- **R:R ≥ 1:2.0:** İdeal ve kabul edilebilir trade kurulumu.

---

## 12. Açık Pozisyonlar ve Canlı Emir Takip Ekranı

Emirler sekmesi iki ana yönetim panelinden oluşur:

### 1. Açık Pozisyonlar Kartı (`#card-positions`)
- **Giriş Fiyatı:** Pozisyonun açıldığı ortalama maliyet.
- **Anlık Fiyat:** KuCoin canlı tahtasındaki son işlem fiyatı.
- **Stop Fiyatı & Mesafe:** Stop seviyeniz ve fiyata olan yüzde uzaklığı (örn. `-1.85%`).
- **Kâr / Zarar (PnL):** Gerçekleşmemiş net kâr/zarar durumu (hem USDT değeri hem de yeşil/kırmızı yüzde rozeti olarak).

### 2. Açık Emirler Tablosu
- **Piyasa Türü:** `Spot`, `Margin` veya `Futures` rozeti.
- **Bacak Rolü:** Emrin niteliği (`🎯 TP1`, `🎯 TP2`, `🛑 SL`, `🔵 Giriş`).
- **Anlık Fiyat & Fark Rozeti:** Emrin gerçekleşmesi için piyasa fiyatının kaç yüzde uzaklıkta olduğunu dinamik renklerle gösterir.
- **🔄 Anlık Yenile Butonu:** Tahta verilerini gecikmesiz tazelemek için kullanılır.
- **İptal & Düzenle (Amend):** Bekleyen limit fiyatınızı piyasa koşullarına göre anında güncelleyebilirsiniz.

---

## 13. Acil Durum (Panic Stop) ve Hata Teşhis & Raporlama

### 🛑 Panic Stop Kalkanı
Beklenmedik bir piyasa çöküşü, aşırı volatilite veya kişisel acil durumlarda:
1. Sağ üst köşedeki **"🛑 PANIC STOP"** butonuna basın.
2. Sistem KuCoin üzerindeki **tüm açık limit ve stop emirlerinizi tek komutla iptal eder**.
3. Bot çekirdeğini dondurarak yeni emir girişlerini engeller.
4. Botu yeniden aktif hale getirmek için mod seçimini yenilemeniz gerekir.

### 📋 Teşhis Bilgisi Kopyalama (Diagnostics)
Bir hata veya bağlantı kopması durumunda:
- Alt bardaki veya hata ekranındaki **"Teşhis Bilgisi Kopyala"** düğmesine basarak sistem sürümü, API durumu, WebSocket sağlığı ve son log kayıtlarını panoya kopyalayabilir, geliştirici ekibe iletebilirsiniz.

### 🐞 Sorun Takip ve Hata Raporlama Ekranı (`#view-issues`)
- Arayüzde veya analizlerde fark ettiğiniz durumları kategori (UI, Analiz, Emir, API), öncelik ve açıklama belirterek kaydedebilirsiniz.
- Kayıtlar yerel SQLite veritabanında saklanır ve çözüldüğünde durumları güncellenebilir.

---

## 14. Yönetici Konsol Komutları Referansı (CLI)

Yönetim komutları projenin sanal ortamı üzerinden doğrudan çalıştırılabilir:

| Komut | Açıklama |
|-------|----------|
| `python -m src.auth.cli setup` | İlk admin kullanıcısını oluşturur, TOTP 2FA secret üretir ve `.env` anahtarlarını şifreli aktarır. |
| `python -m src.auth.cli setup --force` | Veritabanında zaten kullanıcı bulunsa dahi yeni bir admin hesabı ekler. |
| `python -m src.auth.cli reset-password --username <isim>` | Belirtilen kullanıcının şifresini sıfırlar, hatalı giriş sayacını temizler, hesap kilidini kaldırır ve eski açık oturumları düşürür. |
| `python -m src.auth.cli migrate-env --username <isim>` | `.env` dosyasındaki KuCoin API anahtarlarını belirtilen kullanıcının şifreli kasasına aktarır. |

---

*KuCoin Al-Sat Botu Dokümantasyon Ekibi — 2026*
