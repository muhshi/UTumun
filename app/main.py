from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from tuton.db import Database, get_db
from tuton.scanner_service import ScannerService, scanner_service

# Paths
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Inisialisasi FastAPI App
app = FastAPI(
    title="Asisten Tutor Online UT (MKWN4108)",
    description="Sistem otomasi, evaluasi, dan rekapitulasi penilaian tutorial online UT.",
    version="1.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files & Templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# Dependency Injections
def get_database() -> Database:
    """Dependency provider untuk instance database dengan graceful fallback."""
    db = get_db()
    try:
        db.init_db()
        return db
    except Exception as e:
        if getattr(config, "DB_ENGINE", "sqlite").lower() == "mysql":
            import logging
            logging.getLogger("tuton.db").warning(
                f"[!] Gagal terhubung ke MySQL ({e}). Beralih otomatis ke SQLite lokal (data/tuton.db)."
            )
            local_db = Database()
            local_db.init_db()
            return local_db
        raise


def get_scanner() -> ScannerService:
    """Dependency provider untuk scanner service."""
    return scanner_service


# Request Schemas
class CopyFeedbackRequest(BaseModel):
    student_nim: str
    course_id: str
    session_num: int


class CopyGradeRequest(BaseModel):
    student_nim: str
    course_id: str
    session_num: int


class UpdateSubmissionRequest(BaseModel):
    student_nim: str
    course_id: str
    session_num: int
    score: Optional[int] = None
    original_score: Optional[int] = None
    feedback: Optional[str] = None
    status: Optional[str] = "evaluated"


class ScanRequest(BaseModel):
    session_num: Optional[int] = None
    course_id: Optional[str] = None
    dry_run: bool = False


# Root Endpoint
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Menampilkan antarmuka dashboard web utama."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"title": "Dashboard Tutor Online UT"},
    )


# REST API Endpoints
@app.get("/api/recap")
def get_recap(db: Database = Depends(get_database)) -> Dict[str, Any]:
    """Mengambil rekapitulasi progres penilaian seluruh kelas dan sesi."""
    metrics = db.get_recap_metrics()
    total_students = metrics.get("total_students", 0)
    completed = metrics.get("completed", 0)
    pending = metrics.get("pending", 0)
    completion_rate = metrics.get("completion_rate", 0.0)
    matrix = metrics.get("matrix", {})

    return {
        "total_students": total_students,
        "completed_students": completed,
        "pending_students": pending,
        "completed": completed,
        "pending": pending,
        "completion_rate": completion_rate,
        "matrix": matrix,
    }


@app.get("/api/courses")
def get_courses(db: Database = Depends(get_database)) -> List[Dict[str, Any]]:
    """Mengambil daftar 4 kelas perkuliahan."""
    return db.get_courses()


@app.get("/api/sessions")
def get_sessions(db: Database = Depends(get_database)) -> List[Dict[str, Any]]:
    """Mengambil daftar 8 sesi perkuliahan."""
    return db.get_sessions()


@app.get("/api/students")
def get_students(
    course_id: Optional[str] = None,
    session_num: Optional[int] = None,
    db: Database = Depends(get_database),
) -> List[Dict[str, Any]]:
    """Mengambil daftar mahasiswa beserta trajectory nilai dan rekomendasi skor."""
    return db.get_students_with_trajectory(
        course_id=course_id,
        session_num=session_num,
    )


@app.post("/api/submissions/copy-feedback")
def copy_feedback(
    payload: CopyFeedbackRequest,
    db: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Menandai bahwa feedback teks mahasiswa telah disalin ke clipboard."""
    db.mark_feedback_copied(
        student_nim=payload.student_nim,
        course_id=payload.course_id,
        session_num=payload.session_num,
    )
    return {
        "status": "success",
        "message": "Feedback berhasil ditandai telah disalin",
    }


@app.post("/api/submissions/copy-grade")
def copy_grade(
    payload: CopyGradeRequest,
    db: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Menandai bahwa nilai angka mahasiswa telah disalin ke clipboard."""
    db.mark_grade_copied(
        student_nim=payload.student_nim,
        course_id=payload.course_id,
        session_num=payload.session_num,
    )
    return {
        "status": "success",
        "message": "Nilai berhasil ditandai telah disalin",
    }


@app.post("/api/submissions/update")
def update_submission(
    payload: UpdateSubmissionRequest,
    db: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Memperbarui nilai dan feedback tanggapan mahasiswa."""
    db.upsert_submission(
        student_nim=payload.student_nim,
        course_id=payload.course_id,
        session_num=payload.session_num,
        score=payload.score,
        original_score=payload.original_score,
        feedback=payload.feedback,
        status=payload.status or "evaluated",
    )
    return {
        "status": "success",
        "message": "Submission berhasil diperbarui",
    }


@app.post("/api/scan")
async def start_scan(
    payload: Optional[ScanRequest] = None,
    scanner: ScannerService = Depends(get_scanner),
    db: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Memulai proses background scan untuk scraping dan evaluasi."""
    scanner.db = db
    session_num = payload.session_num if payload else None
    course_id = payload.course_id if payload else None
    dry_run = payload.dry_run if payload else False

    result = await scanner.start_scan(
        session_num=session_num,
        course_id=course_id,
        dry_run=dry_run,
    )
    return result


@app.get("/api/scan/status")
def get_scan_status(scanner: ScannerService = Depends(get_scanner)) -> Dict[str, Any]:
    """Mengambil status pemindaian latar belakang terkini."""
    return scanner.get_status()


@app.get("/api/export")
def export_csv(db: Database = Depends(get_database)) -> Response:
    """Mengekspor rekapitulasi progres penilaian dalam format CSV."""
    csv_content = db.export_recap_csv()
    filename = f"recap_tuton_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
