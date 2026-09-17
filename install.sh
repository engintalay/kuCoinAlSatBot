#!/usr/bin/env bash
# ==============================================================================
# KuCoin Al-Sat Botu - Kurulum Scripti (install.sh)
# ==============================================================================
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=================================================================="
echo "🚀 KuCoin Al-Sat Botu: Sanal Ortam ve Bağımlılık Kurulumu"
echo "=================================================================="

# 1. Python Sürüm Kontrolü
if ! command -v python3 &> /dev/null; then
    echo "❌ HATA: Sistemde python3 bulunamadı. Lütfen Python 3.10+ kurun."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo "🔍 Tespit Edilen Python: $PYTHON_VERSION"

# 2. Sanal Ortam (.venv) Oluşturma
VENV_DIR="$PROJECT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Sanal Python ortamı (.venv) oluşturuluyor..."
    python3 -m venv "$VENV_DIR"
    echo "✅ Sanal ortam başarıyla oluşturuldu: $VENV_DIR"
else
    echo "ℹ️  Mevcut sanal ortam (.venv) bulundu."
fi

# 3. Sanal Ortamı Aktif Etme
source "$VENV_DIR/bin/activate"
echo "🔌 Sanal ortam aktif edildi ($(which python))."

# 4. Pip Güncelleme
echo "⬆️  pip ve temel araçlar güncelleniyor..."
pip install --upgrade pip setuptools wheel --quiet

# 5. requirements.txt Kurulumu
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    echo "📥 Bağımlılıklar (requirements.txt) yükleniyor..."
    pip install -r "$PROJECT_DIR/requirements.txt" --quiet
    echo "✅ Tüm Python kütüphaneleri başarıyla kuruldu."
else
    echo "⚠️  UYARI: requirements.txt bulunamadı!"
fi

# 6. Gerekli Dizinlerin Oluşturulması
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/tests"
mkdir -p "$PROJECT_DIR/docs"

echo "=================================================================="
echo "🎉 Kurulum başarıyla tamamlandı!"
echo "   - Sanal Ortam : $VENV_DIR"
echo "   - Başlatmak için: ./run.sh"
echo "   - Testler için  : ./run_tests.sh"
echo "=================================================================="
