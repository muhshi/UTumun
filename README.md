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

### 1. Sesi 1 (Hakikat & Sifat Bahasa)
- **Pemindaian Forum Diskusi Sesi 1:**
  ```bash
  python scan_all_courses_direct.py
  ```
- **Analisis & Rekapitulasi Sesi 1:**
  ```bash
  python run_robust_match.py
  ```

### 2. Sesi 2 (Keterampilan Berbahasa)
- **Unduh & Ekstrak Rubrik Resmi UT:**
  ```bash
  python download_rambu_requests.py
  python read_rubrik_docx.py
  ```
- **Pemindaian Forum Diskusi Sesi 2 (4 Kelas):**
  ```bash
  python scan_sesi2_all.py
  ```
- **Evaluasi & Auto-Grader Sesi 2:**
  ```bash
  python grade_all_sesi2_pending.py
  ```

## Lisensi
MIT License
