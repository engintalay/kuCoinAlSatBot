"""
KuCoin Al-Sat Botu — Admin Konsol Aracı (Faz 1 Task 8)

Kullanım:
    python -m src.auth.cli setup            # İlk admin oluştur (+ TOTP + .env anahtar aktarımı)
    python -m src.auth.cli reset-password   # Admin/kullanıcı şifresi sıfırla + kilidi temizle
    python -m src.auth.cli migrate-env      # .env'deki KuCoin anahtarlarını bir kullanıcıya taşı

Self-registration kapalıdır; kullanıcılar yalnızca bu araç veya admin tarafından
oluşturulur.
"""

import argparse
import asyncio
import getpass
import sys

from src.auth.user_store import UserStore
from src.auth import auth_service
from src.config import Config


# ---------------------------------------------------------------------------- #
# İş mantığı (test edilebilir — I/O'dan bağımsız)
# ---------------------------------------------------------------------------- #
async def create_admin(store: UserStore, username: str, password: str,
                       email: str | None = None, with_totp: bool = True,
                       migrate_env_keys: bool = True) -> dict:
    """
    İlk admin kullanıcıyı oluşturur. TOTP secret üretir ve (istenirse) .env'deki
    KuCoin API anahtarlarını bu kullanıcıya şifreli aktarır.
    Döner: {user, totp_secret, provisioning_uri, migrated}
    """
    existing = await store.get_user_by_username(username)
    if existing:
        raise ValueError(f"'{username}' zaten mevcut.")

    totp_secret = auth_service.generate_totp_secret() if with_totp else None
    user = await store.create_user(
        username=username,
        password_hash=auth_service.hash_password(password),
        role="admin",
        totp_secret=totp_secret,
        email=email,
    )

    migrated = False
    if migrate_env_keys:
        cfg = Config()
        if cfg.API_KEY and cfg.API_SECRET:
            await store.save_api_keys(
                user["id"], cfg.API_KEY, cfg.API_SECRET, cfg.API_PASSPHRASE or "",
                exchange="kucoin", is_sandbox=cfg.IS_SANDBOX,
            )
            migrated = True

    uri = auth_service.totp_provisioning_uri(totp_secret, username) if totp_secret else None
    return {"user": user, "totp_secret": totp_secret, "provisioning_uri": uri, "migrated": migrated}


async def reset_password(store: UserStore, username: str, new_password: str) -> dict:
    """Şifreyi sıfırlar ve tüm kilit durumlarını temizler (admin dahil)."""
    user = await store.get_user_by_username(username)
    if not user:
        raise ValueError(f"'{username}' bulunamadı.")
    updated = await store.update_user_fields(
        user["id"],
        password_hash=auth_service.hash_password(new_password),
        failed_attempts=0, lock_stage=0, locked_until=None, is_disabled=0,
    )
    await store.delete_user_sessions(user["id"])  # eski oturumları düşür
    return updated


async def migrate_env_keys(store: UserStore, username: str) -> bool:
    """.env'deki KuCoin API anahtarlarını belirtilen kullanıcıya taşır."""
    user = await store.get_user_by_username(username)
    if not user:
        raise ValueError(f"'{username}' bulunamadı.")
    cfg = Config()
    if not (cfg.API_KEY and cfg.API_SECRET):
        return False
    await store.save_api_keys(
        user["id"], cfg.API_KEY, cfg.API_SECRET, cfg.API_PASSPHRASE or "",
        exchange="kucoin", is_sandbox=cfg.IS_SANDBOX,
    )
    return True


# ---------------------------------------------------------------------------- #
# CLI arayüzü
# ---------------------------------------------------------------------------- #
def _prompt_password(confirm: bool = True) -> str:
    pw = getpass.getpass("Şifre: ")
    if confirm:
        pw2 = getpass.getpass("Şifre (tekrar): ")
        if pw != pw2:
            print("❌ Şifreler eşleşmedi.")
            sys.exit(1)
    if len(pw) < 8:
        print("❌ Şifre en az 8 karakter olmalı.")
        sys.exit(1)
    return pw


async def _cmd_setup(args):
    store = UserStore()
    await store.init_db()
    if await store.count_users() > 0 and not args.force:
        print("⚠️  Zaten kullanıcı(lar) var. Yeni admin için --force kullanın.")
        sys.exit(1)
    username = args.username or input("Admin kullanıcı adı: ").strip()
    email = args.email or input("E-posta (opsiyonel): ").strip() or None
    password = _prompt_password()
    result = await create_admin(store, username, password, email=email)
    print(f"\n✅ Admin '{username}' oluşturuldu.")
    if result["migrated"]:
        print("✅ .env'deki KuCoin API anahtarları bu hesaba şifreli aktarıldı.")
    if result["provisioning_uri"]:
        print("\n🔐 2FA (TOTP) kurulumu — Authenticator uygulamanıza ekleyin:")
        print(f"   Secret : {result['totp_secret']}")
        print(f"   URI    : {result['provisioning_uri']}")
        try:
            import pyotp  # noqa
            print("   (Bu URI'yi bir QR üreticisine yapıştırarak da tarayabilirsiniz.)")
        except Exception:
            pass
    print("\nKurulum tamam. Uygulamayı başlatıp giriş yapabilirsiniz.")


async def _cmd_reset(args):
    store = UserStore()
    await store.init_db()
    username = args.username or input("Kullanıcı adı: ").strip()
    password = _prompt_password()
    await reset_password(store, username, password)
    print(f"✅ '{username}' şifresi sıfırlandı ve kilitler temizlendi.")


async def _cmd_migrate(args):
    store = UserStore()
    await store.init_db()
    username = args.username or input("Anahtarların taşınacağı kullanıcı: ").strip()
    ok = await migrate_env_keys(store, username)
    print("✅ .env anahtarları taşındı." if ok else "⚠️  .env'de KuCoin anahtarı bulunamadı.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="KuCoin Al-Sat Botu — Admin Konsol Aracı")
    sub = parser.add_subparsers(dest="command", required=True)

    p_setup = sub.add_parser("setup", help="İlk admin oluştur")
    p_setup.add_argument("--username"); p_setup.add_argument("--email")
    p_setup.add_argument("--force", action="store_true", help="Kullanıcı olsa bile yeni admin ekle")

    p_reset = sub.add_parser("reset-password", help="Şifre sıfırla + kilit temizle")
    p_reset.add_argument("--username")

    p_mig = sub.add_parser("migrate-env", help=".env anahtarlarını kullanıcıya taşı")
    p_mig.add_argument("--username")

    args = parser.parse_args(argv)
    handlers = {"setup": _cmd_setup, "reset-password": _cmd_reset, "migrate-env": _cmd_migrate}
    asyncio.run(handlers[args.command](args))


if __name__ == "__main__":
    main()
