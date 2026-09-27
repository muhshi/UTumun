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

## Penggunaan

1. **Pemindaian Forum Diskusi:**
   ```bash
   python scan_all_courses_direct.py
   ```
   Data hasil scraping akan disimpan di folder `data/sessions/`.

2. **Analisis Status & Rekapitulasi:**
   ```bash
   python run_robust_match.py
   ```
   Menampilkan ringkasan status setiap kelas dan daftar mahasiswa yang belum selesai.

## Lisensi
MIT License
