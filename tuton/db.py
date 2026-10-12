import csv
import io
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import tuton.config as config


def suggest_grade(previous_score: Optional[Union[int, float]] = None) -> int:
    """Menghitung rekomendasi nilai otomatis berdasarkan riwayat nilai sesi sebelumnya.
    
    Formula: min(max(previous_score + 2, 85), 95)
    Jika belum ada riwayat nilai sebelumnya, default 85.
    """
    if previous_score is None:
        return 85
    return min(max(int(previous_score) + 2, 85), 95)


class Database:
    """Lapisan persistensi SQLite thread-safe untuk mengelola data Tuton UT."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        if db_path is None:
            data_dir = getattr(config, "DATA_DIR", None)
            if data_dir:
                self.db_path = Path(data_dir) / "tuton.db"
            else:
                self.db_path = Path(config.BASE_DIR) / "data" / "tuton.db"
        else:
            self.db_path = db_path

        self.is_memory = str(self.db_path) == ":memory:"
        if not self.is_memory:
            self.db_path = Path(self.db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._mem_conn = None
        else:
            self.db_path = ":memory:"
            self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._mem_conn.row_factory = sqlite3.Row

        self._lock = threading.Lock()

    @contextmanager
    def get_connection(self):
        """Context manager thread-safe untuk koneksi SQLite dengan row factory sqlite3.Row."""
        if self.is_memory:
            with self._lock:
                try:
                    yield self._mem_conn
                    self._mem_conn.commit()
                except Exception:
                    self._mem_conn.rollback()
                    raise
        else:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=30.0)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def init_db(self) -> None:
        """Inisialisasi tabel SQLite dan data awal (default courses & 8 sessions)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Tabel courses
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS courses (
                    id TEXT PRIMARY KEY,
                    code TEXT,
                    name TEXT
                )
            """)

            # 2. Tabel sessions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_num INTEGER PRIMARY KEY,
                    type TEXT,
                    title TEXT,
                    open_date TEXT,
                    close_date TEXT,
                    status TEXT
                )
            """)

            # 3. Tabel students
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    nim TEXT,
                    name TEXT,
                    course_id TEXT,
                    PRIMARY KEY (nim, course_id)
                )
            """)

            # 4. Tabel submissions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS submissions (
                    student_nim TEXT,
                    course_id TEXT,
                    session_num INTEGER,
                    post_id TEXT,
                    content TEXT,
                    score INTEGER,
                    original_score INTEGER,
                    feedback TEXT,
                    is_copied INTEGER DEFAULT 0,
                    is_grade_copied INTEGER DEFAULT 0,
                    status TEXT,
                    updated_at TEXT,
                    PRIMARY KEY (student_nim, course_id, session_num)
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_submissions_course_session 
                ON submissions (course_id, session_num)
            """)

            # 5. Tabel scan_logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    session_num INTEGER,
                    course_id TEXT,
                    status TEXT,
                    message TEXT
                )
            """)

            # Seed default courses dari config.COURSES
            courses_to_seed = getattr(config, "COURSES", [])
            for c in courses_to_seed:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO courses (id, code, name)
                    VALUES (?, ?, ?)
                    """,
                    (str(c["id"]), str(c["code"]), str(c["name"])),
                )

            # Seed 8 sessions
            # Sesi 3, 5, 7 adalah type 'tugas'; Sesi 1, 2, 4, 6, 8 adalah type 'diskusi'.
            # Open dates berjarak tepat 1 minggu (7 hari).
            base_open_date = datetime(2026, 3, 30, 0, 0, 0)
            for s_num in range(1, 9):
                is_tugas = s_num in (3, 5, 7)
                s_type = "tugas" if is_tugas else "diskusi"
                if is_tugas:
                    tugas_index = (s_num + 1) // 2 - 1  # 3->1, 5->2, 7->3
                    s_title = f"Sesi {s_num}: Tugas {tugas_index}"
                else:
                    s_title = f"Sesi {s_num}: Diskusi {s_num}"

                open_dt = base_open_date + timedelta(days=7 * (s_num - 1))
                close_dt = open_dt + timedelta(days=14)
                open_date_str = open_dt.strftime("%Y-%m-%d")
                close_date_str = close_dt.strftime("%Y-%m-%d")
                s_status = "closed" if s_num <= 3 else ("active" if s_num in (4, 5) else "upcoming")

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO sessions (session_num, type, title, open_date, close_date, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (s_num, s_type, s_title, open_date_str, close_date_str, s_status),
                )

    def get_courses(self) -> List[Dict[str, Any]]:
        """Mengambil seluruh data mata kuliah/kelas yang terdaftar."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM courses ORDER BY id ASC").fetchall()
            return [dict(r) for r in rows]

    def get_sessions(self) -> List[Dict[str, Any]]:
        """Mengambil seluruh jadwal sesi (1-8)."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM sessions ORDER BY session_num ASC").fetchall()
            return [dict(r) for r in rows]

    def upsert_student(self, nim: str, name: str, course_id: str) -> None:
        """Menambahkan atau memperbarui data mahasiswa."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO students (nim, name, course_id)
                VALUES (?, ?, ?)
                ON CONFLICT(nim, course_id) DO UPDATE SET
                    name = excluded.name
                """,
                (str(nim).strip(), str(name).strip(), str(course_id).strip()),
            )

    def get_students(self, course_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Mengambil daftar mahasiswa, opsional difilter berdasarkan course_id."""
        with self.get_connection() as conn:
            if course_id:
                rows = conn.execute(
                    "SELECT * FROM students WHERE course_id = ? ORDER BY nim ASC",
                    (str(course_id),),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM students ORDER BY course_id ASC, nim ASC"
                ).fetchall()
            return [dict(r) for r in rows]

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
        """Menambahkan atau memperbarui data pengumpulan tanggapan/tugas mahasiswa."""
        if updated_at is None:
            updated_at = datetime.now().isoformat()

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO submissions (
                    student_nim, course_id, session_num, post_id, content,
                    score, original_score, feedback, is_copied, is_grade_copied,
                    status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_nim, course_id, session_num) DO UPDATE SET
                    post_id = COALESCE(excluded.post_id, submissions.post_id),
                    content = COALESCE(excluded.content, submissions.content),
                    score = COALESCE(excluded.score, submissions.score),
                    original_score = COALESCE(excluded.original_score, submissions.original_score),
                    feedback = COALESCE(excluded.feedback, submissions.feedback),
                    is_copied = CASE WHEN excluded.status = 'pending' THEN excluded.is_copied WHEN excluded.is_copied != 0 THEN excluded.is_copied ELSE submissions.is_copied END,
                    is_grade_copied = CASE WHEN excluded.status = 'pending' THEN excluded.is_grade_copied WHEN excluded.is_grade_copied != 0 THEN excluded.is_grade_copied ELSE submissions.is_grade_copied END,
                    status = COALESCE(excluded.status, submissions.status),
                    updated_at = excluded.updated_at
                """,
                (
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
                ),
            )

    def get_submission(
        self, student_nim: str, course_id: str, session_num: int
    ) -> Optional[Dict[str, Any]]:
        """Mengambil satu data submission spesifik berdasarkan NIM, course_id, dan session_num."""
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM submissions
                WHERE student_nim = ? AND course_id = ? AND session_num = ?
                """,
                (str(student_nim).strip(), str(course_id).strip(), int(session_num)),
            ).fetchone()
            return dict(row) if row else None

    def get_submissions(
        self,
        course_id: Optional[str] = None,
        session_num: Optional[int] = None,
        student_nim: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Mengambil data submission dengan filter opsional."""
        query = "SELECT * FROM submissions WHERE 1=1"
        params: List[Any] = []

        if course_id:
            query += " AND course_id = ?"
            params.append(str(course_id))
        if session_num is not None:
            query += " AND session_num = ?"
            params.append(int(session_num))
        if student_nim:
            query += " AND student_nim = ?"
            params.append(str(student_nim))
        if status:
            query += " AND status = ?"
            params.append(str(status))

        query += " ORDER BY session_num ASC, student_nim ASC"

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def delete_stale_submissions(
        self, course_id: str, session_num: int, active_nims: List[str]
    ) -> int:
        """Menghapus data submission lama/sintetis yang tidak lagi ada pada hasil pindaian aktual UT."""
        if not active_nims:
            return 0
        placeholders = ",".join("?" for _ in active_nims)
        params: List[Any] = [str(course_id).strip(), int(session_num)] + [str(n).strip() for n in active_nims]
        with self.get_connection() as conn:
            cur = conn.execute(
                f"""
                DELETE FROM submissions
                WHERE course_id = ? AND session_num = ?
                  AND student_nim NOT IN ({placeholders})
                """,
                params,
            )
            return cur.rowcount

    def mark_feedback_copied(
        self, student_nim: str, course_id: str, session_num: int
    ) -> None:
        """Menandai bahwa feedback teks untuk mahasiswa telah disalin (is_copied = 1)."""
        now_str = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE submissions
                SET is_copied = 1, updated_at = ?
                WHERE student_nim = ? AND course_id = ? AND session_num = ?
                """,
                (now_str, str(student_nim).strip(), str(course_id).strip(), int(session_num)),
            )

    def mark_grade_copied(
        self, student_nim: str, course_id: str, session_num: int
    ) -> None:
        """Menandai bahwa nilai angka untuk mahasiswa telah disalin (is_grade_copied = 1)."""
        now_str = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE submissions
                SET is_grade_copied = 1, updated_at = ?
                WHERE student_nim = ? AND course_id = ? AND session_num = ?
                """,
                (now_str, str(student_nim).strip(), str(course_id).strip(), int(session_num)),
            )

    def get_student_trajectory(
        self, student_nim: str, course_id: str
    ) -> List[Dict[str, Any]]:
        """Mengambil lintasan nilai per sesi untuk seorang mahasiswa."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT session_num, score
                FROM submissions
                WHERE student_nim = ? AND course_id = ? AND score IS NOT NULL
                ORDER BY session_num ASC
                """,
                (str(student_nim).strip(), str(course_id).strip()),
            ).fetchall()
            return [
                {"session": r["session_num"], "score": r["score"]}
                for r in rows
            ]

    def get_students_with_trajectory(
        self,
        course_id: Optional[str] = None,
        session_num: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Mengambil daftar mahasiswa lengkap dengan lintasan nilai (trajectory) antar-sesi,
        peringatan jika nilai turun (warning_lower_score), dan rekomendasi nilai otomatis.
        """
        students = self.get_students(course_id=course_id)
        all_subs = self.get_submissions(course_id=course_id)

        # Kelompokkan submission per (student_nim, course_id)
        subs_by_student: Dict[tuple, List[Dict[str, Any]]] = {}
        for sub in all_subs:
            key = (sub["student_nim"], sub["course_id"])
            subs_by_student.setdefault(key, []).append(sub)

        results: List[Dict[str, Any]] = []

        for st in students:
            nim = st["nim"]
            name = st["name"]

            if search:
                s_lower = search.lower().strip()
                if s_lower not in nim.lower() and s_lower not in name.lower():
                    continue

            key = (st["nim"], st["course_id"])
            st_subs = sorted(
                subs_by_student.get(key, []),
                key=lambda x: x["session_num"],
            )

            # Trajectory list berisi sesi yang sudah memiliki nilai
            trajectory = [
                {"session": s["session_num"], "score": s["score"]}
                for s in st_subs
                if s.get("score") is not None
            ]

            if session_num is not None:
                current_sub = next((s for s in st_subs if s["session_num"] == session_num), None)
                # Hanya tampilkan mahasiswa yang aktif berpartisipasi/mengumpulkan pada sesi ini
                if current_sub is None:
                    continue
                current_score = current_sub.get("score")

                # Nilai sesi sebelumnya (sesi paling akhir sebelum session_num yang bernilai)
                prev_scored = [
                    s for s in st_subs
                    if s["session_num"] < session_num and s.get("score") is not None
                ]
                previous_score = prev_scored[-1]["score"] if prev_scored else None
            else:
                current_sub = st_subs[-1] if st_subs else None
                current_score = current_sub.get("score") if current_sub else None

                prev_scored = [
                    s for s in st_subs[:-1]
                    if s.get("score") is not None
                ] if len(st_subs) > 1 else []
                previous_score = prev_scored[-1]["score"] if prev_scored else None

            # Warning jika skor sesi ini lebih rendah dari skor sebelumnya
            warning_lower_score = bool(
                current_score is not None
                and previous_score is not None
                and current_score < previous_score
            )

            suggested_score = suggest_grade(previous_score)

            is_copied = current_sub.get("is_copied", 0) if current_sub else 0
            is_grade_copied = current_sub.get("is_grade_copied", 0) if current_sub else 0
            feedback = current_sub.get("feedback") if current_sub else None

            sub_status = current_sub.get("status", "pending") if current_sub else "pending"
            if sub_status == "pending":
                item_status = "pending"
            elif is_copied == 1 or sub_status == "copied":
                item_status = "copied"
            elif sub_status in ["completed", "graded", "evaluated"]:
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
        """Menghitung metrik rekapitulasi progres penilaian seluruh kelas dan sesi (matriks 4x8)."""
        courses = self.get_courses()
        students = self.get_students()
        submissions = self.get_submissions()

        total_students = len(students)

        # Kelompokkan submission per (course_id, session_num)
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
                # Selesai = status completed/graded/evaluated/copied atau sudah disalin feedback
                completed_subs = [
                    s for s in cs_subs
                    if (s.get("status") in ["completed", "graded", "evaluated", "copied"] or s.get("is_copied") == 1)
                    and s.get("status") != "pending"
                ]
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
        """Mengekspor rekapitulasi matriks progres 4x8 ke format string CSV valid."""
        metrics = self.get_recap_metrics()
        courses = self.get_courses()

        output = io.StringIO()
        writer = csv.writer(output)

        header = ["Course ID", "Course Code", "Course Name"]
        for s in range(1, 9):
            header.append(f"Sesi {s}")
        header.extend(["Total Completed", "Total Pending", "Completion Rate (%)"])
        writer.writerow(header)

        for c in courses:
            cid = c["id"]
            c_matrix = metrics["matrix"].get(cid, {})
            row: List[Any] = [cid, c["code"], c["name"]]
            c_completed = 0
            c_pending = 0
            for s in range(1, 9):
                cell = c_matrix.get(s, {"completed": 0, "pending": 0, "total": 0})
                row.append(f"{cell['completed']}/{cell['total']}")
                c_completed += cell["completed"]
                c_pending += cell["pending"]
            total_slots = c_completed + c_pending
            c_rate = round(c_completed / total_slots * 100, 2) if total_slots > 0 else 0.0
            row.extend([c_completed, c_pending, f"{c_rate}%"])
            writer.writerow(row)

        return output.getvalue()

    def log_scan(
        self,
        session_num: Optional[int],
        course_id: Optional[str],
        status: str,
        message: str,
    ) -> int:
        """Mencatat aktivitas pemindaian ke tabel scan_logs."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO scan_logs (timestamp, session_num, course_id, status, message)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(),
                    int(session_num) if session_num is not None else None,
                    str(course_id) if course_id is not None else None,
                    str(status),
                    str(message),
                ),
            )
            return cur.lastrowid or 0

    def get_scan_logs(
        self,
        course_id: Optional[str] = None,
        session_num: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Mengambil riwayat log pemindaian."""
        query = "SELECT * FROM scan_logs WHERE 1=1"
        params: List[Any] = []

        if course_id:
            query += " AND course_id = ?"
            params.append(str(course_id))
        if session_num is not None:
            query += " AND session_num = ?"
            params.append(int(session_num))

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]


# Instance default & fungsi pembantu tingkat modul
_default_db: Optional[Database] = None


def get_db(db_path: Optional[Union[str, Path]] = None) -> Union[Database, Any]:
    """Mengambil atau menginisialisasi instance Database default (SQLite atau MySQL)."""
    global _default_db
    engine = getattr(config, "DB_ENGINE", "sqlite").lower()
    if engine == "mysql":
        from tuton.mysql_db import MySQLDatabase
        return MySQLDatabase()

    if db_path is not None:
        return Database(db_path=db_path)
    if _default_db is None:
        _default_db = Database()
    return _default_db


def init_db(db_path: Optional[Union[str, Path]] = None) -> Union[Database, Any]:
    """Menginisialisasi skema tabel dan data awal pada database."""
    db = get_db(db_path=db_path)
    db.init_db()
    return db
