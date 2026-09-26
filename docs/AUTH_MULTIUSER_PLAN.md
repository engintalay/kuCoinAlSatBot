# Kimlik Doğrulama, Çok Kullanıcı, Transfer & Binance — Yol Haritası

> **Durum:** Faz 1 geliştirme başladı | **Son Güncelleme:** 2026-09-26

## Onaylanan Kararlar

### Kimlik & Güvenlik
- **Giriş:** Kullanıcı adı / şifre + **TOTP 2FA** (`pyotp`, offline authenticator).
- **E-posta yedek (2FA kurtarma):** Faz 3. Kurtarma tetiklenirse **sistem 2 gün işlemlere kapalı** (güvenlik dondurma).
- **Self-registration KAPALI** — sadece önceden tanımlı hesaplar (admin ekler).
- **İlk admin:** CLI kurulum ile (`python -m src.auth.cli setup`). Kullanıcı/şifre sorar, TOTP secret+QR/provisioning URI basar.
- **Admin şifre reset:** Konsol/CLI mekanizması (`reset-password`).
- **Oturum:** Sunucu tarafı session (SQLite), cookie ile. Anında iptal edilebilir (kilit/kapatma → oturum düşer).

### Brute-force Koruması
- 3-5 başarısız denemede **aşamalı kilitleme** + (Faz 3) e-posta bildirimi.
- 2 aşama sonra hesap **tamamen kapanır**. Admin dahil.
- **Yerel-ağ istisnası (2b):** Sunucu ile aynı /24 alt ağdan (ör. sunucu `192.168.68.100` → `192.168.68.xx`) gelen kullanıcı/admin, şifre doğruysa **hem kilitlemeyi hem 2FA'yı atlar** (sadece şifre yeterli).

### API Anahtarı Saklama
- **Master key (1b→master):** Borsa API anahtarları kullanıcı şifresinden **bağımsız** bir master key ile şifreli (Fernet) DB'de, kullanıcı başına. Şifre sıfırlama API anahtarlarını **etkilemez**.
- **`.env` politikası:** Borsa API anahtarları `.env`'den kaldırılıp şifreli DB'ye taşınır (ilk admin kurulumunda migrate). SMTP gibi genel/sistem ayarları + `MASTER_KEY` `.env`'de kalabilir.

### Modül Mimarisi
- **Request-scoped (3a):** Her API isteği, oturumdaki kullanıcının çözülmüş anahtarıyla borsa client'ı alır (kullanıcı bazlı önbellek). `KuCoinAccount/Market/Orders` bir fabrikadan üretilir.
- **Kullanıcı-bazlı ayarlar:** Watchlist, mod, risk ayarları kullanıcı başına (`user_settings`).

### Hesap İçi Transfer (Faz 2)
- **1a — tüm yönler serbest:** Spot↔Futures, Spot↔Margin, Funding↔Spot vb. (ccxt `transfer(code, amount, fromAccount, toAccount)`; `main`/`trade`/`margin`/`futures`).
- **2a — transfer sonrası** ilgili hesap bakiyeleri otomatik yenilenir + yeni bakiyeler kullanıcıya gösterilir.
- Giriş yapmış kullanıcının kendi API anahtarıyla yapılır (auth'a bağlı → bu yüzden Faz 2).

### Binance (Faz 4)
- Uzun vadeli. Bu turda dokunulmaz. Kod borsa-agnostik hale getirilecek (exchange adapter/factory), sonra Binance tam entegrasyon.

## Yol Haritası (fazlar; her faz testler yeşil olunca bir sonrakine geçilir)
1. **Faz 1 — Auth & Multi-user:** kullanıcı/şifre + TOTP, session, brute-force+kilitleme, yerel-ağ istisnası, master-key şifreli API deposu, request-scoped client, kullanıcı-bazlı ayarlar, admin CLI (setup/reset/migrate-env), giriş ekranı. **(AKTİF)**
2. **Faz 2 — Hesap içi transfer:** Spot↔Futures↔Margin tüm yönler, sonrası bakiye yenileme.
3. **Faz 3 — Dondurma + e-posta:** 2 günlük işlem dondurma, kilit/kurtarma e-posta bildirimleri.
4. **Faz 4 — Binance / çoklu borsa:** exchange adapter soyutlaması + Binance entegrasyonu.

## Teknoloji
- `passlib[bcrypt]` (şifre hash), `pyotp` (TOTP), `cryptography` (Fernet), FastAPI `Depends` + Cookie session (SQLite).
