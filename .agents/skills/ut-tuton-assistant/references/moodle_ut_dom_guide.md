# Panduan Arsitektur DOM & Automasi E-Learning UT (Moodle 3.9+)

Dokumen ini menjelaskan struktur DOM web `elearning.ut.ac.id` dengan tema `mb2iq` untuk menghindari kesalahan penargetan elemen pada proses evaluasi dan pengiriman balasan/nilai.

---

## 1. Forum Diskusi (Discussion Forum)

### Struktur Halaman Topik Diskusi (`discuss.php?d=<discussion_id>`)
- Seluruh postingan dibungkus dalam elemen `<article class="forum-post-container ...">`.
- **PERINGATAN KRITIS (Indeks 0):**
  - Elemen artikel pertama (`index: 0` atau `p<main_topic_id>`) adalah **postingan instruktur/topik utama**.
  - Pada tema `mb2iq`, artikel indeks 0 sering kali secara struktural membungkus postingan balasan mahasiswa di dalamnya.
  - **Aturan Wajib:** Saat mencari mahasiswa, **SELALU abaikan artikel indeks 0**. Periksa kecocokan nama/NIM hanya pada elemen header (`<header>` atau `.author`) di artikel balasan mahasiswa (`index > 0`).
- **Post ID Mahasiswa:**
  - Setiap balasan mahasiswa memiliki atribut unik: `id="p<postId>"` dan `data-post-id="<postId>"`.
  - Database telah menyimpan `postId` ini pada kolom `submissions.post_id`. Selalu gunakan `postId` ini untuk mencari artikel secara deterministik.
- **Tombol Reply / Balas:**
  - Pada artikel mahasiswa, tautan balas berbentuk: `https://elearning.ut.ac.id/mod/forum/post.php?reply=<postId>`.

### Struktur Halaman Form Balasan (`post.php?reply=<postId>`)
- Halaman ini menggunakan editor teks bawaan Moodle (TinyMCE 3 atau Atto).
- **Injeksi TinyMCE 3:**
  - Iframe editor: `iframe#id_message_ifr`.
  - Body dokumen iframe: `iframe.contentDocument.body`.
  - Textarea cadangan: `textarea#id_message` (biasanya `display: none`).
  - **Sinkronisasi Wajib:** Panggil `window.tinyMCE.triggerSave()` sebelum mengirimkan form agar teks di dalam iframe disalin ke textarea form data.
- **Tombol Submit Balasan:**
  - Selector spesifik: `form#mformforum input#id_submitbutton`.

---

## 2. Penilaian Rating Diskusi (Forum Rating AJAX)

- Pada artikel balasan mahasiswa, form penilaian rating berada di bawah konten:
  - Form: `form.post-rating` atau `form[action*='rating']`.
  - Dropdown Nilai: `select[name*='rating']` atau `select.post-rating-menu`.
- Nilai dikirim via AJAX saat event `change` terpicu pada dropdown nilai tersebut.

---

## 3. Penugasan / Assignment (Tugas 1, 2, 3)

### Struktur Halaman Penilaian (`mod/assign/view.php?id=<cmid>&action=grader`)
- Web UT menggunakan Moodle Grader UI yang memuat informasi pengumpulan mahasiswa.
- **Field Nilai:** `input#id_grade` atau `input[name='grade']`.
- **Field Feedback:**
  - Editor iframe feedback: `iframe#id_assignfeedbackcomments_editor_ifr` atau textarea `textarea#id_assignfeedbackcomments_editor`.
- **Tombol Simpan:** `button[name='savechanges']` atau `input#id_submitbutton`.

---

## 4. Keamanan Sesi & Otentikasi
- File sesi tersimpan di `.auth/session.json`.
- Jika sesi kedaluwarsa, helper `ensure_authenticated_page` secara otomatis melakukan *auto-relogin* via portal MyUT menggunakan kredensial di `.env`.
