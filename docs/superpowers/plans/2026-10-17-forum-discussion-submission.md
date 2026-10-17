# Pengiriman Otomatis Nilai & Feedback Forum Diskusi UT (Sesi 1, 2, 4, 6, 8) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mengotomatiskan pengiriman nilai (rating dropdown) dan draf feedback 2 paragraf (sebagai balasan/tanggapan forum) untuk sesi diskusi (Sesi 1, 2, 4, 6, 8) di e-learning UT (elearning.ut.ac.id) dengan proteksi anti-duplikasi.

**Architecture:** Membedakan pipeline submission antara modul `mod_assign` (Tugas Sesi 3, 5, 7 via Moodle Grader) dan modul `mod_forum` (Diskusi Sesi 1, 2, 4, 6, 8 via thread discuss flat). Pada forum, sistem menemukan postingan mahasiswa berdasarkan NIM/post_id, memilih dropdown rating nilai, mengecek apakah tutor sudah pernah membalas, membuka form "Tanggapi/Balas", menginjeksi 2 paragraf feedback ke editor Moodle Atto/TinyMCE, dan menekan "Kirim ke forum".

**Tech Stack:** Python 3.11+, Playwright Async API, FastAPI, SQLite / MySQL, Alpine.js frontend.

---

### File Structure Map
- **Modify:** `tuton/submitter.py` — Tambahkan logika lengkap pengiriman forum: seleksi rating, deteksi balasan tutor yang sudah ada, pembukaan form balasan (*reply*), pengisian editor teks balasan Moodle, dan pengiriman ke forum.
- **Create:** `tests/test_forum_submitter.py` — Pengujian unit & mock untuk logika rating forum dan pengiriman balasan forum.
- **Modify:** `app/static/js/app.js` — Penyesuaian label/status toast agar tutor mendapatkan informasi jelas apakah yang dikirimkan adalah Tugas Tertulis atau Tanggapan Diskusi Forum.

---

### Task 1: Write Unit Tests for Forum Rating & Reply Selection Logic

**Files:**
- Create: `tests/test_forum_submitter.py`

- [ ] **Step 1: Write the failing unit tests for forum submitter logic**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tuton.submitter import submit_single_grade_to_ut


@pytest.mark.anyio
async def test_submit_single_grade_to_ut_forum_invalid_cmid(monkeypatch):
    # Test bahwa jika CMID forum tidak ditemukan, sistem mengembalikan error yang informatif
    monkeypatch.setattr("tuton.submitter.get_forum_cmid", lambda cid, snum: None)
    
    res = await submit_single_grade_to_ut(
        course_id="413073",
        session_num=4,
        student_nim="041234567",
        score=90,
        feedback="Halo Budi, tanggapan Anda sangat baik.\n\nPerlu ditambahkan rujukan BMP.",
        student_name="Budi Santoso"
    )
    assert res["success"] is False
    assert "CMID forum diskusi tidak ditemukan" in res["message"]


@pytest.mark.anyio
async def test_submit_single_grade_to_ut_forum_mocked_success(monkeypatch):
    # Mocking Playwright browser dan halaman forum
    monkeypatch.setattr("tuton.submitter.get_forum_cmid", lambda cid, snum: "88888")
    
    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    
    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()
    
    mock_p = MagicMock()
    mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
    
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_p)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    
    monkeypatch.setattr("tuton.submitter.async_playwright", lambda: mock_cm)
    monkeypatch.setattr("tuton.submitter.ensure_authenticated_page", AsyncMock())
    
    # Mock evaluate: topic href -> link, forum actions -> success
    def mock_evaluate(script, *args):
        if "discussionname" in script:
            return "https://elearning.ut.ac.id/mod/forum/discuss.php?d=99999"
        elif "rateSelect" in script or "submit_forum_post" in script:
            return {"rated": True, "replied": True, "already_replied": False}
        return {"rated": True, "replied": True}
        
    mock_page.evaluate = AsyncMock(side_effect=mock_evaluate)
    
    res = await submit_single_grade_to_ut(
        course_id="413073",
        session_num=4,
        student_nim="041234567",
        score=92,
        feedback="Halo Budi, argumen diskusi Anda sangat tepat.\n\nSaran saya perlu diperkaya teori dari BMP.",
        student_name="Budi Santoso"
    )
    assert res["success"] is True
    assert "berhasil" in res["message"].lower()
```

- [ ] **Step 2: Run test to verify it fails initially**

Run: `.venv/bin/pytest tests/test_forum_submitter.py -v`  
Expected: FAIL or mismatch because forum reply logic is not yet implemented.

---

### Task 2: Implement Complete Forum Rating & Reply Submission in `tuton/submitter.py`

**Files:**
- Modify: `tuton/submitter.py:223-270`

- [ ] **Step 1: Implement robust forum post rating and reply mechanism**

Update the `else:` branch in `tuton/submitter.py` for discussion sessions (Sesi 1, 2, 4, 6, 8):
1. Buka halaman diskusi flat (`mode=1` untuk menampilkan seluruh pohon diskusi dalam satu halaman).
2. Temukan postingan spesifik mahasiswa berdasarkan NIM atau Nama.
3. **Rating Nilai:** Cari elemen `select[name*='rating']` di dalam wadah artikel postingan tersebut. Jika nilai saat ini belum sesuai dengan target skor, set `value = targetScore` dan trigger event `change`.
4. **Balasan Feedback (Reply):**
   - Periksa apakah postingan mahasiswa tersebut sudah memiliki balasan dari Tutor (Ainur Rosyidah / NIP: `01007726`).
   - Jika sudah ada balasan, lewati pengiriman balasan agar tidak terjadi duplikasi komentar.
   - Jika belum ada balasan:
     - Cari tombol/tautan "Tanggapi" / "Balas" / "Reply" pada postingan tersebut (`a[href*='reply='], a[data-action='reply'], a:has-text('Tanggapi')`).
     - Klik tombol tanggapi dan tunggu form balasan terbuka (`textarea[name='message'], div[contenteditable='true']`).
     - Injeksi 2 paragraf draf feedback ke editor balasan Moodle.
     - Klik tombol "Kirim ke forum" / "Post to forum" (`button[id*='submit'], input[type='submit'][value*='forum']`).
     - Tunggu hingga balasan terunggah di utas.

- [ ] **Step 2: Run tests to verify implementation passes**

Run: `.venv/bin/pytest tests/test_forum_submitter.py -v`  
Expected: PASS

- [ ] **Step 3: Commit Task 2**

```bash
git add tuton/submitter.py tests/test_forum_submitter.py
git commit -m "feat(submitter): implementasi pengiriman rating dan balasan feedback otomatis untuk forum diskusi"
```

---

### Task 3: UI Feedback & End-to-End Verification

**Files:**
- Modify: `app/static/js/app.js`
- Test: Full pytest suite & Playwright browser test

- [ ] **Step 1: Update UI notification messages in `app.js` to distinguish Tugas vs Diskusi**

In `app/static/js/app.js` method `submitToUt(student)`:
- Jika `isSessionTugas(sNum)`: Tampilkan toast "Mengirim nilai & feedback Tugas Sesi X ke e-learning UT..."
- Jika bukan Tugas: Tampilkan toast "Mengirim nilai rating & komentar balasan Diskusi Sesi X ke forum UT..."

- [ ] **Step 2: Run full regression pytest suite**

Run: `.venv/bin/pytest -v`  
Expected: 65+ passed, 0 failed.

- [ ] **Step 3: Commit and push**

```bash
git add app/static/js/app.js
git commit -m "feat(ui): sesuaikan teks konfirmasi pengiriman untuk forum diskusi vs tugas"
git push origin main
```
