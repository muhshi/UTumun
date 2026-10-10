# Asisten Tutor Online UT (MKWN4108 - Bahasa Indonesia)

Sistem Asisten Resmi Tutor Online Universitas Terbuka (`elearning.ut.ac.id`) yang didesain khusus untuk **Ibu Ainur Rosyidah Azmie Putry, S.Pd., M.Pd.** (NIP Tutor: `01007726`) pada mata kuliah **MKWN4108 - Bahasa Indonesia**.

Sistem ini memfasilitasi monitoring keaktifan mahasiswa, visualisasi trajektori nilai, pembuatan draf umpan balik (feedback) 2 paragraf berstandar Buku Materi Pokok (BMP) UT, serta rekapitulasi progres 4 kelas x 8 sesi perkuliahan.

---

## 🌟 Web Dashboard Interaktif (Rekomendasi Utama)

Web Dashboard menyediakan antarmuka grafis modern, elegan, dan ramah pengguna bernuansa **Warm Honey & Sunlight Gold** (Kuning Emas Hangat) untuk melakukan evaluasi, meninjau tanggapan mahasiswa, memantau kenaikan nilai, dan menyalin draf penilaian ke portal e-learning UT.

### Cara Menjalankan Web Dashboard
Cukup jalankan satu perintah sederhana di terminal:

```bash
./run.sh
```
*(atau via python: `python run_dashboard.py`)*

Terminal akan menampilkan informasi peluncuran:
```text
========================================================================
 ☀️  SISTEM ASISTEN TUTOR ONLINE UT (MKWN4108 BAHASA INDONESIA)
     Tutor: Ainur Rosyidah Azmie Putry, S.Pd., M.Pd. (NIP: 01007726)
========================================================================
[✓] Database terhubung: SQLite (data/tuton.db)
[✓] Tema Visual: Warm Honey & Sunlight Gold
[✓] Server berjalan di: http://127.0.0.1:8000
Buka tautan di atas pada Google Chrome untuk memulai evaluasi mahasiswa.
Tekan Ctrl+C untuk menghentikan server.
```
Buka peramban Google Chrome dan akses alamat **`http://127.0.0.1:8000`**.

> **Opsi Port/Host Kustom:** Anda juga dapat menentukan alamat host atau port secara fleksibel via argumen:  
> `./run.sh --port 8080 --host 0.0.0.0`

---

## 🚀 Fitur Unggulan Web Dashboard

1. **Tema Khusus Warm Honey & Sunlight Gold (Kuning Emas Hangat):**
   - Palet warna hangat (*Soft Ivory Cream* `#FFFDF5`, aksen madu `#F59E0B` & `#D97706`, tipografi *Deep Bronze* `#451A03`) yang didesain ergonomis dan menyenangkan di mata dosen saat memeriksa puluhan esai mahasiswa.
2. **Dashboard Ringkasan & Matriks Progres 4 Kelas x 8 Sesi:**
   - 4 Kartu Metrik: Total Mahasiswa, Selesai Dinilai, Perlu Tindakan (Pending), dan Sesi Berjalan.
   - Matriks interaktif 4 kelas tutorial (`MKWN4108.2137`, `2141`, `2145`, `465`) di seluruh 8 sesi:
     - **💬 Sesi Forum Diskusi:** Sesi 1, 2, 4, 6, 8 (pembukaan tiap selang 1 minggu).
     - **📝 Sesi Tugas Tutorial:** Sesi 3, 5, 7 (pembukaan tiap selang 1 minggu).
   - Klik langsung kotak sesi pada tabel matriks untuk memfilter daftar mahasiswa di bawahnya secara instan!
3. **Validasi Trajektori Nilai & Peringatan Penurunan Nilai:**
   - Visualisasi alur perkembangan nilai mahasiswa lintas sesi (`S1: 85 ➔ S2: 88 ➔ S3: 92`).
   - Memberikan indikator peringatan visual (⚠️) jika nilai sesi saat ini mengalami penurunan dibanding sesi sebelumnya, menjaga konsistensi penilaian akademik.
   - **Rekomendasi Nilai Progresif (*Auto-Suggest Grade*):** Menyarankan nilai bertahap naik (rentang 85–95) sebagai apresiasi konsistensi belajar mahasiswa.
4. **Tombol 1-Klik Salin Feedback & Salin Nilai:**
   - **Salin Feedback:** 1-klik menyalin draf umpan balik 2 paragraf berstandar BMP UT ke clipboard komputer. Tombol langsung berubah warna hijau (*"Tersalin! ✓"*) dan status mahasiswa diperbarui menjadi *"Sudah Disalin"*.
   - **Salin Nilai:** Tombol terpisah untuk menyalin angka skor secara instan.
5. **Dukungan Multi-Database (SQLite Lokal & MySQL Server):**
   - **Mode Lokal (Offline Default):** Menggunakan SQLite (`data/tuton.db`), data tersimpan persisten di komputer tanpa perlu server MySQL.
   - **Mode Server (Deploy):** Mendukung MySQL secara *native* hanya dengan mengatur `DB_ENGINE=mysql` di file `.env`.
   - Dilengkapi tombol **Ekspor Rekap (CSV)** untuk mengunduh rekapitulasi nilai semesteran siap pakai di Microsoft Excel.
6. **Sinkronisasi Inkremental & Pemindaian Latar Belakang:**
   - Hanya menarik dan mengevaluasi postingan mahasiswa yang **baru** atau yang **belum tuntas dinilai**.
   - Mahasiswa yang sudah memiliki nilai lengkap atau feedback-nya sudah disalin oleh Ibu Tutor **tidak akan ditimpa**, sehingga pekerjaan Ibu Tutor selalu aman.
   - Dialog progres sinkronisasi real-time dengan animasi persentase dan log berbahasa Indonesia.

---

## 🗄️ Konfigurasi Deployment & Database MySQL

Aplikasi ini dapat dijalankan baik di laptop lokal (SQLite) maupun dideploy di server pribadi Anda dengan database MySQL.

### 1. Menjalankan di Server dengan MySQL
Cukup tambahkan variabel konfigurasi berikut ke file `.env` di server Anda:

```env
# Aktifkan engine MySQL
DB_ENGINE=mysql

# Kredensial MySQL Server
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=password_database_anda
MYSQL_DATABASE=tuton_db
```

Jika server database MySQL aktif, aplikasi akan otomatis membuat tabel-tabel yang diperlukan saat pertama kali dijalankan.

### 2. Mengimpor Data Awal ke MySQL
Untuk mengisi data mahasiswa dan riwayat sesi 1–4 ke database MySQL di server, jalankan:
```bash
python -m tuton.seed_db
```

---

## 🧹 Struktur Repositori yang Bersih & Rapi

Seluruh skrip eksperimen dan eksplorasi awal telah dipindahkan secara tertib ke folder `scripts/legacy_scratch/`, sehingga struktur repositori bersih dan siap di-*push* ke GitHub:

```text
tuton_ut/
├── app/                      # Web Dashboard (FastAPI, Templates, Static Assets)
│   ├── static/               # CSS kustom, JavaScript controller (Alpine.js)
│   ├── templates/            # index.html (UI Warm Honey & Gold)
│   └── main.py               # REST API Endpoints
├── tuton/                    # Modul Inti Asisten Tuton
│   ├── db.py                 # SQLite Database Layer & Factory
│   ├── mysql_db.py           # MySQL Database Layer (untuk deploy server)
│   ├── scanner_service.py    # Background Scanner & Inkremental Sync
│   ├── scraper.py            # Playwright Scraper Forum & Tugas
│   ├── evaluator.py          # Rubrik Penilaian Resmi UT MKWN4108
│   ├── matcher.py            # Algoritma Pencocokan Feedback Tutor
│   ├── config.py             # Konfigurasi Kelas, Sesi, & Lingkungan
│   └── seed_db.py            # Seeder Data Historis Mahasiswa
├── scripts/
│   └── legacy_scratch/       # Arsip skrip eksplorasi & debug lawas
├── tests/                    # Rangkaian 53 Pengujian Otomatis (Pytest)
├── run.sh                    # Skrip 1-Klik Peluncur Web Dashboard
├── run_dashboard.py          # Python Entrypoint Web Dashboard
├── main.py                   # CLI Pipeline Runner
├── requirements.txt          # Dependensi Python
├── DESIGN.md                 # Dokumentasi Desain Sistem Warm Honey & Gold
└── .gitignore                # Filter keamanan (mengabaikan .env & .auth/)
```

> **Tidak Perlu Membuat Repo Baru:** Repositori yang ada saat ini sudah bersih dan siap digunakan. File `.gitignore` telah dikonfigurasi agar kredensial login (`.env`), cookie sesi Playwright (`.auth/`), dan cache temporer tidak akan ter-push ke GitHub.

---

## 🛡️ Aturan Keselamatan & Etika Kerja (Safety First)

1. **Mode Baca (Read-Only) Default:** 
   - Sistem **DILARANG KERAS** mengklik tombol *submit*, mengirim nilai, atau memposting tanggapan langsung ke website `elearning.ut.ac.id` secara otomatis.
   - Seluruh hasil evaluasi, nilai, dan feedback disajikan di dashboard agar Ibu Tutor dapat meninjau dan menyalinnya secara sadar dan mandiri.
2. **Kerahasiaan Akun:**
   - Kredensial login (`.env` dan `.auth/`) bersifat pribadi dan tidak boleh di-push ke publik.

---

## 📦 Panduan Instalasi Cepat di Server / Laptop

1. **Clone Repositori & Masuk Direktori:**
   ```bash
   git clone https://github.com/muhshi/UTumun.git
   cd UTumun
   ```

2. **Buat Virtual Environment & Pasang Dependensi:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   playwright install chromium
   ```

3. **Konfigurasi Kredensial (`.env`):**
   ```bash
   cp .env.example .env
   ```
   Sesuaikan isi `.env` dengan kredensial akun UT dan pilihan database Anda.

4. **Jalankan Dashboard:**
   ```bash
   ./run.sh
   ```
