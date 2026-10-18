import pytest
from fastapi.testclient import TestClient

from tuton.db import Database
from app.main import app, get_database, get_scanner


@pytest.fixture
def test_db():
    db = Database(":memory:")
    db.init_db()
    cid = db.get_courses()[0]["id"]
    # Seed sample students and submissions
    db.upsert_student(nim="041234567", name="Budi Santoso", course_id=cid)
    db.upsert_student(nim="041234568", name="Siti Aminah", course_id=cid)
    db.upsert_submission(
        student_nim="041234567",
        course_id=cid,
        session_num=1,
        post_id="p101",
        content="Jawaban sesi 1",
        score=85,
        feedback="Bagus sekali",
        status="evaluated",
    )
    return db


@pytest.fixture
def client(test_db):
    app.dependency_overrides[get_database] = lambda: test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "html" in response.headers["content-type"].lower()
    assert "Dashboard" in response.text


def test_get_recap(client, test_db):
    response = client.get("/api/recap")
    assert response.status_code == 200
    data = response.json()
    assert "total_students" in data
    assert "completed_students" in data
    assert "pending_students" in data
    assert "matrix" in data
    assert data["total_students"] >= 2
    assert data["completed_students"] >= 1


def test_get_sessions(client):
    response = client.get("/api/sessions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 8
    assert data[0]["session_num"] == 1


def test_get_students(client, test_db):
    cid = test_db.get_courses()[0]["id"]
    response = client.get("/api/students", params={"course_id": cid, "session_num": 1})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    student = next(s for s in data if s["nim"] == "041234567")
    assert "trajectory" in student
    assert "suggested_score" in student
    assert student["suggested_score"] is not None


def test_post_copy_feedback(client, test_db):
    cid = test_db.get_courses()[0]["id"]
    payload = {
        "student_nim": "041234567",
        "course_id": cid,
        "session_num": 1,
    }
    response = client.post("/api/submissions/copy-feedback", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "success"

    subs = test_db.get_submissions(course_id=cid, session_num=1, student_nim="041234567")
    assert len(subs) == 1
    assert subs[0]["is_copied"] == 1


def test_post_copy_grade(client, test_db):
    cid = test_db.get_courses()[0]["id"]
    payload = {
        "student_nim": "041234567",
        "course_id": cid,
        "session_num": 1,
    }
    response = client.post("/api/submissions/copy-grade", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "success"

    subs = test_db.get_submissions(course_id=cid, session_num=1, student_nim="041234567")
    assert len(subs) == 1
    assert subs[0]["is_grade_copied"] == 1


def test_post_update_submission(client, test_db):
    cid = test_db.get_courses()[0]["id"]
    payload = {
        "student_nim": "041234567",
        "course_id": cid,
        "session_num": 1,
        "score": 90,
        "feedback": "Feedback diperbarui",
        "status": "evaluated",
    }
    response = client.post("/api/submissions/update", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "success"

    subs = test_db.get_submissions(course_id=cid, session_num=1, student_nim="041234567")
    assert len(subs) == 1
    assert subs[0]["score"] == 90
    assert subs[0]["feedback"] == "Feedback diperbarui"


def test_scan_and_status(client, test_db):
    cid = test_db.get_courses()[0]["id"]
    # Test GET /api/scan/status initially
    status_resp = client.get("/api/scan/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "is_running" in status_data
    assert "progress" in status_data
    assert "message" in status_data

    # Test POST /api/scan with dry_run
    scan_resp = client.post("/api/scan", json={"session_num": 1, "course_id": cid, "dry_run": True})
    assert scan_resp.status_code == 200
    scan_data = scan_resp.json()
    assert scan_data.get("status") in ("started", "success")


def test_export_csv(client):
    response = client.get("/api/export")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    assert "attachment" in response.headers.get("content-disposition", "")
    assert "filename=" in response.headers.get("content-disposition", "")
    assert "Course ID" in response.text


def test_post_submit_to_ut_mocked(client, test_db, monkeypatch):
    from unittest.mock import AsyncMock
    import tuton.submitter

    mock_submit = AsyncMock(return_value={"success": True, "message": "Nilai 92 dan feedback berhasil dikirim ke UT!"})
    monkeypatch.setattr(tuton.submitter, "submit_single_grade_to_ut", mock_submit)

    payload = {
        "student_nim": "041234567",
        "course_id": "413073",
        "session_num": 5,
        "score": 92,
        "feedback": "Halo Budi, tugas sangat baik.\n\nPerbaiki daftar pustaka.",
        "student_name": "Budi Santoso",
        "userid": "12345"
    }
    response = client.post("/api/submissions/submit-to-ut", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "berhasil" in data["message"]


def test_root_template_submit_bindings(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    # Pastikan binding tombol submit menggunakan helper aman dan tidak menghasilkan disabled permanen
    assert "isSubmittingUt(student)" in html
    assert "isSubmittedUt(student)" in html
    assert "app.js?v=2.4" in html


def test_scan_multi_sessions_and_courses(client, test_db):
    courses = test_db.get_courses()
    cids = [c["id"] for c in courses[:2]]
    scan_resp = client.post(
        "/api/scan",
        json={
            "session_nums": [1, 2, 4],
            "course_ids": cids,
            "dry_run": True,
        },
    )
    assert scan_resp.status_code == 200
    data = scan_resp.json()
    assert data.get("status") in ["started", "error"]
