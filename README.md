# UT Tuton Automation (UTumun)

Automasi asisten Tutorial Online (Tuton) Universitas Terbuka (`elearning.ut.ac.id`) untuk monitoring, rekapitulasi, penilaian, dan evaluasi draf feedback forum diskusi mahasiswa.

## Fitur Utama

- **Automated Login & Session Management:** Autentikasi MyUT (Tutor Eksternal) dengan penyimpanan sesi browser yang aman via Playwright.
- **Multi-Course Flat Forum Scraping:** Menarik seluruh postingan diskusi Sesi 1 secara cepat menggunakan mode *flat discussion* (`&mode=1`).
- **Student & Feedback Matching:** Algoritma pencocokan cerdas antara postingan mahasiswa dan riwayat feedback tutor untuk mendeteksi:
  - Mahasiswa yang sudah dinilai dan memiliki feedback.
  - Mahasiswa yang sudah memiliki nilai di sistem namun belum ada feedback teks.
  - Mahasiswa yang baru mengumpulkan dan belum dinilai.
- **Evaluation & Auto-Grader Assistant:** Menghasilkan rekomendasi nilai (0–100) dan draf feedback konstruktif (2 paragraf: kelebihan dan saran perbaikan) sesuai rubrik dan Buku Materi Pokok (BMP).
- **Safety First:** Berjalan dalam mode *read-only* secara default untuk menghindari duplikasi tanggapan atau kerusakan UI sebelum disetujui pengguna.

## Instalasi

1. Clone repositori:
   ```bash
   git clone https://github.com/muhshi/UTumun.git
   cd UTumun
   ```

2. Buat virtual environment & pasang dependensi:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   playwright install chromium
   ```

3. Konfigurasi kredensial pada file `.env`:
   ```bash
   cp .env.example .env
   ```
   Isi `UT_USERNAME` dan `UT_PASSWORD` sesuai akun Tutor UT Anda.

## Penggunaan Terpadu (`main.py`)

Sistem dilengkapi antarmuka CLI tunggal dengan fitur **auto-relogin transparan** (otomatis login ulang ketika sesi kedaluwarsa tanpa menghentikan proses):

```bash
# 1. Rekapitulasi status semua sesi (Tahap 1 saja: ringkasan tabel & daftar mahasiswa yang kurang)
python main.py --mode recap

# 2. Rekapitulasi dan generate draf nilai & feedback untuk Sesi 1 saja
python main.py --session 1 --mode full

# 3. Rekapitulasi dan generate draf nilai & feedback untuk Sesi 2 saja
python main.py --session 2 --mode full

# 4. Pipeline penuh (Semua sesi: Rekapitulasi status disusul draf nilai & feedback siap salin)
python main.py --mode full
```

### Opsi CLI:
- `--session {1,2,all}` : Memilih sesi forum yang diproses (default: `all`).
- `--mode {recap,grade,full}` :
  - `recap`: Hanya menampilkan tabel ringkasan dan daftar mahasiswa yang kurang.
  - `grade`: Hanya menampilkan draf nilai dan feedback 2 paragraf untuk mahasiswa yang kurang.
  - `full`: Menjalankan Tahap 1 (rekapitulasi status) lalu dilanjutkan Tahap 2 (draf nilai & feedback siap salin).

## Lisensi
MIT License
