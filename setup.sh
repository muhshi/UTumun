#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " Setup Asisten Tuton UT (MKWN4108) untuk Bu Ainur"
echo "=========================================================="

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "Python3 belum terpasang. Harap pasang Python 3 terlebih dahulu."
    exit 1
fi

# 2. Virtual Environment
if [ ! -d ".venv" ]; then
    echo "Membuat virtual environment Python (.venv)..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# 3. Install Python Dependencies
echo "Memasang dependensi pustaka Python..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install Playwright Chromium
echo "Memasang browser otomatisasi Chromium..."
python3 -m playwright install chromium

# 5. Setup .env template if not exists
if [ ! -f ".env" ]; then
    echo "Menyiapkan file .env dari template..."
    cp .env.example .env
    echo "PENTING: Silakan buka file .env dan isi UT_USERNAME dan UT_PASSWORD akun Tuton Anda."
fi

echo ""
echo "=========================================================="
echo " Setup Selesai! Asisten Tuton UT sudah siap digunakan."
echo "=========================================================="
