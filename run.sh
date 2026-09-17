#!/usr/bin/env bash
# ==============================================================================
# KuCoin Al-Sat Botu - Uygulama Başlatma Scripti (run.sh)
# ==============================================================================
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

VENV_DIR="$PROJECT_DIR/.venv"

# 1. Sanal Ortam Kontrolü
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Sanal ortam (.venv) bulunamadı. Lütfen önce './install.sh' veya './first_run.sh' çalıştırın."
    exit 1
fi

source "$VENV_DIR/bin/activate"

# 2. .env Dosyası Kontrolü
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "⚠️  UYARI: '.env' dosyası bulunamadı. '.env.example' dosyası kopyalanıyor..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
fi

# 3. Ortam Değişkenlerini Okuma
HOST=$(grep -E "^HOST=" "$PROJECT_DIR/.env" | cut -d '=' -f2 | tr -d ' ' || echo "127.0.0.1")
PORT=$(grep -E "^PORT=" "$PROJECT_DIR/.env" | cut -d '=' -f2 | tr -d ' ' || echo "8000")
HOST=${HOST:-127.0.0.1}
PORT=${PORT:-8000}

echo "=================================================================="
echo "⚡ KuCoin Al-Sat Botu Başlatılıyor..."
echo "=================================================================="
echo "   🌐 REST API & Web Panel : http://$HOST:$PORT"
echo "   📖 Canlı Swagger UI     : http://$HOST:$PORT/docs"
echo "   📑 ReDoc Dokümantasyonu : http://$HOST:$PORT/redoc"
echo "=================================================================="
echo "Durdurmak için: CTRL + C"
echo ""

# 4. Backend Uygulama Kontrolü ve Başlatma
if [ -f "$PROJECT_DIR/src/main.py" ]; then
    uvicorn src.main:app --host "$HOST" --port "$PORT" --reload
else
    echo "ℹ️  'src/main.py' henüz oluşturulmadı (Şu an analiz ve tasarım aşamasındayız)."
    echo "   Modül 1 analizi tamamlanıp kodlamaya onay verildiğinde sunucu burada çalışacaktır."
fi
