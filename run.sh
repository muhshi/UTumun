#!/usr/bin/env bash
# ==============================================================================
# Skrip Peluncur: Asisten Tutor Online UT MKWN4108
# Dosen/Tutor: Ainur Rosyidah Azmie Putry, S.Pd., M.Pd. (NIP: 01007726)
# ==============================================================================

set -e

# Berpindah ke direktori skrip berada
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================================"
echo " ☀️  SISTEM ASISTEN TUTOR ONLINE UT (MKWN4108 BAHASA INDONESIA)"
echo "    Tutor: Ainur Rosyidah Azmie Putry, S.Pd., M.Pd."
echo "========================================================================"

# Cek keberadaan Virtual Environment (.venv)
if [ -d ".venv" ]; then
    echo "[✓] Mengaktifkan virtual environment (.venv)..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "[✓] Mengaktifkan virtual environment (venv)..."
    source venv/bin/activate
else
    echo "[!] Virtual environment tidak ditemukan. Membuat .venv baru..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "[✓] Menginstal paket yang dibutuhkan..."
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# Jalankan dashboard
python run_dashboard.py "$@"
