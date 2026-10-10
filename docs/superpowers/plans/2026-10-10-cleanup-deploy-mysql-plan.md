# Cleanup, Deployment, MySQL Support & Incremental Scraping Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merapikan struktur repositori dari script-script scratch lama, membuat skrip peluncur `run.sh`, mengoptimalkan logika inkremental scraping (hanya menarik & memproses data baru/terkini sejak penarikan terakhir), menambahkan dukungan database MySQL (dengan fallback SQLite) untuk kemudahan deploy ke server, serta memperbarui `.gitignore` agar aman saat di-push ke GitHub.

**Architecture:** 
- Menyediakan lapisan database agnostik di `tuton/db.py` yang mendukung SQLite (`data/tuton.db`) untuk mode lokal offline dan MySQL (`PyMySQL`) via konfigurasi `.env`.
- Mengimplementasikan watermark waktu penarikan terakhir (`last_scraped_at`) per sesi & kelas di `scan_logs` sehingga scraping dapat mengenali postingan baru secara inkremental tanpa mengulang postingan lama yang sudah tuntas dinilai.
- Mengorganisir ~55 skrip eksperimen ke direktori `scripts/legacy_scratch/` sehingga root project bersih dan rapi.

**Tech Stack:** Python 3, FastAPI, Uvicorn, SQLite3, PyMySQL, Bash (`run.sh`), Playwright.

---

### Task 1: Buat Executable Launcher Script (`run.sh`)

**Files:**
- Create: `run.sh`

- [ ] **Step 1: Buat skrip `run.sh` yang otomatis mendeteksi virtual environment, menginstal dependensi jika belum ada, dan menjalankan server**
- [ ] **Step 2: Berikan permission executable (`chmod +x run.sh`)**
- [ ] **Step 3: Uji eksekusi `run.sh --help`**

---

### Task 2: Logika Scraping Inkremental (Hanya Data Baru dari UT)

**Files:**
- Modify: `tuton/scraper.py`
- Modify: `tuton/scanner_service.py`
- Test: `tests/test_incremental_scraping.py`

- [ ] **Step 1: Tulis unit test untuk verifikasi filter postingan baru berdasarkan timestamp postingan / post ID terakhir**
- [ ] **Step 2: Implementasikan pencatatan `last_scraped_time` pada tabel `scan_logs`**
- [ ] **Step 3: Filter postingan yang ditarik sehingga hanya postingan setelah timestamp terakhir yang dievaluasi ulang (postingan lama yang sudah memiliki nilai & feedback tidak di-override)**
- [ ] **Step 4: Jalankan pengujian dan pastikan lulus**

---

### Task 3: Dukungan Multi-Database (MySQL & SQLite)

**Files:**
- Modify: `requirements.txt` (tambah `pymysql>=1.1.0`, `cryptography>=42.0.0`)
- Modify: `tuton/config.py` (tambah konfigurasi MySQL dari `.env`)
- Modify: `tuton/db.py` (tambah konektor MySQL dengan skema tabel identik dan sintaks query kompatibel)
- Modify: `.env.example` (cantumkan contoh setting MySQL)
- Test: `tests/test_mysql_config.py`

- [ ] **Step 1: Tambahkan dependensi `pymysql` dan `cryptography`**
- [ ] **Step 2: Update konfigurasi di `tuton/config.py` untuk membaca `DB_ENGINE`, `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`**
- [ ] **Step 3: Sesuaikan `tuton/db.py` agar menginisialisasi koneksi MySQL jika `DB_ENGINE=mysql`, atau SQLite jika `DB_ENGINE=sqlite`**
- [ ] **Step 4: Buat unit test verifikasi abstraksi query multi-database**

---

### Task 4: Perapian Repositori (Noise Cleanup) & Standarisasi Git

**Files:**
- Create directory: `scripts/legacy_scratch/`
- Move: ~55 file `scratch_*.py`, `check_*.py`, `inspect_*.py`, `parse_*.py` ke `scripts/legacy_scratch/`
- Modify: `.gitignore` (pastikan mengabaikan `.env`, `.auth/`, `*.db`, `__pycache__`, log, berkas temporer)
- Modify: `README.md` (tambahkan panduan deploy ke server mandiri & konfigurasi MySQL)

- [ ] **Step 1: Pindahkan seluruh script lawas ke `scripts/legacy_scratch/`**
- [ ] **Step 2: Perbarui `.gitignore` agar kredensial login, sesi Playwright, dan database lokal tidak bocor ke GitHub**
- [ ] **Step 3: Jalankan seluruh test suite (`pytest`) untuk memastikan pemindahan berkas tidak merusak modul utama**
- [ ] **Step 4: Perbarui panduan Deployment di `README.md`**

---
