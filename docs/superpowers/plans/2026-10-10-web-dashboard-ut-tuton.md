# Local Web App Asisten Tutor UT MKWN4108 Implementation Plan (Tema Warm Honey & Gold)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Membangun aplikasi Web Dashboard lokal (FastAPI + HTML5 + Tailwind CSS + Alpine.js) bernuansa **Warm Honey & Sunlight Gold (warna kuning madu & emas hangat kesukaan Ibu Ainur)** yang sangat elegan, responsif, nyaman di mata, terintegrasi dengan modul `tuton/`, database lokal SQLite (`data/tuton.db`), validasi trajektori nilai progresif, kartu feedback 1-klik salin, matriks progres 4 kelas x 8 sesi (Sesi 3, 5, 7 Tugas; Sesi 1, 2, 4, 6, 8 Diskusi dengan jadwal pembukaan 1 minggu sekali), dan fitur ekspor CSV/Excel.

**Architecture:** Arsitektur modular memisahkan layer data (`tuton/db.py`), adapter scraping/evaluasi latar belakang (`tuton/scanner_service.py`), REST API backend (`app/main.py`), dan UI responsif modern berbasis Alpine.js + Tailwind CSS bertema Warm Honey Gold yang membaca data secara reaktif dan memberikan umpan balik visual instan tanpa reload halaman.

**Tech Stack:** Python 3, FastAPI, Uvicorn, SQLite3, Tailwind CSS (CDN), Alpine.js, Lucide Icons, Plus Jakarta Sans, Playwright (terintegrasi modul `tuton/`).

---

### Task 1: Environment & Dependencies Setup

**Files:**
- Modify: `requirements.txt`
- Test: `tests/test_deps.py`

- [x] **Step 1: Write failing dependency test**

```python
# tests/test_deps.py
def test_required_packages_installed():
    import fastapi
    import uvicorn
    import pydantic
    assert fastapi.__name__ == "fastapi"
    assert uvicorn.__name__ == "uvicorn"
    assert pydantic.__name__ == "pydantic"
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_deps.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fastapi'`

- [x] **Step 3: Update requirements.txt and install packages**

Update `requirements.txt`:
```text
playwright>=1.40.0
python-dotenv>=1.0.0
requests>=2.31.0
fastapi>=0.110.0
uvicorn>=0.28.0
pydantic>=2.0.0
jinja2>=3.1.0
```

Install command: `.venv/bin/pip install fastapi uvicorn pydantic jinja2`

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_deps.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add requirements.txt tests/test_deps.py
git commit -m "chore: add fastapi, uvicorn, and jinja2 dependencies"
```

---

### Task 2: SQLite Database Schema & Persistence Layer

**Files:**
- Create: `tuton/db.py`
- Test: `tests/test_db.py`

- [x] **Step 1: Write failing database test**

```python
# tests/test_db.py
import pytest
import os
from tuton.db import Database

TEST_DB = "data/test_tuton.db"

@pytest.fixture
def db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    database = Database(db_path=TEST_DB)
    database.init_db()
    yield database
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_db_initialization_and_courses(db):
    courses = db.get_courses()
    assert len(courses) == 4
    codes = [c["code"] for c in courses]
    assert "MKWN4108.2137" in codes
    assert "MKWN4108.465" in codes

def test_db_sessions_schedule(db):
    sessions = db.get_sessions()
    assert len(sessions) == 8
    # Sesi 3, 5, 7 adalah tugas; sisanya diskusi
    assert sessions[0]["type"] == "diskusi" # Sesi 1
    assert sessions[1]["type"] == "diskusi" # Sesi 2
    assert sessions[2]["type"] == "tugas"   # Sesi 3
    assert sessions[3]["type"] == "diskusi" # Sesi 4
    assert sessions[4]["type"] == "tugas"   # Sesi 5

def test_student_and_submission_lifecycle(db):
    db.upsert_student("059123456", "Budi Santoso", "413073")
    db.upsert_submission(
        student_nim="059123456",
        course_id="413073",
        session_num=1,
        score=88,
        feedback="Paragraf 1 apresiasi.\n\nParagraf 2 saran.",
        status="completed"
    )
    db.upsert_submission(
        student_nim="059123456",
        course_id="413073",
        session_num=2,
        score=85, # Nilai turun dari 88!
        feedback="Paragraf 1 evaluasi.\n\nParagraf 2 saran.",
        status="pending"
    )
    
    students = db.get_students_with_trajectory(course_id="413073", session_num=2)
    assert len(students) == 1
    s = students[0]
    assert s["nim"] == "059123456"
    assert s["score"] == 85
    assert len(s["trajectory"]) == 2
    assert s["warning_lower_score"] is True # 85 < 88 memicu peringatan!
    assert s["suggested_score"] >= 90 # Auto-suggested grade progresif

    # Test copy feedback marker
    db.mark_feedback_copied("059123456", "413073", 2)
    updated = db.get_submission("059123456", "413073", 2)
    assert updated["is_copied"] == 1
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tuton.db'`

- [x] **Step 3: Implement SQLite Database Layer (`tuton/db.py`)**

Implement `tuton/db.py`:
- Connection handling with row_factory as dictionary.
- Schema creation: `courses`, `sessions`, `students`, `submissions`, `scan_logs`.
- Seed standard courses (413073, 413077, 413081, 411401) and 8 sessions (with 1-week intervals; Sessions 3, 5, 7 as 'tugas', Sessions 1, 2, 4, 6, 8 as 'diskusi').
- Trajectory calculation logic: queries past sessions for the student, calculates if current score < previous score, and calculates suggested score `min(max(prev_score + 2, 85), 95)`.
- Mark feedback / grade copied.
- Overview recap queries (Total, Selesai, Pending, matrix 4 x 8).

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_db.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add tuton/db.py tests/test_db.py
git commit -m "feat: implement SQLite database layer with trajectory validation and schedule"
```

---

### Task 3: Historical Data Seeder

**Files:**
- Create: `tuton/seed_db.py`
- Test: `tests/test_seed.py`

- [x] **Step 1: Write failing seed test**

```python
# tests/test_seed.py
import os
from tuton.db import Database
from tuton.seed_db import seed_from_markdown_reports

def test_seeder_imports_markdown_data():
    test_db_path = "data/test_seed.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    db = Database(db_path=test_db_path)
    db.init_db()
    count = seed_from_markdown_reports(db)
    assert count > 50 # Harus berhasil memuat ratusan data dari laporan Sesi 1-4
    
    recap = db.get_recap_metrics()
    assert recap["total_students"] > 100
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_seed.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tuton.seed_db'`

- [x] **Step 3: Implement Historical Data Seeder (`tuton/seed_db.py`)**

Parse:
- `SESI1_EVALUATION_REPORT.md` (Sesi 1 Diskusi)
- `SESI2_EVALUATION_REPORT.md` (Sesi 2 Diskusi)
- `SESI3_EVALUATION_REPORT.md` (Sesi 3 Tugas 1)
- `SESI4_EVALUATION_REPORT.md` (Sesi 4 Diskusi 4)
- Load from `data/sessions/course_413073_complete.json`, `data/sessions/sesi2_evaluated_ready.json` if available.
Populate `students` and `submissions` in `data/tuton.db`.

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_seed.py -v`
Expected: PASS

- [x] **Step 5: Run seeder on production `data/tuton.db`**

Run: `.venv/bin/python -m tuton.seed_db`
Expected: Populated `data/tuton.db` with existing data.

- [x] **Step 6: Commit**

```bash
git add tuton/seed_db.py tests/test_seed.py
git commit -m "feat: implement historical data seeder from markdown reports and json caches"
```

---

### Task 4: Background Scanner Service

**Files:**
- Create: `tuton/scanner_service.py`
- Test: `tests/test_scanner_service.py`

- [x] **Step 1: Write test for scanner service**

```python
# tests/test_scanner_service.py
import pytest
from tuton.scanner_service import ScannerService

def test_scanner_service_state():
    service = ScannerService()
    status = service.get_status()
    assert status["is_running"] is False
    assert status["progress"] == 0
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_scanner_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tuton.scanner_service'`

- [x] **Step 3: Implement Background Scanner Service (`tuton/scanner_service.py`)**

- Manages async background task execution.
- Invokes `tuton.scraper.scrape_session_forum` or `scrape_session_assign`.
- Evaluates pending submissions using `tuton.evaluator.evaluate_submission`.
- Updates `data/tuton.db` with newly scraped scores, content, and feedback.
- Provides real-time progress logging (`status["progress"]`, `status["message"]`).

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_scanner_service.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add tuton/scanner_service.py tests/test_scanner_service.py
git commit -m "feat: implement background scanner service"
```

---

### Task 5: FastAPI Application & REST Endpoints

**Files:**
- Create: `app/main.py`
- Create: `app/__init__.py`
- Test: `tests/test_api.py`

- [x] **Step 1: Write failing API test**

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_recap_api():
    response = client.get("/api/recap")
    assert response.status_code == 200
    data = response.json()
    assert "total_students" in data
    assert "completed_students" in data
    assert "pending_students" in data
    assert "matrix" in data

def test_get_sessions_api():
    response = client.get("/api/sessions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 8

def test_get_students_api():
    response = client.get("/api/students?course_id=413073&session_num=1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_copy_feedback_api():
    response = client.post("/api/submissions/copy-feedback", json={
        "nim": "059123456",
        "course_id": "413073",
        "session_num": 1
    })
    assert response.status_code in [200, 404]

def test_export_csv_api():
    response = client.get("/api/export")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'`

- [x] **Step 3: Implement FastAPI Backend Endpoints (`app/main.py`)**

- Mount static files and templates.
- Endpoints:
  - `GET /` -> Render main HTML UI.
  - `GET /api/recap` -> Overview metrics & 4x8 matrix.
  - `GET /api/sessions` -> Sesi 1-8 details (dates, types, status).
  - `GET /api/students` -> List students filtered by course, session, status, search query.
  - `POST /api/submissions/copy-feedback` -> Mark feedback copied.
  - `POST /api/submissions/copy-grade` -> Mark grade copied.
  - `POST /api/submissions/update` -> Manual score or feedback adjustment.
  - `POST /api/scan` -> Trigger background scan.
  - `GET /api/scan/status` -> Check scan progress.
  - `GET /api/export` -> Download CSV recap file.

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_api.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add app/ tests/test_api.py
git commit -m "feat: implement FastAPI app and REST endpoints"
```

---

### Task 6: High-Fidelity Local Web Dashboard UI (Tema Warm Honey & Gold)

**Files:**
- Create: `app/templates/index.html`
- Create: `app/static/css/style.css`
- Create: `app/static/js/app.js`

- [x] **Step 1: Build the UI Structure in `app/templates/index.html` dengan Tema Kuning Emas Hangat**
  - **Header Bernuansa Hangat:** Aksen Warm Honey & Amber Gold (`#F59E0B`, `#D97706`), ikon matahari/emas edukasi ☀️, Judul *"Asisten Tutor UT MKWN4108"*, Badge Profil Ibu Ainur Rosyidah, Tombol Sinkronkan Data UT, Tombol Ekspor Nilai.
  - **4 Kartu Metrik Utama:**
    - Total Mahasiswa (Border Emas Lembut).
    - Selesai Dinilai (Hijau Zamrud Segar).
    - Perlu Tindakan / Pending (Kuning Madu Hangat).
    - Sesi Berjalan (Badge Kuning Amber Aktif).
  - **Matriks Progres 4 Kelas x 8 Sesi:**
    - Sel interaktif 4x8 dengan gradasi warna madu/kuning sesuai tingkat penyelesaian.
    - Penanda ikon jelas: 💬 Kuning Mustard untuk Diskusi (Sesi 1, 2, 4, 6, 8) dan 📝 Amber Emas untuk Tugas (Sesi 3, 5, 7).
    - Info status pembukaan sesi (tiap sesi berselang 1 minggu).
    - Klik langsung sel mana pun untuk memfilter daftar mahasiswa secara instan.
  - **Toolbar Filter & Pencarian:**
    - Dropdown Kelas, Dropdown Sesi (1-8), Tombol Pil Status (Semua / Belum Dinilai / Selesai), Input Pencarian Cepat Nama/NIM.
    - Tombol pemindaian cepat: *"⚡ Pindai Sesi Ini"*.
  - **Kartu Evaluasi Mahasiswa (Student Cards):**
    - Header: Nama mahasiswa dalam huruf kapital tebal (Deep Bronze `#451A03`), badge NIM berlatar kuning muda, kode kelas.
    - **Trajektori Nilai Emas:** Visual pil riwayat nilai (`S1: 85 ➔ S2: 88 ➔ S3: 92`) dengan highlight sesi aktif bernuansa madu.
    - Peringatan Turun Nilai: Kotak peringatan oranye-amber lembut jika nilai sesi saat ini lebih rendah dari sebelumnya.
    - Auto-suggested grade progresif (85–95).
    - Tombol **Salin Nilai** 1-klik.
    - Wadah Feedback Siap Salin (2 paragraf standar UT) berbingkai emas halus dengan tombol **Salin Feedback**:
      - Menyalin teks langsung ke clipboard.
      - Transisi warna cerah ke hijau zamrud (*"Tersalin! ✓"*).
      - Status kartu terbarui menjadi *"Sudah Disalin"*.
  - **Modal Dialog Sinkronisasi:** Menampilkan bilah progres scanning dengan animasi gelombang emas.

- [x] **Step 2: Implement Alpine.js Controller (`app/static/js/app.js`)**
  - Reaktif state management untuk filter kelas, sesi, status, dan pencarian.
  - Fungsi Clipboard API dengan fallback manual.
  - Polling berkala untuk status background scan.
  - Filter instan di sisi klien dengan sinkronisasi ke backend.

- [x] **Step 3: Verify UI rendering and interactions**
  - Pastikan seluruh tampilan, kontras teks, tombol copy, dan visualisasi trajektori bekerja sempurna.

- [x] **Step 4: Commit**

```bash
git add app/templates/index.html app/static/
git commit -m "feat: implement Warm Honey and Gold Alpine.js dashboard UI"
```

---

### Task 7: Startup Script, Documentation & Final Verification

**Files:**
- Create: `run_dashboard.py`
- Modify: `README.md`
- Test: Full end-to-end verification

- [x] **Step 1: Create easy launch script `run_dashboard.py`**
  - Otomatis mengecek dan mengisi database SQLite dari seeder jika belum ada.
  - Menjalankan Uvicorn server pada `http://127.0.0.1:8000`.
  - Memberikan sambutan ramah dan petunjuk penggunaan untuk Ibu Ainur di terminal.

- [x] **Step 2: Update README.md with Quick Start instructions**
  - Menambahkan panduan menjalankan aplikasi dashboard lokal.

- [x] **Step 3: Run comprehensive test suite**
  - Jalankan `.venv/bin/pytest -v` untuk memastikan semua unit test dan integrasi lolos 100%.

- [x] **Step 4: Commit**

```bash
git add run_dashboard.py README.md
git commit -m "feat: add dashboard launch script and update documentation"
```

---
