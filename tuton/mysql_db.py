import csv
import io
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import tuton.config as config
from tuton.db import suggest_grade

try:
    import pymysql
    import pymysql.cursors
    PYMYSQL_AVAILABLE = True
except ImportError:
    PYMYSQL_AVAILABLE = False


class MySQLDatabase:
    """Lapisan persistensi MySQL thread-safe untuk deployment server Tuton UT."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        if not PYMYSQL_AVAILABLE:
            raise ImportError("Paket 'pymysql' tidak ditemukan. Jalankan: pip install pymysql")

        self.host = host or getattr(config, "MYSQL_HOST", "10.133.21.24")
        self.port = port or getattr(config, "MYSQL_PORT", 3306)
        self.user = user or getattr(config, "MYSQL_USER", "root")
        self.password = password or getattr(config, "MYSQL_PASSWORD", "demak3321")
        self.database = database or getattr(config, "MYSQL_DATABASE", "muhshi_utumun")
        self._lock = threading.Lock()

    @contextmanager
    def get_connection(self):
        """Context manager thread-safe untuk koneksi MySQL dengan DictCursor."""
        conn = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
            connect_timeout=5,
        )
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        """Inisialisasi tabel MySQL dan data awal (default courses & 8 sessions)."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # 1. Tabel courses
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS courses (
                        id VARCHAR(64) PRIMARY KEY,
                        code VARCHAR(64) NOT NULL,
                        name VARCHAR(255) NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # 2. Tabel sessions
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_num INT PRIMARY KEY,
                        type VARCHAR(32) NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        open_date VARCHAR(64),
                        close_date VARCHAR(64),
                        status VARCHAR(32) NOT NULL DEFAULT 'upcoming'
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # 3. Tabel students
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS students (
                        nim VARCHAR(64) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        course_id VARCHAR(64) NOT NULL,
                        PRIMARY KEY (nim, course_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # 4. Tabel submissions
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS submissions (
                        student_nim VARCHAR(64) NOT NULL,
                        course_id VARCHAR(64) NOT NULL,
                        session_num INT NOT NULL,
                        post_id VARCHAR(64),
                        content LONGTEXT,
                        score INT,
                        original_score INT,
                        feedback LONGTEXT,
                        is_copied TINYINT NOT NULL DEFAULT 0,
                        is_grade_copied TINYINT NOT NULL DEFAULT 0,
                        status VARCHAR(32) NOT NULL DEFAULT 'draft',
                        updated_at VARCHAR(64),
                        PRIMARY KEY (student_nim, course_id, session_num)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # 5. Tabel scan_logs
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS scan_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        timestamp VARCHAR(64) NOT NULL,
                        session_num INT,
                        course_id VARCHAR(64),
                        status VARCHAR(32) NOT NULL,
                        message TEXT
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # Seeding default courses
                for c in getattr(config, "COURSES", []):
                    cursor.execute("""
                        INSERT INTO courses (id, code, name)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE code = VALUES(code), name = VALUES(name)
                    """, (str(c["id"]), str(c["code"]), str(c["name"])))

                # Seeding default 8 sessions (interval 7 hari)
                base_start = datetime(2026, 9, 14, 0, 0, 0)
                now = datetime.now()
                for s in range(1, 9):
                    s_type = "tugas" if s in [3, 5, 7] else "diskusi"
                    s_title = f"Tugas { (s - 1) // 2 }" if s_type == "tugas" else f"Forum Diskusi {s}"
                    open_dt = base_start + timedelta(days=(s - 1) * 7)
                    close_dt = open_dt + timedelta(days=13, hours=23, minutes=59)

                    if now > close_dt:
                        s_status = "closed"
                    elif now >= open_dt:
                        s_status = "active"
                    else:
                        s_status = "upcoming"

                    cursor.execute("""
                        INSERT INTO sessions (session_num, type, title, open_date, close_date, status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            type = VALUES(type),
                            title = VALUES(title),
                            open_date = VALUES(open_date),
                            close_date = VALUES(close_date),
                            status = VALUES(status)
                    """, (s, s_type, s_title, open_dt.strftime("%Y-%m-%d"), close_dt.strftime("%Y-%m-%d"), s_status))

    def get_courses(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM courses ORDER BY id ASC")
                return list(cursor.fetchall())

    def get_sessions(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM sessions ORDER BY session_num ASC")
                return list(cursor.fetchall())

    def upsert_student(self, nim: str, name: str, course_id: str) -> None:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO students (nim, name, course_id)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE name = VALUES(name)
                """, (str(nim).strip(), str(name).strip(), str(course_id).strip()))

    def get_students(self, course_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                if course_id:
                    cursor.execute("SELECT * FROM students WHERE course_id = %s ORDER BY nim ASC", (str(course_id),))
                else:
                    cursor.execute("SELECT * FROM students ORDER BY course_id ASC, nim ASC")
                return list(cursor.fetchall())

    def upsert_submission(
        self,
        student_nim: str,
        course_id: str,
        session_num: int,
        post_id: Optional[str] = None,
        content: Optional[str] = None,
        score: Optional[int] = None,
        original_score: Optional[int] = None,
        feedback: Optional[str] = None,
        is_copied: int = 0,
        is_grade_copied: int = 0,
        status: str = "draft",
        updated_at: Optional[str] = None,
    ) -> None:
        if updated_at is None:
            updated_at = datetime.now().isoformat()

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO submissions (
                        student_nim, course_id, session_num, post_id, content,
                        score, original_score, feedback, is_copied, is_grade_copied,
                        status, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        post_id = COALESCE(VALUES(post_id), submissions.post_id),
                        content = COALESCE(VALUES(content), submissions.content),
                        score = COALESCE(VALUES(score), submissions.score),
                        original_score = COALESCE(VALUES(original_score), submissions.original_score),
                        feedback = COALESCE(VALUES(feedback), submissions.feedback),
                        is_copied = CASE WHEN VALUES(is_copied) != 0 THEN VALUES(is_copied) ELSE submissions.is_copied END,
                        is_grade_copied = CASE WHEN VALUES(is_grade_copied) != 0 THEN VALUES(is_grade_copied) ELSE submissions.is_grade_copied END,
                        status = COALESCE(VALUES(status), submissions.status),
                        updated_at = VALUES(updated_at)
                """, (
                    str(student_nim).strip(),
                    str(course_id).strip(),
                    int(session_num),
                    post_id,
                    content,
                    score,
                    original_score,
                    feedback,
                    int(is_copied),
                    int(is_grade_copied),
                    status,
                    updated_at,
                ))

    def get_submission(
        self, student_nim: str, course_id: str, session_num: int
    ) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM submissions
                    WHERE student_nim = %s AND course_id = %s AND session_num = %s
                """, (str(student_nim), str(course_id), int(session_num)))
                return cursor.fetchone()

    def get_submissions(
        self,
        course_id: Optional[str] = None,
        session_num: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM submissions WHERE 1=1"
        params: List[Any] = []
        if course_id:
            query += " AND course_id = %s"
            params.append(str(course_id))
        if session_num is not None:
            query += " AND session_num = %s"
            params.append(int(session_num))
        if status:
            query += " AND status = %s"
            params.append(str(status))

        query += " ORDER BY course_id ASC, session_num ASC, student_nim ASC"
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, tuple(params))
                return list(cursor.fetchall())

    def mark_feedback_copied(
        self, student_nim: str, course_id: str, session_num: int
    ) -> None:
        now_str = datetime.now().isoformat()
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE submissions
                    SET is_copied = 1, status = 'copied', updated_at = %s
                    WHERE student_nim = %s AND course_id = %s AND session_num = %s
                """, (now_str, str(student_nim), str(course_id), int(session_num)))

    def mark_grade_copied(
        self, student_nim: str, course_id: str, session_num: int
    ) -> None:
        now_str = datetime.now().isoformat()
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE submissions
                    SET is_grade_copied = 1, updated_at = %s
                    WHERE student_nim = %s AND course_id = %s AND session_num = %s
                """, (now_str, str(student_nim), str(course_id), int(session_num)))

    def get_student_trajectory(
        self, student_nim: str, course_id: str
    ) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT session_num, score, status, is_copied
                    FROM submissions
                    WHERE student_nim = %s AND course_id = %s AND score IS NOT NULL
                    ORDER BY session_num ASC
                """, (str(student_nim), str(course_id)))
                rows = cursor.fetchall()
                return [{"session": r["session_num"], "score": r["score"]} for r in rows]

    def get_students_with_trajectory(
        self,
        course_id: Optional[str] = None,
        session_num: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        students = self.get_students(course_id=course_id)
        all_submissions = self.get_submissions(course_id=course_id)

        subs_by_student: Dict[str, Dict[int, Dict[str, Any]]] = {}
        for sub in all_submissions:
            nim_key = sub["student_nim"]
            subs_by_student.setdefault(nim_key, {})[sub["session_num"]] = sub

        results: List[Dict[str, Any]] = []
        for st in students:
            nim = st["nim"]
            name = st["name"]

            if search:
                s_lower = search.lower().strip()
                if s_lower not in nim.lower() and s_lower not in name.lower():
                    continue

            student_subs = subs_by_student.get(nim, {})
            current_sub = student_subs.get(session_num) if session_num is not None else None

            if session_num is not None:
                current_sub = next((s for s in student_subs.values() if s["session_num"] == session_num), None)
                if current_sub is None:
                    continue
                current_score = current_sub.get("score")
                previous_score: Optional[int] = None
                for prev_s in range(session_num - 1, 0, -1):
                    if prev_s in student_subs and student_subs[prev_s].get("score") is not None:
                        previous_score = student_subs[prev_s]["score"]
                        break
            else:
                current_sub = student_subs[max(student_subs.keys())] if student_subs else None
                current_score = current_sub.get("score") if current_sub else None
                prev_scored = [
                    s for s in sorted(student_subs.values(), key=lambda x: x["session_num"])[:-1]
                    if s.get("score") is not None
                ] if len(student_subs) > 1 else []
                previous_score = prev_scored[-1]["score"] if prev_scored else None

            trajectory: List[Dict[str, Any]] = []
            for s_idx in sorted(student_subs.keys()):
                sc = student_subs[s_idx].get("score")
                if sc is not None:
                    trajectory.append({"session": s_idx, "score": sc})

            warning_lower_score = bool(
                current_score is not None
                and previous_score is not None
                and current_score < previous_score
            )

            suggested_score = suggest_grade(previous_score)
            is_copied = current_sub.get("is_copied", 0) if current_sub else 0
            is_grade_copied = current_sub.get("is_grade_copied", 0) if current_sub else 0
            feedback = current_sub.get("feedback") if current_sub else None

            if is_copied == 1:
                item_status = "copied"
            elif current_score is not None and feedback:
                item_status = "completed"
            else:
                item_status = "pending"

            if status:
                if status == "completed" and item_status not in ["completed", "copied"]:
                    continue
                elif status in ["pending", "draft"] and item_status in ["completed", "copied"]:
                    continue

            results.append({
                "nim": st["nim"],
                "name": st["name"],
                "course_id": st["course_id"],
                "trajectory": trajectory,
                "current_session": session_num if session_num is not None else (current_sub["session_num"] if current_sub else None),
                "current_score": current_score,
                "previous_score": previous_score,
                "warning_lower_score": warning_lower_score,
                "suggested_score": suggested_score,
                "is_copied": is_copied,
                "is_grade_copied": is_grade_copied,
                "feedback": feedback,
                "status": item_status,
                "submission": current_sub,
            })

        return results

    def get_recap_metrics(self) -> Dict[str, Any]:
        courses = self.get_courses()
        students = self.get_students()
        submissions = self.get_submissions()

        total_students = len(students)

        subs_by_cs: Dict[tuple, List[Dict[str, Any]]] = {}
        for sub in submissions:
            key = (sub["course_id"], sub["session_num"])
            subs_by_cs.setdefault(key, []).append(sub)

        matrix: Dict[str, Dict[int, Dict[str, Any]]] = {}
        total_completed = 0
        total_pending = 0

        for c in courses:
            cid = c["id"]
            matrix[cid] = {}

            for s_num in range(1, 9):
                cs_subs = subs_by_cs.get((cid, s_num), [])
                completed_subs = [s for s in cs_subs if s.get("score") is not None]
                completed_count = len(completed_subs)
                total_in_session = len(cs_subs)
                pending_count = max(0, total_in_session - completed_count)
                rate = round(completed_count / total_in_session * 100, 2) if total_in_session > 0 else 0.0

                matrix[cid][s_num] = {
                    "course_id": cid,
                    "session_num": s_num,
                    "completed": completed_count,
                    "pending": pending_count,
                    "total": total_in_session,
                    "rate": rate,
                }
                total_completed += completed_count
                total_pending += pending_count

        total_slots = total_completed + total_pending
        overall_rate = round(total_completed / total_slots * 100, 2) if total_slots > 0 else 0.0

        return {
            "total_students": total_students,
            "completed": total_completed,
            "pending": total_pending,
            "completion_rate": overall_rate,
            "matrix": matrix,
        }

    def export_recap_csv(self) -> str:
        metrics = self.get_recap_metrics()
        courses = self.get_courses()

        output = io.StringIO()
        writer = csv.writer(output)

        header = ["Course ID", "Course Code", "Course Name"]
        for s in range(1, 9):
            header.append(f"Sesi {s}")
        writer.writerow(header)

        for c in courses:
            cid = c["id"]
            row = [cid, c["code"], c["name"]]
            c_matrix = metrics["matrix"].get(cid, {})
            for s in range(1, 9):
                s_info = c_matrix.get(s, {})
                comp = s_info.get("completed", 0)
                tot = s_info.get("total", 0)
                pct = s_info.get("rate", 0.0)
                row.append(f"{comp}/{tot} ({pct}%)")
            writer.writerow(row)

        return output.getvalue()

    def log_scan(
        self,
        session_num: Optional[int],
        course_id: Optional[str],
        status: str,
        message: str,
    ) -> None:
        now_str = datetime.now().isoformat()
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO scan_logs (timestamp, session_num, course_id, status, message)
                    VALUES (%s, %s, %s, %s, %s)
                """, (now_str, session_num, course_id, status, message))
