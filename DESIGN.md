# Panduan Desain Sistem: Asisten Tutor UT MKWN4108 (Edisi Warm Honey & Sunlight Gold)

## 1. Filosofi & Karakter Visual
Antarmuka didesain secara spesial dan personal untuk **Ibu Ainur Rosyidah Azmie Putry, S.Pd., M.Pd.** dengan sentuhan **palet warna kekuningan hangat (Warm Honey, Amber, & Soft Sunshine Gold)**. 

Prinsip desain:
- **Hangat, Ceria, & Menyenangkan (Warmth & Delight):** Warna kuning lembut menciptakan suasana kerja yang ramah dan mencerahkan, tidak membosankan saat memeriksa puluhan esai mahasiswa.
- **Keterbacaan & Kenyamanan Mata (Ergonomic Legibility):** Menghindari warna kuning neon yang menyilaukan. Sebagai gantinya, latar belakang menggunakan warna krem mentega lembut (*Soft Butter/Ivory* `#FFFDF5` dan `#FEF3C7`), dipadukan dengan tipografi warna *Deep Espresso Bronze* (`#451A03`) dan *Rich Amber Slate* (`#78350F`) untuk rasio kontras WCAG AAA.
- **Kewibawaan Akademis:** Warna emas kuning merupakan lambang kebijaksanaan, pencerahan, dan keluhuran ilmu dalam dunia pendidikan.
- **Efisiensi Tindakan 1-Klik:** Tombol salin berbalut aksen emas hangat dengan transisi hijau zamrud instan (*"Tersalin! ✓"*).

---

## 2. Palet Warna (Color Palette)

| Kategori | Nama Warna | Hex Code | Penggunaan |
|---|---|---|---|
| **Identitas Utama** | Amber Gold Prime | `#D97706` | Header navigasi, tombol aksi utama, sorotan kartu aktif |
| **Aksen Cerah** | Warm Honey | `#F59E0B` | Tombol sekunder, ikon, badge interaktif, bilah kemajuan |
| **Sorotan Lembut** | Canary Sunshine | `#FBBF24` | Badge sesi aktif, pendaran hover |
| **Latar Belakang Utama**| Soft Ivory Cream | `#FFFDF5` | Latar utama aplikasi (sangat nyaman dan teduh di mata) |
| **Latar Kotak & Kartu** | Warm Butter / White | `#FFFFFF` | Latar kartu mahasiswa & dialog modal |
| **Garis Batas Lembut** | Honey Border | `#FDE68A` | Pembatas kartu, tabel, dan sel matriks |
| **Teks Utama** | Deep Espresso Bronze | `#451A03` | Judul, nama mahasiswa, dan teks feedback |
| **Teks Pendukung** | Rich Amber Slate | `#78350F` | Label metrik, keterangan tanggal, subjudul |
| **Status Sukses** | Emerald Success | `#059669` | Indikator tuntas dinilai, tombol "Tersalin! ✓" |
| **Peringatan Trajektori**| Warm Amber Alert | `#B45309` | Pita peringatan jika nilai turun dari sesi sebelumnya |
| **Lencana Tugas** | Deep Honey Amber | `#D97706` | Penanda Sesi Tugas (Sesi 3, 5, 7) |
| **Lencana Diskusi** | Mustard Gold | `#CA8A04` | Penanda Sesi Diskusi (Sesi 1, 2, 4, 6, 8) |

---

## 3. Tipografi
- **Keluarga Huruf:** `Plus Jakarta Sans` / `Inter`, sans-serif.
- **Hirarki:**
  - `H1 (Page Title)`: 24px - 28px / Semi-bold (700)
  - `H2 (Section Title)`: 18px - 20px / Bold (700)
  - `H3 (Student Name)`: 16px - 18px / Semi-bold (600)
  - `Body / Feedback Text`: 14px - 15px / Regular (400) dengan `line-height: 1.65`
  - `Meta / Badge`: 11px - 12px / Semi-bold (600)

---

## 4. Komponen Kunci

### A. Kartu Mahasiswa (Student Feedback Card)
- **Header:** Nama mahasiswa dalam huruf kapital rapi warna bronze gelap, badge NIM berlatar kuning muda manis, kode kelas, dan status penyelesaian.
- **Trajektori Nilai Emas:** Pil riwayat nilai sesi (`S1: 85 ➔ S2: 88 ➔ S3: 92`) dengan aksen kuning amber yang menyala lembut.
- **Indikator Peringatan Turun:** Kotak peringatan bernuansa oranye-amber lembut: `⚠️ Peringatan: Nilai lebih rendah dari sesi sebelumnya`.
- **Kotak Feedback Siap Salin:** Wadah teks berlatar putih bersih dengan bingkai emas lembut `#FDE68A` dan tombol `Salin Feedback` berwarna kuning emas hangat (`#D97706`).
- **Mikro-interaksi Salin:** Saat diklik, tombol bertransformasi menjadi hijau zamrud cerah dengan ikon centang `Tersalin! ✓`.

### B. Matriks Progres Kelas x Sesi (4 x 8 Matrix)
- Nuansa kuning madu bergradasi lembut sesuai persentase kelengkapan:
  - 100% tuntas: Latar kuning cerah keemasan dengan ikon centang hijau.
  - Sebagian: Latar krem lembut dengan indikator jumlah pending.
  - Belum dimulai: Latar abu-krem pudar.
- Badge tipe sesi: 💬 Kuning Mustard untuk Diskusi, 📝 Amber Emas untuk Tugas.

### C. Jadwal & Status Pembukaan Sesi
- Sesi berurutan selang 1 minggu.
- Kartu sesi aktif berpendar lembut (*golden glow effect*), memberikan fokus visual langsung pada sesi yang sedang berjalan.
