#!/usr/bin/env bash
# ==============================================================================
# KuCoin Al-Sat Botu - Otomatik Test ve Raporlama Scripti (run_tests.sh)
# ==============================================================================
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

VENV_DIR="$PROJECT_DIR/.venv"

# 1. Sanal Ortam Kontrolü
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Sanal ortam (.venv) bulunamadı. Lütfen önce './install.sh' çalıştırın."
    exit 1
fi

source "$VENV_DIR/bin/activate"

echo "=================================================================="
echo "🧪 KuCoin Al-Sat Botu: Otomatik Birim Test ve Kalite Raporu"
echo "=================================================================="

# Test raporları dizini
REPORT_DIR="$PROJECT_DIR/test-reports"
mkdir -p "$REPORT_DIR"

# 2. Pytest ile Testleri Çalıştırma
if [ -d "$PROJECT_DIR/tests" ] && [ "$(ls -A "$PROJECT_DIR/tests" 2>/dev/null)" ]; then
    echo "🏃 Testler çalıştırılıyor..."
    pytest "$PROJECT_DIR/tests" \
        -v \
        --tb=short \
        --junitxml="$REPORT_DIR/junit-report.xml" || {
            echo "❌ Bazı birim testler BAŞARISIZ oldu! Lütfen yukarıdaki hata detaylarını inceleyin."
            exit 1
        }
    echo "=================================================================="
    echo "✅ TÜM BİRİM TESTLER BAŞARIYLA GEÇTİ!"
    echo "   - Test Raporu: $REPORT_DIR/junit-report.xml"
    echo "=================================================================="
else
    echo "ℹ️  'tests/' dizininde henüz test dosyası bulunmuyor."
    echo "   Modül kodlamaları başladığında her fonksiyon için birim test eklenecektir."
fi
