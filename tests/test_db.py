import csv
import io
from datetime import datetime, timedelta
import pytest
from tuton.db import Database, suggest_grade

@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_tuton.db"
    db = Database(db_path=db_file)
    db.init_db()
    return db


def test_db_initialization_and_default_courses(test_db):
    """Test DB initialization and default 4 courses (413073, 413077, 413081, 411401)."""
    courses = test_db.get_courses()
    assert len(courses) == 4
    
    course_ids = {c["id"] for c in courses}
    expected_ids = {"413073", "413077", "413081", "411401"}
    assert course_ids == expected_ids

    # Verify fields
    for c in courses:
        assert "id" in c
        assert "code" in c
        assert "name" in c
        assert c["code"].startswith("MKWN4108")


def test_sessions_schedule(test_db):
    """Test 8 sessions schedule:
    - Sesi 3, 5, 7 are type 'tugas'; Sesi 1, 2, 4, 6, 8 are type 'diskusi'.
    - Verify open dates are spaced 1 week apart (7 days apart).
    """
    sessions = test_db.get_sessions()
    assert len(sessions) == 8

    # Sort by session_num
    sorted_sessions = sorted(sessions, key=lambda s: s["session_num"])
    
    for s in sorted_sessions:
        num = s["session_num"]
        if num in (3, 5, 7):
            assert s["type"] == "tugas", f"Session {num} must be 'tugas'"
        else:
            assert s["type"] == "diskusi", f"Session {num} must be 'diskusi'"

    # Verify open dates spaced 7 days apart
    for i in range(len(sorted_sessions) - 1):
        curr_open = datetime.fromisoformat(sorted_sessions[i]["open_date"])
        next_open = datetime.fromisoformat(sorted_sessions[i + 1]["open_date"])
        diff = next_open - curr_open
        assert diff == timedelta(days=7), (
            f"Session {sorted_sessions[i]['session_num']} and {sorted_sessions[i+1]['session_num']} "
            f"open dates are not 7 days apart: {diff}"
        )


def test_student_and_submission_upsert(test_db):
    """Test upserting students and submissions."""
    # Insert student
    test_db.upsert_student(nim="041234567", name="Ahmad Dahlan", course_id="413073")
    students = test_db.get_students(course_id="413073")
    assert len(students) == 1
    assert students[0]["nim"] == "041234567"
    assert students[0]["name"] == "Ahmad Dahlan"

    # Update student name
    test_db.upsert_student(nim="041234567", name="Ahmad Dahlan, S.T.", course_id="413073")
    students = test_db.get_students(course_id="413073")
    assert len(students) == 1
    assert students[0]["name"] == "Ahmad Dahlan, S.T."

    # Insert submission
    test_db.upsert_submission(
        student_nim="041234567",
        course_id="413073",
        session_num=1,
        post_id="post_001",
        content="Jawaban diskusi sesi 1",
        score=88,
        feedback="Ulasan baik",
        status="graded"
    )

    subs = test_db.get_submissions(course_id="413073", session_num=1)
    assert len(subs) == 1
    assert subs[0]["score"] == 88
    assert subs[0]["is_copied"] == 0
    assert subs[0]["is_grade_copied"] == 0

    # Test update_submission alias works identically
    test_db.update_submission(
        student_nim="041234567",
        course_id="413073",
        session_num=1,
        score=92,
        feedback="Ulasan sangat baik",
        is_copied=1,
        is_grade_copied=1,
        status="completed"
    )
    subs = test_db.get_submissions(course_id="413073", session_num=1)
    assert len(subs) == 1
    assert subs[0]["score"] == 92
    assert subs[0]["is_copied"] == 1
    assert subs[0]["is_grade_copied"] == 1
    assert subs[0]["status"] == "completed"


def test_students_with_trajectory_and_lower_score_warning(test_db):
    """Test trajectory calculation, lower score warning, and auto-suggested grade."""
    nim = "041234567"
    course_id = "413073"
    test_db.upsert_student(nim=nim, name="Ahmad Dahlan", course_id=course_id)

    # Session 1 score 88
    test_db.upsert_submission(
        student_nim=nim,
        course_id=course_id,
        session_num=1,
        score=88,
        feedback="Bagus sekali",
        status="graded"
    )

    # Session 2 score 85 (lower than Session 1: 85 < 88)
    test_db.upsert_submission(
        student_nim=nim,
        course_id=course_id,
        session_num=2,
        score=85,
        feedback="Perlu pendalaman referensi BMP",
        status="graded"
    )

    results = test_db.get_students_with_trajectory(course_id=course_id, session_num=2)
    assert len(results) == 1
    res = results[0]

    assert res["nim"] == nim
    assert res["trajectory"] == [{"session": 1, "score": 88}, {"session": 2, "score": 85}]
    assert res["previous_score"] == 88
    assert res["current_score"] == 85
    assert res["warning_lower_score"] is True

    # Auto-suggested grade: min(max(previous_score + 2, 85), 95)
    # previous_score 88 -> 88 + 2 = 90
    assert res["suggested_score"] == 90
    assert suggest_grade(88) == 90
    assert suggest_grade(70) == 85  # max(72, 85)
    assert suggest_grade(96) == 95  # min(98, 95)
    assert suggest_grade(None) == 85


def test_mark_copied_flags(test_db):
    """Test marking feedback and grade as copied."""
    nim = "041234567"
    course_id = "413073"
    test_db.upsert_student(nim=nim, name="Ahmad Dahlan", course_id=course_id)
    test_db.upsert_submission(
        student_nim=nim,
        course_id=course_id,
        session_num=2,
        score=85,
        feedback="Feedback teks",
        status="graded"
    )

    # Initially 0
    subs = test_db.get_submissions(course_id=course_id, session_num=2)
    assert subs[0]["is_copied"] == 0
    assert subs[0]["is_grade_copied"] == 0

    # Mark feedback copied
    test_db.mark_feedback_copied(student_nim=nim, course_id=course_id, session_num=2)
    subs = test_db.get_submissions(course_id=course_id, session_num=2)
    assert subs[0]["is_copied"] == 1
    assert subs[0]["is_grade_copied"] == 0

    # Mark grade copied
    test_db.mark_grade_copied(student_nim=nim, course_id=course_id, session_num=2)
    subs = test_db.get_submissions(course_id=course_id, session_num=2)
    assert subs[0]["is_copied"] == 1
    assert subs[0]["is_grade_copied"] == 1


def test_get_recap_metrics(test_db):
    """Test get_recap_metrics returns total, completed, pending, rate, and 4x8 matrix."""
    # Seed 2 students in course 413073, 1 student in 413077
    test_db.upsert_student(nim="001", name="Mahasiswa 1", course_id="413073")
    test_db.upsert_student(nim="002", name="Mahasiswa 2", course_id="413073")
    test_db.upsert_student(nim="003", name="Mahasiswa 3", course_id="413077")

    # Submissions:
    # 001: Sesi 1 (graded 90), Sesi 2 (graded 88)
    # 002: Sesi 1 (graded 85)
    # 003: Sesi 1 (pending / score None)
    test_db.upsert_submission(student_nim="001", course_id="413073", session_num=1, score=90, status="graded")
    test_db.upsert_submission(student_nim="001", course_id="413073", session_num=2, score=88, status="graded")
    test_db.upsert_submission(student_nim="002", course_id="413073", session_num=1, score=85, status="graded")
    test_db.upsert_submission(student_nim="003", course_id="413077", session_num=1, score=None, status="pending")

    metrics = test_db.get_recap_metrics()

    assert "total_students" in metrics
    assert metrics["total_students"] == 3
    assert "completed" in metrics
    assert metrics["completed"] == 3  # 3 graded submissions
    assert "pending" in metrics
    assert metrics["pending"] >= 1
    assert "completion_rate" in metrics

    # 4x8 Matrix of courses x sessions
    matrix = metrics["matrix"]
    assert len(matrix) == 4  # 4 courses

    expected_course_ids = ["413073", "413077", "413081", "411401"]
    for cid in expected_course_ids:
        assert cid in matrix
        assert len(matrix[cid]) == 8  # 8 sessions per course
        for sess_num in range(1, 9):
            cell = matrix[cid][sess_num]
            assert "completed" in cell
            assert "pending" in cell
            assert "total" in cell

    # Check 413073 session 1 cell
    assert matrix["413073"][1]["completed"] == 2


def test_export_recap_csv(test_db):
    """Test export_recap_csv returns valid CSV string."""
    test_db.upsert_student(nim="001", name="Mahasiswa 1", course_id="413073")
    test_db.upsert_submission(student_nim="001", course_id="413073", session_num=1, score=90, status="graded")

    csv_output = test_db.export_recap_csv()
    assert isinstance(csv_output, str)
    assert len(csv_output) > 0

    # Parse with standard csv reader
    reader = csv.reader(io.StringIO(csv_output))
    rows = list(reader)
    assert len(rows) >= 5  # Header + 4 course rows

    header = rows[0]
    assert "Course ID" in header[0]
    for sess_num in range(1, 9):
        assert any(f"Sesi {sess_num}" in col or f"S{sess_num}" in col for col in header)


def test_thread_safe_context_manager(test_db):
    """Test thread-safe context manager method."""
    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM courses")
        count = cursor.fetchone()[0]
        assert count == 4
