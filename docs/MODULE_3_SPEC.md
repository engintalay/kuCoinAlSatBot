# Modül 3 Spesifikasyonu: Al-Sat Emir Entegrasyonu ve Emir Yönetimi

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
