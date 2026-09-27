# KuCoin Al-Sat Botu — Hata Raporlama ve Sorun Takip Sistemi (Bug Reports & Diagnostics)

> **Modül Durumu:** %100 Tamamlandı (Canlı Arayüz + SQLite Veritabanı + REST API + Teşhis Konsolu) ✅  
> **Test Durumu:** 330 / 330 Test %100 Yeşil (%81 Coverage) ✅  
> **Son Güncelleme:** 2026-09-27 14:20:00 (+03:00)

---

## 1. Genel Bakış ve Amaç
Bu modül, KuCoin Al-Sat Botu kullanıcılarının ve test ekibinin arayüz üzerinde karşılaştıkları hataları, beklenmeyen davranışları veya geliştirme taleplerini doğrudan sistem içerisinden raporlayabilmesi, takip edebilmesi ve sistem teşhis verileriyle birlikte analiz edebilmesi için geliştirilmiştir.

Uygulama; **Web Arayüzü**, **SQLite Veritabanı Tablosu (`bug_reports`)**, **FastAPI REST API Servisi** ve **Sistem Teşhis Konsolu** bileşenlerinden oluşur.

---

## 2. Mimari Bileşenler

### 2.1 Veritabanı Şeması (`bug_reports`)
```sql
CREATE TABLE IF NOT EXISTS bug_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,          -- 'analysis', 'orders', 'account', 'settings', 'chart', 'api', 'general'
    severity TEXT NOT NULL,          -- 'critical', 'high', 'medium', 'low'
    status TEXT NOT NULL,            -- 'open', 'in_progress', 'resolved', 'closed'
    description TEXT NOT NULL,
    steps_to_reproduce TEXT,
    expected_behavior TEXT,
    actual_behavior TEXT,
    system_info TEXT,
    resolution_note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### 2.2 REST API Uç Noktaları
| Metot | Uç Nokta | Açıklama |
| :--- | :--- | :--- |
| `GET` | `/api/v1/issues` | Kayıtlı hataları listeler (opsiyonel `status` ve `category` filtreleri) |
| `POST` | `/api/v1/issues` | Yeni hata bildirimi oluşturur |
| `GET` | `/api/v1/issues/{id}` | Tekil hata kaydını ve çözüm notunu getirir |
| `PATCH` | `/api/v1/issues/{id}` | Hata durumunu (`in_progress`, `resolved`, `closed`) ve çözüm açıklamasını günceller |
| `DELETE` | `/api/v1/issues/{id}` | Hata kaydını siler |
| `GET` | `/api/v1/system/diagnostics` | Platform, Python sürümü, borsa bağlantısı, mod ve hata sayaçlarını döner |

### 2.3 Kullanıcı Arayüzü (Web UI)
1. **Navigasyon**: Sol menüye `🐛 Hata Raporlama` bağlantısı eklendi.
2. **Özet Sayaç Kartları**: Toplam Bildirim, Açık/İncelenen Hata, Çözülen Hata ve Sistem Sağlık Durumu.
3. **Yeni Hata Bildir Formu**:
   - Başlık, Kategori, Önem Derecesi.
   - Hata Açıklaması ve Tekrarlama Adımları.
   - Beklenen Davranış ve Gerçekleşen Davranış.
   - *"Sistem ve tarayıcı bilgilerini rapora otomatik ekle"* onay kutusu.
4. **Kayıtlı Hatalar Paneli**:
   - `[Tümü]`, `[Açık]`, `[İnceleniyor]`, `[Çözüldü]` filtre butonları.
   - Akordeon tarzı açılır detaylar, rozetler ve eylem butonları (`[✅ Çözüldü Olarak İşaretle]`, `[🔍 İnceleniyor Yap]`, `[🗑️ Sil]`).
5. **Sistem Teşhis Konsolu**:
   - Platform, Python, Aktif Mod, Watchlist boyutu.
   - Canlı olay ve hata logları terminali.
   - *"📋 Bilgileri Kopyala"* tek tıkla pano aktarımı.

---

## 3. Kayıtlı Hatalar ve Çözüm Günlüğü (Issue Log)

### 📌 Hata #1 (Issue #1)
- **Başlık**: Analiz ekranında coin seçim combo'sunda sadece BTC var
- **Kategori**: `analysis` (Analiz Ekranı / Kullanıcı Deneyimi)
- **Önem Derecesi**: `high` (Yüksek)
- **Durum**: `resolved` (Çözüldü) ✅
- **Kök Neden Analizi (Root Cause)**:
  1. Analiz ekranındaki sembol alanı HTML5 `<input list="symbol-choices" value="BTC/USDT">` olarak tanımlanmıştı.
  2. Tarayıcılar (Chrome, Firefox, Brave, Safari, Edge), input kutusunda `"BTC/USDT"` metni yazılıyken açılır liste tıklandığında datalist seçeneklerini mevcut metinle otomatik filtreler. Bu sebeple izleme listesindeki diğer koinler (`ETH/USDT`, `SOL/USDT`) gizlenmekte ve kullanıcı yalnızca `BTC/USDT` görmektedir.
  3. Ayrıca datalist yalnızca varsayılan 3 izleme listesi koinini içeriyordu; KuCoin'in en çok işlem gören popüler koinleri (SOL, XRP, DOGE, SUI vb.) hazır açılır seçenek olarak sunulmamıştı.
- **Uygulanan Düzeltme & Çözüm**:
  1. **Gerçek Açılır Kutu (Combo Dropdown)**: Analiz araç çubuğuna `<select id="analysis-symbol-select">` eklendi.
  2. **Optgroup Gruplaması**:
     - `👁️ İzleme Listesi (Watchlist)`: Kullanıcının Ayarlar'dan yönettiği tüm koinler.
     - `🔥 Popüler KuCoin Çiftleri`: BTC, ETH, SOL, XRP, DOGE, BNB, ADA, AVAX, LINK, SUI, PEPE, NEAR, LTC, DOT, TRX, APT, INJ, ARB, OP, TIA.
     - `➕ Diğer / Özel Sembol...`: İsteyen kullanıcının KuCoin'deki herhangi bir egzotik pariteyi yazabilmesi için özel giriş seçeneği.
  3. **Hızlı Seçim Çipleri (`quick-chips`)**: Toolbar'ın hemen altına tek tıkla analiz başlatan hızlı butonlar yerleştirildi (`[BTC] [ETH] [SOL] [XRP] [DOGE] [BNB] [SUI] [AVAX] [PEPE]`).
  4. **Metin Seçimi Otomasyonu**: `<input id="analysis-symbol">` odaklandığında `this.select()` ile tüm metin seçilerek tarayıcının datalist filtrelemesi aşılmış, kullanıcı dilediğinde serbest yazım yapabilmiştir.
  5. **Geriye Dönük Uyumluluk**: `assert r.text.count('list="symbol-choices"') == 3` testi dahil olmak üzere mevcut tüm kontratlar korunmuştur.
- **Doğrulama**:
  - `tests/test_bug_reports.py` altında testler yazıldı ve başarıyla geçti.
  - Proje genelinde 181 / 181 test %100 yeşil, test kapsamı %81.

---

### 📌 Hata #2 (Issue #2)
- **Başlık**: Ayarlardan canlı (live) moda geçiş olmuyor
- **Kategori**: `settings` (Ayarlar / Emir Motoru)
- **Önem Derecesi**: `critical` (Kritik)
- **Durum**: `resolved` (Çözüldü) ✅
- **Kök Neden Analizi (Root Cause)**:
  1. `POST /api/v1/settings` uç noktası `default_mode: "live"` bilgisini yalnızca SQLite `settings` tablosuna yazıyordu. Ancak arka plandaki emir yürütme motorunun çalışma modunu (`orders.switch_mode()`) çağırmıyordu.
  2. FastAPI sunucusu yeniden başladığında (`startup_event`), SQLite'a kaydedilen `default_mode` okunmuyor; emir motoru varsayılan olarak her zaman `paper` (simülasyon) modunda kalıyordu.
  3. Arayüzde `static/js/app.js` içerisindeki başlık çubuğu rozeti (`#mode-badge`), ayarlar kaydedildiğinde güncellenmiyordu ve tıklanabilir interaktif bir geçiş işlevi bulunmuyordu.
- **Uygulanan Düzeltme & Çözüm**:
  1. **Çift Yönlü Senkronizasyon**:
     - `POST /api/v1/settings` uç noktası gelen `default_mode` değerini artık doğrudan `await orders.switch_mode(payload["default_mode"])` ile emir motoruna senkronize etmektedir.
     - `POST /api/v1/orders/switch-mode` uç noktası da değiştirilen modu kalıcı olarak SQLite `settings` tablosuna yazmaktadır.
  2. **Açılışta Mod Restorasyonu**:
     - `main.py` içindeki `startup_event()` fonksiyonu veritabanındaki `default_mode` ayarını okuyup `orders.switch_mode()` ile sunucu açılışında otomatik devreye almaktadır.
  3. **Yeni Uç Nokta**:
     - `GET /api/v1/orders/mode` uç noktası eklendi; aktif mod, botun çalışma durumu ve KuCoin API anahtar doğrulama durumu anlık olarak sorgulanabilmektedir.
  4. **Arayüz Geliştirmesi**:
     - Başlıktaki `#mode-badge` rozeti interaktif hızlı geçiş düğmesine dönüştürüldü. Rozete tıklandığında onay kutusu ile doğrudan canlı/simülasyon modları arasında geçiş yapılabilmektedir.
     - Ayarlar kaydedildiğinde ya da rozet tıklandığında anlık bakiye (`loadSummary`), bot durumu (`loadStatus`), açık emirler (`loadOpenOrders`) ve sistem teşhis verileri (`loadDiagnostics`) otomatik olarak yenilenmektedir.
- **Doğrulama**:
  - `tests/test_bug_reports.py` içerisine `test_settings_live_mode_switch` testi eklendi.
  - Proje genelinde 181 / 181 test %100 yeşil, test kapsamı %81.

---

### 📌 Hata #3 (Issue #3)
- **Başlık**: Ayarlar ekranında kısmi değişiklik yapıldığında diğer ayarların sıfırlanması
- **Kategori**: `settings` (Ayarlar / Kalıcılık)
- **Önem Derecesi**: `high` (Yüksek)
- **Durum**: `resolved` (Çözüldü) ✅
- **Kök Neden Analizi**:
  - `SettingsManager.save()` metodu her çağrıda diskteki mevcut ayarları okumak yerine `DEFAULT_SETTINGS` sözlüğünden başlayarak yalnızca gelen payload anahtarlarını yazıyordu.
  - Örneğin yalnızca `default_mode` değiştirildiğinde `watchlist` ve `default_symbol` gibi kullanıcı tercihleri varsayılan değerlere sıfırlanıyordu.
- **Uygulanan Düzeltme & Çözüm**:
  - `save()` fonksiyonu diskteki mevcut ayarları (`_read_raw`) okuyup üzerine merge edecek şekilde güncellendi; `risk` gibi iç içe dict yapıları derin birleştirme (deep merge) ile korundu.
- **Doğrulama**:
  - `test_settings.py` içerisine kısmi güncelleme regresyon testi eklendi.

---

### 📌 Hata #4 (Issue #4)
- **Başlık**: KuCoin Futures paket emrinde "kucoinfutures does not have market symbol PEPE/USDT" hatası
- **Kategori**: `orders` (Futures / Sembol Biçimi)
- **Önem Derecesi**: `critical` (Kritik)
- **Durum**: `resolved` (Çözüldü) ✅
- **Kök Neden Analizi**:
  - KuCoin Futures USDT-M sözleşmeleri ccxt üzerinde `BASE/QUOTE:SETTLE` formatında tanımlıdır (`PEPE/USDT:USDT`).
  - Spot sembolü doğrudan vadeli borsaya gönderildiğinde borsa sembolü tanıyamayıp işlemi reddediyordu.
- **Uygulanan Düzeltme & Çözüm**:
  - `_normalize_symbol()` metodu yazılarak vadeli piyasalarda `:SETTLE` eki otomatik denetlendi ve borsanın market sözlüğüne göre doğrulandı.

---

### 📌 Hata #5 (Issue #5)
- **Başlık**: Futures 5x izole seçildiğinde 3x cross açılması ve 330005 marjin modu uyuşmazlığı
- **Kategori**: `orders` (Futures / Marjin & Kaldıraç)
- **Önem Derecesi**: `critical` (Kritik)
- **Durum**: `resolved` (Çözüldü) ✅
- **Kök Neden Analizi**:
  1. KuCoin Futures'ta marjin modu (`CROSS` vs `ISOLATED`) emir bazında değil, borsadaki sembol ayarı düzeyindedir. Borsa ayarı CROSS iken ISOLATED parametresiyle emir verilirse borsa `330005: "The order's margin mode does not match the selected one"` hatası fırlatır.
  2. Eski kod bu hatayı sessizce yakalayıp emri otomatik `cross` modunda yeniden gönderiyordu.
  3. KuCoin cross moddayken `create_order` içindeki `params['leverage']` parametresini tamamen yoksayar ve borsadaki cross kaldıraç ayarını (kullanıcı hesabında 3x idi) zorunlu kılar.
  4. Açık pozisyon veya bekleyen emir varken borsa marjin modu değişimini (`CROSS` $\leftrightarrow$ `ISOLATED`) kesinlikle reddeder (`500020`).
- **Uygulanan Düzeltme & Çözüm**:
  1. `_create_live_order` öncesinde borsanın `set_leverage(lev, symbol)` ve `set_margin_mode(mode, symbol)` API metotları çağrılarak borsadaki sembol yapılandırması güncellendi.
  2. Borsa mevcut pozisyon sebebiyle izole moda geçişe izin vermezse kullanıcıya detaylı bir `warning` mesajı iletildi.
  3. Tablolara `[CROSS]` ve `[ISOLATED]` rozetleri eklendi.
  4. Canlıdaki SUI pozisyonunun kaldıracı borsada doğrudan 5x'e yükseltildi.

---

### 📌 Hata #6 (Issue #6)
- **Başlık**: Take profit ve stop loss emirlerinin borsaya geçmemesi
- **Kategori**: `orders` (Futures / TP & SL İcrası)
- **Önem Derecesi**: `critical` (Kritik)
- **Durum**: `resolved` (Çözüldü) ✅
- **Kök Neden Analizi**:
  - KuCoin Futures'ta stop emirleri standart emir defterine değil, borsanın koşullu tetikleme motoruna (`/api/v1/st-orders` ve `/api/v1/stop-order`) `stopPrice`, `triggerStopUpPrice`, `triggerStopDownPrice` ve `reduceOnly=True` bayraklarıyla iletilmelidir.
  - Açıkta duran bir pozisyona sonradan TP/SL bağlama imkanı bulunmuyordu.
- **Uygulanan Düzeltme & Çözüm**:
  - `KuCoinOrders.set_position_tp_sl()` motoru ve `POST /api/v1/orders/position/set-tp-sl` uç noktası yazıldı.
  - Açık pozisyon büyüklüğü kadar `reduceOnly` TP limit ve SL market tetikleyici emirleri KuCoin stop-order uç noktasına bağlandı.
  - Açık Pozisyonlar tablosundaki her pozisyona tek tıkla hedef ve stop belirleyen **"🛡️ TP/SL"** modal butonu eklendi.

---

### 📌 Hata #7 (Issue #7)
- **Başlık**: Portföyde yalnızca Spot/Funding görünmesi ve hesaplar arası transfer eksikliği
- **Kategori**: `account` (Hesap / Çoklu Cüzdan & Transfer)
- **Önem Derecesi**: `high` (Yüksek)
- **Durum**: `resolved` (Çözüldü) ✅
- **Kök Neden Analizi**:
  - Bakiye sorguları yalnızca spot ve funding cüzdanlarını tarıyordu; marjin ve futures cüzdanları listelenmiyordu.
- **Uygulanan Düzeltme & Çözüm**:
  - `get_balances` Spot, Funding, Margin ve KuCoin Futures cüzdanlarını birleştirecek şekilde genişletildi.
  - `transfer_funds()` ve `POST /api/v1/account/transfer` yazılarak tüm cüzdanlar arasında iki yönlü transfer devreye alındı.

---

### 📌 Hata #8 (Issue #8)
- **Başlık**: Dashboard ekranında piyasa rejim ve izleme listesi widget'larının "Yükleniyor"da takılması
- **Kategori**: `frontend` (Dashboard / Asenkron Yükleme)
- **Önem Derecesi**: `medium` (Orta)
- **Durum**: `resolved` (Çözüldü) ✅
- **Kök Neden Analizi**:
  - `apiGet` geçersiz yanıtta throw ediyordu ve sıralı `await` çağrısı tek bir başarısız istekte (CoinGecko rate limit vb.) sonraki tüm widget'ları kilitliyordu.
- **Uygulanan Düzeltme & Çözüm**:
  - `apiGet` `try/catch` + `{success:false,error}` korumasına alındı; `refreshDashboard` `Promise.allSettled` ile widget izolasyonuna kavuşturuldu.
- **Doğrulama**:
  - Toplam 330/330 test %100 yeşil.

