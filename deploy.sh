#!/usr/bin/env bash
# ==============================================================================
# Smart Deployment Script: Asisten Tutor Online UT MKWN4108
# Port: 8020
# Fitur Pintar: Deteksi perubahan dependensi (build total vs rebuild cepat)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================================"
echo " 🚀 SMART DEPLOYMENT: ASISTEN TUTOR ONLINE UT (PORT 8020)"
echo "========================================================================"

# 1. Cek keberadaan file konfigurasi lingkungan (.env)
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "[!] File .env tidak ditemukan. Menyalin dari .env.example..."
        cp .env.example .env
        echo "[!] Harap sesuaikan kredensial di file .env terlebih dahulu!"
    else
        echo "[ERROR] File .env tidak ditemukan!"
        exit 1
    fi
fi

# 2. Tarik update terbaru dari repositori Git jika berada dalam git repo
NEED_FULL_BUILD=false
CURRENT_HASH_FILE=".deploy_cache_hash"

if [ -d ".git" ]; then
    echo "[1/4] Memeriksa pembaruan dari Git..."
    OLD_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "")
    git pull origin main || echo "[i] Melanjutkan dengan versi lokal saat ini..."
    NEW_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "")

    if [ "$OLD_HEAD" != "$NEW_HEAD" ] && [ -n "$OLD_HEAD" ]; then
        # Cek apakah ada perubahan pada berkas dependensi inti
        DIFF_DEPS=$(git diff "$OLD_HEAD" "$NEW_HEAD" -- requirements.txt Dockerfile 2>/dev/null || echo "")
        if [ -n "$DIFF_DEPS" ]; then
            echo "[i] Terdeteksi perubahan pada requirements.txt atau Dockerfile."
            NEED_FULL_BUILD=true
        fi
    fi
fi

# 3. Hitung checksum dari requirements.txt dan Dockerfile sebagai verifikasi ganda
CALC_HASH=$(cat requirements.txt Dockerfile 2>/dev/null | shasum -a 256 | awk '{print $1}')
LAST_HASH=""
if [ -f "$CURRENT_HASH_FILE" ]; then
    LAST_HASH=$(cat "$CURRENT_HASH_FILE")
fi

if [ "$CALC_HASH" != "$LAST_HASH" ]; then
    NEED_FULL_BUILD=true
fi

# Cek apakah container image tuton-dashboard sudah ada
IMAGE_EXISTS=$(docker images -q tuton-dashboard 2>/dev/null || docker images -q tuton_dashboard 2>/dev/null || echo "")
if [ -z "$IMAGE_EXISTS" ]; then
    NEED_FULL_BUILD=true
fi

# 4. Eksekusi Build Sesuai Kebutuhan (Smart Build)
if [ "$NEED_FULL_BUILD" = true ]; then
    echo "[2/4] Melakukan BUILD TOTAL (Dependensi / Image berubah)..."
    docker compose build --pull
    echo "$CALC_HASH" > "$CURRENT_HASH_FILE"
else
    echo "[2/4] Menggunakan CACHE LAYER CEPAT (Kode diperbarui tanpa install ulang paket)..."
    docker compose build
fi

# 5. Jalankan Container
echo "[3/4] Menjalankan layanan di latar belakang (Port 8020)..."
docker compose up -d --remove-orphans

# 6. Verifikasi Healthcheck
echo "[4/4] Memeriksa status kesehatan layanan..."
MAX_RETRIES=15
COUNTER=0
SUCCESS=false

while [ $COUNTER -lt $MAX_RETRIES ]; do
    if curl -s -f "http://127.0.0.1:8020/api/recap" >/dev/null 2>&1; then
        SUCCESS=true
        break
    fi
    sleep 2
    COUNTER=$((COUNTER + 1))
    echo -n "."
done
echo ""

if [ "$SUCCESS" = true ]; then
    echo "========================================================================"
    echo " [✓] DEPLOYMENT BERHASIL!"
    echo " [✓] URL Dashboard: http://127.0.0.1:8020 (atau IP server Anda: 8020)"
    echo " [✓] Container: tuton_dashboard (Aktif)"
    echo "========================================================================"
else
    echo "========================================================================"
    echo " [!] Layanan sedang khởi động atau memerlukan penyesuaian."
    echo " Periksa log dengan perintah: docker compose logs -f"
    echo "========================================================================"
fi
