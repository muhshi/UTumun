# Unified Session Manager, Multi-Session Recap, and Auto-Grader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Membangun arsitektur terpadu automasi Tuton UT dengan auto-relogin persisten saat session habis, rekapitulasi berjenjang status kelengkapan mahasiswa per sesi dan per kelas, serta auto-grader draf nilai dan feedback 2 paragraf siap salin untuk mahasiswa yang belum selesai.

**Architecture:** Modul terpisah berbasis Python: `tuton/auth.py` untuk auto-login dan validasi session persisten; `tuton/scraper.py` untuk penarikan data forum diskusi dinamis multi-sesi; `tuton/matcher.py` untuk rekonsiliasi postingan mahasiswa vs feedback tutor; `tuton/evaluator.py` untuk penilaian berbasis rubrik baku modul BMP UT; dan `main.py` sebagai antarmuka terpadu (Two-Stage Pipeline: Rekapitulasi Status Dulu -> Draf Nilai & Feedback untuk yang Kurang).

**Tech Stack:** Python 3.10+, Playwright, python-dotenv, BeautifulSoup4 / regex parsing, pytest.

---

## File Structure

- `tuton/`: Paket inti sistem automasi tuton
  - `tuton/__init__.py`: Package init & export publik
  - `tuton/config.py`: Konfigurasi konstan (Course IDs, Forum CMID registry, selector Moodle, kredensial)
  - `tuton/auth.py`: Pengelola sesi browser Playwright, verifikasi login, dan auto-relogin transparan
  - `tuton/scraper.py`: Scraper forum diskusi fleksibel multi-sesi (flat mode `&mode=1`)
  - `tuton/matcher.py`: Algoritma pencocokan tanggapan mahasiswa dengan riwayat nilai & feedback tutor
  - `tuton/evaluator.py`: Generator rubrik penilaian resmi & draf feedback 2 paragraf per sesi
  - `tuton/reporter.py`: Generator format laporan rekapitulasi berjenjang (Tabel Ringkasan -> Daftar Mahasiswa Kurang -> Kotak Feedback Siap Salin)
- `main.py`: CLI terpadu untuk Ibu Tutor (`python main.py --recap`, `python main.py --grade`, `python main.py --session 1/2/all`)
- `tests/`: Unit test suite (TDD)
  - `tests/test_config.py`: Pengujian validasi konfigurasi dan registry URL kelas/sesi
  - `tests/test_matcher.py`: Pengujian pencocokan fuzzy nama mahasiswa vs feedback tutor
  - `tests/test_evaluator.py`: Pengujian kalkulasi nilai dan kepatuhan format feedback 2 paragraf
  - `tests/test_reporter.py`: Pengujian output laporan berjenjang (Tabel ringkasan & blok kode ` ```text `)
- `GEMINI.md`: Pembaruan aturan prompt Antigravity untuk menjalankan alur berjenjang baru

---

### Task 1: Environment & Project Configuration Module

**Files:**
- Create: `tuton/__init__.py`
- Create: `tuton/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write test for configuration and registry**

```python
# tests/test_config.py
import pytest
from tuton.config import COURSES, get_forum_cmid, get_course_info

def test_courses_registry():
    assert len(COURSES) == 4
    course_ids = [c["id"] for c in COURSES]
    assert "413073" in course_ids
    assert "413077" in course_ids
    assert "413081" in course_ids
    assert "411401" in course_ids

def test_get_forum_cmid():
    # Sesi 1 cmid check
    assert get_forum_cmid(course_id="413073", session_num=1) == "47302993"
    assert get_forum_cmid(course_id="413077", session_num=1) == "47303711"
    # Sesi 2 cmid check
    assert get_forum_cmid(course_id="413073", session_num=2) == "47303004"
    assert get_forum_cmid(course_id="411401", session_num=2) == "46978750"

def test_get_course_info():
    info = get_course_info("413073")
    assert info is not None
    assert info["code"] == "MKWN4108.2137"
    assert get_course_info("999999") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_config.py -v`  
Expected: FAIL with ModuleNotFoundError or ImportError

- [ ] **Step 3: Implement config module**

```python
# tuton/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SESSION_FILE = str(BASE_DIR / ".auth" / "session.json")
DATA_DIR = str(BASE_DIR / "data")
CHROME_PATH = os.getenv("CHROME_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

UT_USERNAME = os.getenv("UT_USERNAME", "")
UT_PASSWORD = os.getenv("UT_PASSWORD", "")

TUTOR_NAME = "AINUR ROSYIDAH AZMIE PUTRY"
TUTOR_ID = "01007726"

COURSES = [
    {
        "id": "413073",
        "code": "MKWN4108.2137",
        "name": "Bahasa Indonesia 2137",
        "forums": {
            1: {"cmid": "47302993", "name": "Forum Diskusi.1"},
            2: {"cmid": "47303004", "name": "Forum Diskusi.2"},
        }
    },
    {
        "id": "413077",
        "code": "MKWN4108.2141",
        "name": "Bahasa Indonesia 2141",
        "forums": {
            1: {"cmid": "47303711", "name": "Forum Diskusi.1"},
            2: {"cmid": "47303722", "name": "Forum Diskusi.2"},
        }
    },
    {
        "id": "413081",
        "code": "MKWN4108.2145",
        "name": "Bahasa Indonesia 2145",
        "forums": {
            1: {"cmid": "47304429", "name": "Forum Diskusi.1"},
            2: {"cmid": "47304452", "name": "Forum Diskusi.2"},
        }
    },
    {
        "id": "411401",
        "code": "MKWN4108.465",
        "name": "Bahasa Indonesia 465",
        "forums": {
            1: {"cmid": "46978721", "name": "Forum Diskusi.1"},
            2: {"cmid": "46978750", "name": "Forum Diskusi.2"},
        }
    }
]

def get_course_info(course_id: str):
    for c in COURSES:
        if c["id"] == str(course_id):
            return c
    return None

def get_forum_cmid(course_id: str, session_num: int):
    c = get_course_info(course_id)
    if not c:
        return None
    forum = c.get("forums", {}).get(int(session_num))
    return forum["cmid"] if forum else None
```

```python
# tuton/__init__.py
"""UT Tuton Automation & Evaluation Package."""
__version__ = "1.1.0"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_config.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tuton/__init__.py tuton/config.py tests/test_config.py
git commit -m "feat: add tuton configuration module and course registry"
```

---

### Task 2: Robust Auto-Login and Session Management Module

**Files:**
- Create: `tuton/auth.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: Write unit test for auth helper functions**

```python
# tests/test_auth.py
import pytest
from tuton.auth import is_session_expired_indicator

def test_session_expired_indicator_detection():
    assert is_session_expired_indicator("Sesi Anda telah habis. Silakan masuk lagi.") is True
    assert is_session_expired_indicator("Peringatan: sesi anda telah habis") is True
    assert is_session_expired_indicator("Selamat datang di Elearning UT") is False
    assert is_session_expired_indicator("") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_auth.py -v`  
Expected: FAIL with ImportError

- [ ] **Step 3: Implement `tuton/auth.py`**

```python
# tuton/auth.py
import os
import asyncio
from pathlib import Path
from playwright.async_api import BrowserContext, Page, async_playwright
from tuton.config import (
    SESSION_FILE,
    UT_USERNAME,
    UT_PASSWORD,
    CHROME_PATH
)

def is_session_expired_indicator(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    return "sesi anda telah habis" in lower or "session has timed out" in lower

async def perform_login(context: BrowserContext, page: Page) -> bool:
    """Melakukan login otomatis melalui portal MyUT Tutor Eksternal."""
    if not UT_USERNAME or not UT_PASSWORD:
        raise ValueError("UT_USERNAME atau UT_PASSWORD belum diatur pada file .env")

    print("[AUTH] Memulai proses login MyUT...")
    await page.goto("https://elearning.ut.ac.id/login/index.php", wait_until="domcontentloaded")
    await page.wait_for_timeout(1500)

    # Klik tombol login MyUT
    login_btn = page.locator("#btnLoginMyUT")
    if await login_btn.count() > 0:
        await login_btn.click()
        await page.wait_for_timeout(1000)

    # Pilih Tutor Eksternal
    tutor_btn = page.locator("#btnTutorEksternal")
    if await tutor_btn.count() > 0:
        await tutor_btn.click()
        await page.wait_for_timeout(1000)

    # Isi credentials di modal
    await page.fill("#username_modal", UT_USERNAME)
    await page.fill("#password_modal", UT_PASSWORD)

    modal_submit = page.locator('#modalLogin, .modal-content, .modal-body').locator(
        'button[type="submit"], input[type="submit"], button:has-text("Masuk")'
    ).first

    if await modal_submit.count() > 0:
        await modal_submit.click()
    else:
        await page.locator("#password_modal").press("Enter")

    # Tunggu pengalihan ke dashboard /my/
    try:
        await page.wait_for_url(lambda u: "/my/" in u, timeout=30000)
    except Exception:
        # Fallback jika redirect lambat tapi URL sudah berubah
        await page.wait_for_timeout(5000)

    # Simpan state session yang valid
    Path(SESSION_FILE).parent.mkdir(parents=True, exist_ok=True)
    await context.storage_state(path=SESSION_FILE)
    print(f"[AUTH] Login berhasil! Sesi diperbarui dan disimpan di {SESSION_FILE}")
    return True

async def ensure_authenticated_page(context: BrowserContext, page: Page) -> bool:
    """
    Memeriksa validitas sesi saat ini.
    Jika sesi kedaluwarsa atau belum ada, lakukan login ulang secara otomatis.
    """
    print("[AUTH] Memeriksa validitas sesi di e-learning UT...")
    await page.goto("https://elearning.ut.ac.id/my/", wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

    needs_login = False
    current_url = page.url

    if "/login/" in current_url:
        needs_login = True
    elif await page.locator("#btnLoginMyUT").count() > 0:
        needs_login = True
    else:
        # Cek apakah ada pesan atau modal "Sesi Anda telah habis"
        body_text = await page.evaluate("() => document.body.innerText")
        if is_session_expired_indicator(body_text):
            needs_login = True

    if needs_login:
        print("[AUTH] Sesi tidak valid atau telah kedaluwarsa. Menjalankan auto-relogin...")
        return await perform_login(context, page)
    else:
        print("[AUTH] Sesi aktif dan valid!")
        return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_auth.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tuton/auth.py tests/test_auth.py
git commit -m "feat: add persistent session manager and auto-relogin handler"
```

---

### Task 3: Student & Tutor Feedback Reconciliation Matcher Module

**Files:**
- Create: `tuton/matcher.py`
- Test: `tests/test_matcher.py`

- [ ] **Step 1: Write test for fuzzy matcher logic**

```python
# tests/test_matcher.py
import pytest
from tuton.matcher import match_feedbacks_to_students, normalize_name, clean_student_name

def test_clean_student_name():
    assert clean_student_name("Re: Forum Diskusi.1 by AHMAD FADLI") == "AHMAD FADLI"
    assert clean_student_name("Forum Diskusi.2 by 058104929 SAFIRA DIAH") == "SAFIRA DIAH"
    assert clean_student_name("058988712 SYAHRUL RAMANDANA") == "SYAHRUL RAMANDANA"

def test_normalize_name():
    assert normalize_name("Nur 'Azizah") == "nur azizah"
    assert normalize_name("HABIBUR RAHMAN") == "habibur rahman"

def test_match_feedbacks_fuzzy():
    students = [
        {"name": "NUR 'AZIZAH", "nim": "057659672", "score": None, "feedback": None},
        {"name": "HABIBUR RAHMAN", "nim": "057934868", "score": "94", "feedback": None},
        {"name": "FADRI TRI HARTANTO", "nim": "059890447", "score": None, "feedback": None},
    ]
    tutor_posts = [
        {"author": "AINUR ROSYIDAH", "content": "Nur Azizah, jawaban Anda sudah sangat baik..."},
        {"author": "AINUR ROSYIDAH", "content": "Waalaikumsalam saudara Habiburrahman, tanggapan Anda tepat..."},
    ]

    matched = match_feedbacks_to_students(students, tutor_posts)
    
    # Check Nur Azizah matched despite apostrophe
    s1 = next(s for s in matched if s["nim"] == "057659672")
    assert s1["feedback"] is not None
    assert "Nur Azizah" in s1["feedback"]

    # Check Habibur Rahman matched despite compound name
    s2 = next(s for s in matched if s["nim"] == "057934868")
    assert s2["feedback"] is not None

    # Check Fadri has no feedback
    s3 = next(s for s in matched if s["nim"] == "059890447")
    assert s3["feedback"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_matcher.py -v`  
Expected: FAIL with ImportError

- [ ] **Step 3: Implement `tuton/matcher.py`**

```python
# tuton/matcher.py
import re
from typing import List, Dict, Any

GREETING_STOPWORDS = {
    'halo', 'saudara', 'saudari', 'waalaikumsalam', 'warahmatullahi', 'wabarakatuh',
    'wr', 'wb', 'selamat', 'pagi', 'siang', 'sore', 'malam', 'rekan', 'teman', 'mahasiswa',
    'terima', 'kasih', 'jawaban', 'anda', 'yang', 'sampaikan', 'berikan', 'sudah', 'sangat',
    'baik', 'dan', 'menunjukkan', 'pemahaman', 'terhadap', 'mengenai', 'izin', 'menjawab',
    'ibu', 'bapak', 'tutor', 'dosen', 'assalamualaikum', 'assalamu', 'alaikum'
}

def normalize_name(name: str) -> str:
    """Membersihkan simbol dan merapikan spasi."""
    n = re.sub(r'[^a-zA-Z0-9\s]', ' ', name.lower())
    return ' '.join(n.split())

def clean_student_name(author: str) -> str:
    """Membersihkan awalan Moodle dan NIM dari nama mahasiswa."""
    for prefix in [
        "Re: Forum Diskusi.1 by", "Forum Diskusi.1 by",
        "Re: Forum Diskusi.2 by", "Forum Diskusi.2 by",
        "Re: Forum Diskusi by", "Forum Diskusi by", "Re:"
    ]:
        author = author.replace(prefix, "")
    author = re.sub(r"\b\d{9}\b", "", author).strip()
    return author

def match_feedbacks_to_students(students: List[Dict[str, Any]], tutor_posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Mencocokkan postingan feedback tutor ke mahasiswa yang bersangkutan
    menggunakan pencocokan NIM, nama lengkap, dan fuzzy token sapaan pembuka.
    """
    # Clone student list
    res_students = [dict(s) for s in students]

    for fb in tutor_posts:
        content = fb.get("content", "")
        header = content[:200]
        header_norm = normalize_name(header)
        header_clean = re.sub(r'[^a-z0-9]', '', header_norm)

        matched_idx = None

        # 1. Cek kecocokan NIM langsung di teks feedback
        nim_match = re.search(r"\b\d{9}\b", header)
        if nim_match:
            nim_val = nim_match.group(0)
            for idx, s in enumerate(res_students):
                if s.get("nim") == nim_val:
                    matched_idx = idx
                    break

        # 2. Cek kecocokan nama lengkap (tanpa spasi/tanda baca)
        if matched_idx is None:
            for idx, s in enumerate(res_students):
                stu_clean = re.sub(r'[^a-z0-9]', '', normalize_name(s.get("name", "")))
                if stu_clean and len(stu_clean) >= 4 and stu_clean in header_clean:
                    matched_idx = idx
                    break

        # 3. Cek kecocokan multi-token nama pada 5 kata pertama penerima
        if matched_idx is None:
            header_words = [w for w in normalize_name(header).split() if w not in GREETING_STOPWORDS and len(w) >= 3]
            target_tokens = header_words[:4]
            best_score = 0
            best_idx = None
            for idx, s in enumerate(res_students):
                stu_tokens = set(normalize_name(s.get("name", "")).split())
                matches = sum(1 for t in target_tokens if t in stu_tokens)
                if matches > best_score:
                    best_score = matches
                    best_idx = idx
            if best_score >= 1:
                matched_idx = best_idx

        if matched_idx is not None:
            res_students[matched_idx]["feedback"] = content

    return res_students
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_matcher.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tuton/matcher.py tests/test_matcher.py
git commit -m "feat: add robust student-feedback reconciliation matcher"
```

---

### Task 4: Official UT Rubric & Auto-Grader Evaluator Module

**Files:**
- Create: `tuton/evaluator.py`
- Test: `tests/test_evaluator.py`

- [ ] **Step 1: Write test for evaluator and 2-paragraph feedback generator**

```python
# tests/test_evaluator.py
import pytest
from tuton.evaluator import evaluate_submission

def test_evaluate_submission_sesi1():
    student_content = """
    1. Ya, Budi dan Wati sedang berbahasa karena memenuhi hakikat bahasa sebagai sistem lambang bunyi.
    2. Sifat arbitrer bahasa berarti bebas manasuka, namun konvensional disepakati mereka berdua.
    3. Menurut M.A.K. Halliday ada fungsi instrumental, interaksional, personal, dan regulasi.
    BMP MKWN4108 modul 1.
    """
    res = evaluate_submission(student_name="FADRI TRI HARTANTO", content=student_content, session_num=1)
    assert res["score"] >= 85
    paragraphs = [p for p in res["feedback"].split("\n\n") if p.strip()]
    assert len(paragraphs) == 2
    assert "Halo Fadri Tri Hartanto" in paragraphs[0]
    assert "NIM" not in paragraphs[0]
    assert "kelebihan" in paragraphs[0].lower() or "baik" in paragraphs[0].lower()
    assert "catatan" in paragraphs[1].lower() or "saran" in paragraphs[1].lower()

def test_evaluate_submission_sesi2():
    student_content = """
    1. Keterampilan menyimak Ayu, membaca Cinta, berbicara Budi, dan menulis Dani terintegrasi secara padu.
    2. Teori membaca Frank Smith modul hal 1.30: interaksi informasi visual dan non-visual dalam mencari makna.
    3. Tahapan menulis Dani modul hal 1.35: prapenulisan, penulisan, dan pascapenulisan dengan elemen ringkasan dan rekomendasi lingkungan.
    """
    res = evaluate_submission(student_name="ROSI ANINDHITA", content=student_content, session_num=2)
    assert res["score"] >= 90
    paragraphs = [p for p in res["feedback"].split("\n\n") if p.strip()]
    assert len(paragraphs) == 2
    assert "Halo Rosi Anindhita" in paragraphs[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_evaluator.py -v`  
Expected: FAIL with ImportError

- [ ] **Step 3: Implement `tuton/evaluator.py`**

```python
# tuton/evaluator.py
import re
from typing import Dict, Any

def clean_title_name(name: str) -> str:
    words = name.strip().split()
    return " ".join(w.capitalize() for w in words)

def evaluate_submission(student_name: str, content: str, session_num: int) -> Dict[str, Any]:
    """
    Mengevaluasi tanggapan mahasiswa berdasarkan rubrik resmi UT
    dan menghasilkan nilai (0-100) serta feedback tepat 2 paragraf.
    """
    name = clean_title_name(student_name)
    c_lower = content.lower()

    if session_num == 1:
        # Rubrik Sesi 1: Hakikat Bahasa, Arbitrer & Konvensional, M.A.K. Halliday
        has_hakikat = any(k in c_lower for k in ["hakikat", "lambang bunyi", "sistem", "bermakna", "komunikasi"])
        has_arbitrer = "arbitrer" in c_lower or "manasuka" in c_lower
        has_konvensi = "konvensional" in c_lower or "kesepakatan" in c_lower or "disepakati" in c_lower
        has_halliday = "halliday" in c_lower
        has_fungsi = any(k in c_lower for k in ["instrumental", "interaksional", "personal", "regulasi", "representasional", "heuristik"])
        has_bmp = "mkwn4108" in c_lower or "bmp" in c_lower or "modul" in c_lower

        score = 80
        if has_hakikat: score += 4
        if has_arbitrer: score += 3
        if has_konvensi: score += 2
        if has_halliday: score += 3
        if has_fungsi: score += 2
        if has_bmp: score += 2

        score = min(max(score, 82), 95)

        p1 = (
            f"Halo {name}, terima kasih atas partisipasi aktif Saudara dalam Forum Diskusi 1 ini. "
            f"Analisis yang Saudara paparkan sudah sangat baik dan terstruktur, khususnya dalam menjelaskan "
            f"bahwa percakapan antara Budi dan Wati tetap memenuhi hakikat bahasa sebagai sistem lambang bunyi "
            f"bermakna yang disepakati bersama. Pemahaman Saudara mengenai sifat bahasa yang arbitrer namun tetap "
            f"terikat konvensi sosial juga diuraikan secara logis, disertai identifikasi fungsi bahasa menurut "
            f"M.A.K. Halliday yang relevan dengan konteks dialog."
        )

        catatan = []
        if not has_konvensi:
            catatan.append("menegaskan aspek konvensional yang mengikat variasi arbitrer agar pesan tetap tersampaikan")
        if not has_bmp:
            catatan.append("mencantumkan rujukan resmi Buku Materi Pokok (BMP MKWN4108) UT")

        saran_str = " serta ".join(catatan) if catatan else "memperkaya kutipan tuturan langsung dari dialog percakapan untuk memperkuat pembuktian"

        p2 = (
            f"Sebagai catatan penyempurnaan ke depan, Saudara dapat lebih memperkuat analisis dengan {saran_str}. "
            f"Pertahankan antusiasme, ketelitian, dan cara berpikir kritis ini pada sesi-sesi diskusi berikutnya!"
        )

    else:
        # Rubrik Sesi 2: Keterpaduan 4 Keterampilan, Teori Frank Smith, Tiga Tahapan Menulis
        has_keterampilan = all(k in c_lower for k in ["menyimak", "berbicara", "membaca", "menulis"]) or all(k in c_lower for k in ["ayu", "budi", "cinta", "dani"])
        has_smith = "smith" in c_lower
        has_visual = "visual" in c_lower or "non-visual" in c_lower or "skema" in c_lower or "pemaknaan" in c_lower
        has_tahapan = any(k in c_lower for k in ["prapenulisan", "pra-penulisan", "pra penulisan"]) and any(k in c_lower for k in ["penulisan", "drafting"]) and any(k in c_lower for k in ["pascapenulisan", "pasca-penulisan", "revisi", "editing"])
        has_elemen = any(k in c_lower for k in ["ringkasan", "rekomendasi", "laporan akhir"])
        has_bmp = "mkwn4108" in c_lower or "bmp" in c_lower or "modul" in c_lower

        score = 80
        if has_keterampilan: score += 4
        if has_smith: score += 3
        if has_visual: score += 2
        if has_tahapan: score += 4
        if has_elemen: score += 1
        if has_bmp: score += 2

        score = min(max(score, 82), 95)

        p1 = (
            f"Halo {name}, terima kasih atas pengumpulan jawaban diskusi Sesi 2 yang telah Saudara susun dengan "
            f"sangat baik dan terstruktur. Kelebihan utama dari tanggapan Saudara terletak pada kemampuan menguraikan "
            f"kontribusi keempat keterampilan berbahasa (menyimak oleh Ayu, berbicara oleh Budi, membaca oleh Cinta, "
            f"dan menulis oleh Dani) dalam mendukung kesuksesan presentasi kelompok secara padu. Pemahaman Saudara "
            f"terhadap esensi membaca menurut teori Frank Smith juga berhasil dikaitkan secara logis dengan tindakan Cinta "
            f"dalam memilih kutipan yang relevan dan selaras dengan gagasan pokok proyek."
        )

        catatan = []
        if not has_visual:
            catatan.append("memperdalam konsep dua sumber informasi Frank Smith (informasi visual teks dan informasi non-visual berupa skemata pembaca)")
        if not has_elemen:
            catatan.append("memastikan elemen penting laporan Dani (khususnya ringkasan temuan dan rekomendasi aksi nyata pelestarian lingkungan) terintegrasi eksplisit")
        if not has_bmp:
            catatan.append("mencantumkan rujukan formal Buku Materi Pokok (BMP MKWN4108) UT secara lengkap")

        saran_str = " dan ".join(catatan) if catatan else "mengaitkan contoh konkret tantangan penyuntingan bahasa (PUEBI/EYD) pada tahap pascapenulisan Dani"

        p2 = (
            f"Sebagai catatan penyempurnaan ke depan, Saudara dapat lebih memperkuat analisis dengan {saran_str}. "
            f"Secara keseluruhan argumentasi Saudara sudah sangat baik, pertahankan daya kritis dan keaktifan ini pada sesi-sesi selanjutnya!"
        )

    return {
        "name": name,
        "score": score,
        "feedback": f"{p1}\n\n{p2}"
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_evaluator.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tuton/evaluator.py tests/test_evaluator.py
git commit -m "feat: add rubric-based evaluator and 2-paragraph feedback generator"
```

---

### Task 5: Multi-Session Forum Scraper Engine

**Files:**
- Create: `tuton/scraper.py`
- Test: `tests/test_scraper.py`

- [ ] **Step 1: Write test for URL and post parser logic**

```python
# tests/test_scraper.py
import pytest
from tuton.scraper import build_flat_topic_url, parse_post_author_and_nim

def test_build_flat_topic_url():
    url_with_hash = "https://elearning.ut.ac.id/mod/forum/discuss.php?d=11190918#p122494901"
    assert build_flat_topic_url(url_with_hash) == "https://elearning.ut.ac.id/mod/forum/discuss.php?d=11190918&mode=1"

    url_plain = "https://elearning.ut.ac.id/mod/forum/discuss.php?d=12345"
    assert build_flat_topic_url(url_plain) == "https://elearning.ut.ac.id/mod/forum/discuss.php?d=12345&mode=1"

def test_parse_post_author_and_nim():
    author, nim = parse_post_author_and_nim("Re: Forum Diskusi.1 by 058104929 SAFIRA DIAH", "Halo...")
    assert author == "SAFIRA DIAH"
    assert nim == "058104929"

    author2, nim2 = parse_post_author_and_nim("ROSI ANINDHITA", "NIM: 057625959 dari Prodi Sistem Informasi")
    assert author2 == "ROSI ANINDHITA"
    assert nim2 == "057625959"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_scraper.py -v`  
Expected: FAIL with ImportError

- [ ] **Step 3: Implement `tuton/scraper.py`**

```python
# tuton/scraper.py
import re
from typing import Dict, Any, List, Tuple
from playwright.async_api import Page
from tuton.config import get_course_info, get_forum_cmid, COURSES
from tuton.matcher import clean_student_name

def build_flat_topic_url(raw_topic_url: str) -> str:
    """Mengekstrak d=(\d+) dan membangun URL flat mode bersih tanpa fragment hash."""
    d_match = re.search(r'[?&]d=(\d+)', raw_topic_url)
    if not d_match:
        raise ValueError(f"Tidak dapat mengekstrak ID diskusi dari URL: {raw_topic_url}")
    return f"https://elearning.ut.ac.id/mod/forum/discuss.php?d={d_match.group(1)}&mode=1"

def parse_post_author_and_nim(author_raw: str, content: str) -> Tuple[str, str]:
    """Mengekstrak nama bersih dan NIM 9 digit dari header/konten."""
    clean_name = clean_student_name(author_raw)
    nim_match = re.search(r"\b\d{9}\b", author_raw) or re.search(r"NIM\s*[:\.]?\s*(\d{9})", content, re.IGNORECASE)
    nim = nim_match.group(0) if nim_match else ""
    return clean_name, nim

async def scrape_session_forum(page: Page, course_id: str, session_num: int) -> Dict[str, Any]:
    """Menarik seluruh postingan forum diskusi suatu sesi untuk kelas tertentu."""
    cmid = get_forum_cmid(course_id, session_num)
    course_info = get_course_info(course_id)
    if not cmid or not course_info:
        raise ValueError(f"Konfigurasi tidak ditemukan untuk course {course_id} sesi {session_num}")

    forum_url = f"https://elearning.ut.ac.id/mod/forum/view.php?id={cmid}"
    print(f"[SCRAPER] Membuka {course_info['name']} Sesi {session_num} ({forum_url})...")

    await page.goto(forum_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(2500)

    # Ambil tautan topik diskusi pertama
    topic_url = await page.evaluate('''() => {
        const a = document.querySelector('a[href*="/mod/forum/discuss.php?d="]');
        return a ? a.href : null;
    }''')

    if not topic_url:
        print(f"[SCRAPER] Peringatan: Tidak ditemukan topik diskusi pada {forum_url}")
        return {"course": course_info, "session": session_num, "posts": []}

    flat_url = build_flat_topic_url(topic_url)
    print(f"[SCRAPER] Membuka topik dalam flat mode: {flat_url}...")
    await page.goto(flat_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(3500)

    posts = await page.evaluate('''() => {
        const articles = document.querySelectorAll('article.forum-post-container');
        const res = [];
        articles.forEach(art => {
            const postId = art.getAttribute('data-post-id');
            const header = art.querySelector('header');
            const userLink = header ? header.querySelector('a[href*="/user/view.php"]') : null;
            const author = userLink ? userLink.innerText.trim() : (header ? header.innerText.trim().split('\\n')[0] : 'Unknown');
            
            const timeEl = art.querySelector('time');
            const time = timeEl ? timeEl.innerText.trim() : '';

            const contentEl = art.querySelector('.post-content-container');
            const content = contentEl ? contentEl.innerText.trim() : '';

            const rateSelect = art.querySelector(`select#menurating${postId}`) || art.querySelector('select[name="rating"]');
            let rating = null;
            if (rateSelect) {
                const sel = rateSelect.querySelector('option[selected]');
                rating = sel ? sel.value : rateSelect.value;
            }

            res.push({
                postId: postId,
                author: author,
                time: time,
                rating: rating,
                content: content
            });
        });
        return res;
    }''')

    print(f"[SCRAPER] Berhasil mengekstrak {len(posts)} postingan dari {course_info['name']} Sesi {session_num}")
    return {"course": course_info, "session": session_num, "posts": posts}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_scraper.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tuton/scraper.py tests/test_scraper.py
git commit -m "feat: add multi-session forum scraper engine"
```

---

### Task 6: Two-Stage Reporting Module (Rekapitulasi Berjenjang)

**Files:**
- Create: `tuton/reporter.py`
- Test: `tests/test_reporter.py`

- [ ] **Step 1: Write test for report formatting**

```python
# tests/test_reporter.py
import pytest
from tuton.reporter import format_recap_summary_table, format_pending_student_card

def test_format_recap_summary_table():
    summary_data = [
        {
            "session": 1,
            "classes": [
                {"name": "Bahasa Indonesia 2137", "code": "2137", "total": 43, "completed": 41, "pending": 2},
                {"name": "Bahasa Indonesia 2141", "code": "2141", "total": 48, "completed": 48, "pending": 0},
            ]
        }
    ]
    table_md = format_recap_summary_table(summary_data)
    assert "| Sesi | Kelas | Total Mhs | Selesai | Kurang (Pending) |" in table_md
    assert "Bahasa Indonesia 2137" in table_md
    assert "2141" in table_md

def test_format_pending_student_card():
    student_eval = {
        "name": "Fadri Tri Hartanto",
        "nim": "059890447",
        "course_name": "Bahasa Indonesia 2145",
        "session": 1,
        "score": 90,
        "status_desc": "Belum ada nilai & belum ada feedback",
        "feedback": "Halo Fadri Tri Hartanto...\n\nSebagai catatan..."
    }
    card_md = format_pending_student_card(student_eval)
    assert "Fadri Tri Hartanto" in card_md
    assert "90" in card_md
    assert "```text" in card_md
    assert "Halo Fadri Tri Hartanto" in card_md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_reporter.py -v`  
Expected: FAIL with ImportError

- [ ] **Step 3: Implement `tuton/reporter.py`**

```python
# tuton/reporter.py
from typing import List, Dict, Any

def format_recap_summary_table(summary_data: List[Dict[str, Any]]) -> str:
    """Menghasilkan tabel Markdown ringkasan status per sesi dan per kelas."""
    lines = [
        "| Sesi | Kelas | Kode Kelas | Total Mhs | Selesai | Kurang (Pending) | Status |",
        "|:---:|---|---|:---:|:---:|:---:|:---:|"
    ]
    for s_item in summary_data:
        s_num = s_item["session"]
        for c in s_item["classes"]:
            status_badge = "✅ Tuntas" if c["pending"] == 0 else f"⚠️ {c['pending']} Butuh Penanganan"
            lines.append(
                f"| Sesi {s_num} | {c['name']} | `{c['code']}` | {c['total']} | {c['completed']} | **{c['pending']}** | {status_badge} |"
            )
    return "\n".join(lines)

def format_pending_names_list(pending_grouped: Dict[str, List[Dict[str, Any]]]) -> str:
    """Menampilkan daftar nama mahasiswa yang masih kurang per kelas dan per sesi."""
    lines = []
    for group_title, students in pending_grouped.items():
        lines.append(f"### {group_title}")
        if not students:
            lines.append("- *(Semua mahasiswa sudah selesai dinilai dan diberi feedback)*\n")
            continue
        for idx, s in enumerate(students, 1):
            curr_score = f" (Nilai saat ini: {s['score']})" if s.get("score") else " (Belum ada nilai)"
            has_fb = "Sudah ada feedback" if s.get("feedback") else "Belum ada feedback"
            lines.append(f"{idx}. **{s['name']}** (NIM: {s.get('nim') or 'N/A'}) — Status: {has_fb}{curr_score}")
        lines.append("")
    return "\n".join(lines)

def format_pending_student_card(s: Dict[str, Any]) -> str:
    """Menghasilkan kotak feedback siap salin dengan blok kode ```text."""
    nim_str = f" (NIM: {s['nim']})" if s.get("nim") else ""
    return (
        f"#### {s['name']}{nim_str} — {s['course_name']} (Sesi {s['session']})\n"
        f"- **Status:** {s['status_desc']}\n"
        f"- **Rekomendasi Nilai:** **{s['score']}**\n"
        f"- **Draf Feedback Siap Salin:**\n"
        f"```text\n"
        f"{s['feedback']}\n"
        f"```\n"
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_reporter.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tuton/reporter.py tests/test_reporter.py
git commit -m "feat: add two-stage recap and copy-friendly reporting module"
```

---

### Task 7: Unified Orchestrator & CLI Entrypoint

**Files:**
- Create: `main.py`
- Modify: `README.md`
- Modify: `GEMINI.md`

- [ ] **Step 1: Implement `main.py`**

```python
# main.py
import asyncio
import argparse
import os
from playwright.async_api import async_playwright
from tuton.config import COURSES, CHROME_PATH, SESSION_FILE
from tuton.auth import ensure_authenticated_page
from tuton.scraper import scrape_session_forum, parse_post_author_and_nim
from tuton.matcher import match_feedbacks_to_students
from tuton.evaluator import evaluate_submission
from tuton.reporter import (
    format_recap_summary_table,
    format_pending_names_list,
    format_pending_student_card
)

async def run_pipeline(session_target: str = "all", mode: str = "full"):
    """
    Menjalankan pipeline terpadu:
    mode='recap': Tahap 1 saja (Ringkasan & Daftar Nama yang Kurang)
    mode='grade': Tahap 2 saja (Nilai & Feedback)
    mode='full': Tahap 1 kemudian Tahap 2
    """
    sessions = [1, 2] if session_target == "all" else [int(session_target)]

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROME_PATH, headless=True)
        context = await browser.new_context(
            storage_state=SESSION_FILE if os.path.exists(SESSION_FILE) else None,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Step 1: Auto login & session check
        await ensure_authenticated_page(context, page)

        summary_table_data = []
        all_pending_grouped = {}
        all_evaluations = []

        for s_num in sessions:
            class_summaries = []
            for c in COURSES:
                cid = c["id"]
                raw_data = await scrape_session_forum(page, cid, s_num)
                posts = raw_data["posts"]

                topic_post = posts[0] if posts else None
                tutor_posts = [p for p in posts[1:] if "ainur" in p["author"].lower() or "01007726" in p["author"]]
                student_raw = [p for p in posts[1:] if p not in tutor_posts]

                # Deduplikasi mahasiswa
                student_map = {}
                for sp in student_raw:
                    cname, nim = parse_post_author_and_nim(sp["author"], sp["content"])
                    key = nim if nim else cname.lower()
                    score = sp["rating"] if sp["rating"] and sp["rating"] not in ["-1", "-999", "0", ""] else None
                    if key not in student_map:
                        student_map[key] = {
                            "name": cname,
                            "nim": nim,
                            "postId": sp["postId"],
                            "score": score,
                            "content": sp["content"],
                            "feedback": None
                        }
                    else:
                        if not student_map[key]["score"] and score:
                            student_map[key]["score"] = score
                        if len(sp["content"]) > len(student_map[key]["content"]):
                            student_map[key]["content"] = sp["content"]

                # Rekonsiliasi feedback
                matched_students = match_feedbacks_to_students(list(student_map.values()), tutor_posts)
                matched_students.sort(key=lambda x: x["name"])

                completed = [s for s in matched_students if s["score"] and s["feedback"]]
                pending = [s for s in matched_students if not (s["score"] and s["feedback"])]

                class_summaries.append({
                    "name": c["name"],
                    "code": c["code"],
                    "total": len(matched_students),
                    "completed": len(completed),
                    "pending": len(pending)
                })

                group_key = f"Sesi {s_num} — {c['name']} ({c['code']})"
                all_pending_grouped[group_key] = pending

                # Siapkan evaluasi draf nilai & feedback untuk mahasiswa yang pending
                for ps in pending:
                    status_desc = "Belum ada nilai & belum ada feedback"
                    if ps["score"] and not ps["feedback"]:
                        status_desc = f"Sudah ada nilai ({ps['score']}), butuh teks feedback"
                    elif not ps["score"] and ps["feedback"]:
                        status_desc = "Sudah ada feedback, butuh input nilai di web"

                    eval_res = evaluate_submission(ps["name"], ps["content"], s_num)
                    all_evaluations.append({
                        "name": eval_res["name"],
                        "nim": ps.get("nim"),
                        "course_name": c["name"],
                        "session": s_num,
                        "score": ps["score"] if ps["score"] else eval_res["score"],
                        "status_desc": status_desc,
                        "feedback": eval_res["feedback"]
                    })

            summary_table_data.append({"session": s_num, "classes": class_summaries})

        await browser.close()

    # OUTPUT TAHAP 1: REKAPITULASI STATUS
    print("\n" + "="*70)
    print(" TAHAP 1: REKAPITULASI STATUS KELAS & MAHASISWA KURANG")
    print("="*70 + "\n")
    print(format_recap_summary_table(summary_table_data))
    print("\n" + "-"*70)
    print(" DAFTAR MAHASISWA YANG MASIH KURANG (PENDING)")
    print("-"*70 + "\n")
    print(format_pending_names_list(all_pending_grouped))

    # OUTPUT TAHAP 2: NILAI DAN FEEDBACK (Jika mode full atau grade)
    if mode in ["full", "grade"]:
        print("\n" + "="*70)
        print(" TAHAP 2: REKOMENDASI NILAI & DRAF FEEDBACK SIAP SALIN")
        print("="*70 + "\n")
        if not all_evaluations:
            print("Luar biasa! Semua mahasiswa di sesi yang dipilih telah selesai dinilai dan memiliki feedback.")
        else:
            for s_eval in all_evaluations:
                print(format_pending_student_card(s_eval))

def main():
    parser = argparse.ArgumentParser(description="UT Tuton Automation & Evaluation Assistant")
    parser.add_argument("--session", choices=["1", "2", "all"], default="all", help="Pilih sesi yang diproses (1, 2, atau all)")
    parser.add_argument("--mode", choices=["recap", "grade", "full"], default="full", help="recap: ringkasan saja; grade: nilai & feedback; full: keduanya")
    args = parser.parse_args()

    asyncio.run(run_pipeline(session_target=args.session, mode=args.mode))

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Update `GEMINI.md` to document the new unified workflow**

Update `GEMINI.md` section 3 Quick Actions:
- "Rekap semua sesi": `python main.py --mode recap`
- "Cek Sesi 1": `python main.py --session 1 --mode full`
- "Cek Sesi 2": `python main.py --session 2 --mode full`
- "Beri nilai mahasiswa yang kurang": `python main.py --mode full`

- [ ] **Step 3: Update `README.md`**

Update `README.md` to highlight:
- Auto-relogin persisten jika session habis.
- Perintah tunggal `python main.py`.

- [ ] **Step 4: Run test suite to verify all unit tests pass**

Run: `.venv/bin/pytest tests/ -v`  
Expected: PASS all tests

- [ ] **Step 5: Commit and push**

```bash
git add main.py README.md GEMINI.md
git commit -m "feat: add unified CLI orchestrator with two-stage reporting and auto-relogin"
git push origin main
```

---

## Self-Review

1. **Spec Coverage:**
   - Auto session persistence & transparent auto-relogin: Implemented in `tuton/auth.py` and invoked in `main.py`.
   - Tahap 1 (Rekapitulasi status per sesi/kelas & daftar siapa yang kurang): Implemented in `tuton/reporter.py` and `main.py`.
   - Tahap 2 (Nilai & feedback draf siap salin untuk anak yang kurang): Implemented in `tuton/evaluator.py`, `tuton/reporter.py`, and `main.py`.
2. **Placeholder Scan:**
   - No TODOs, no TBDs, full code provided in each task.
3. **Type Consistency:**
   - `session_num` as integer across scraper, evaluator, and reporter.
   - Course IDs strings, `clean_title_name` consistent across modules.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-10-unified-session-recap-grader.md`. Two execution options:

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
