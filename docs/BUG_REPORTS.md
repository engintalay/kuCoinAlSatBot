# KuCoin Al-Sat Botu — Hata Raporlama ve Sorun Takip Sistemi (Bug Reports & Diagnostics)

> **Modül Durumu:** %100 Tamamlandı (Canlı Arayüz + SQLite Veritabanı + REST API + Teşhis Konsolu) ✅  
> **Test Durumu:** 181 / 181 Test %100 Yeşil (%81 Coverage) ✅  
> **Son Güncelleme:** 2026-09-20 17:42:00 (+03:00)

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

