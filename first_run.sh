#!/usr/bin/env bash
# ==============================================================================
# KuCoin Al-Sat Botu - İlk Çalıştırma Scripti (first_run.sh)
# ==============================================================================
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=================================================================="
echo "🌟 KuCoin Al-Sat Botu: İlk Kurulum ve Hazırlık Sihirbazı"
echo "=================================================================="

# 1. .env Dosyası Kontrolü
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "📋 '.env' yapılandırma dosyası bulunamadı."
    if [ -f "$PROJECT_DIR/.env.example" ]; then
        echo "📄 '.env.example' dosyası '.env' olarak kopyalanıyor..."
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        echo "✅ '.env' dosyası oluşturuldu."
        echo "💡 İPUCU: Gerçek KuCoin işlemleriniz için '.env' dosyasına API anahtarlarınızı girebilirsiniz."
    else
        echo "❌ HATA: '.env.example' şablon dosyası bulunamadı!"
        exit 1
    fi
else
    echo "✅ '.env' yapılandırma dosyası mevcut."
fi

# 2. install.sh Çalıştırma (Sanal ortam ve paket kurulumu)
echo ""
echo "🔧 Bağımlılık kurulumu başlatılıyor (install.sh)..."
bash "$PROJECT_DIR/install.sh"

# 3. Klasör Yapısı Kontrolü
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/tests"

# 4. Doğrulama Testlerini Çalıştırma
echo ""
echo "🧪 Doğrulama ve entegrasyon testleri kontrol ediliyor..."
if [ -f "$PROJECT_DIR/run_tests.sh" ]; then
    bash "$PROJECT_DIR/run_tests.sh" || echo "⚠️  Henüz test dosyası yok veya bazı testler tamamlanmadı (Normal)."
fi

echo ""
echo "=================================================================="
echo "✨ İLK KURULUM BAŞARIYLA TAMAMLANDI!"
echo "   1. Ayarları düzenlemek için: nano .env (veya tercih ettiğiniz editör)"
echo "   2. Uygulamayı başlatmak için: ./run.sh"
echo "   3. Testleri çalıştırmak için: ./run_tests.sh"
echo "=================================================================="
