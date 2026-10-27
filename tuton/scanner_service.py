import asyncio
import os
from typing import Any, Dict, List, Optional, Union
from playwright.async_api import async_playwright

from tuton.auth import ensure_authenticated_page
from tuton.config import CHROME_PATH, COURSES, SESSION_FILE
from tuton.db import Database, get_db
from tuton.evaluator import evaluate_submission
from tuton.gemini_evaluator import evaluate_with_gemini
from tuton.matcher import match_feedbacks_to_students
from tuton.scraper import (
    parse_post_author_and_nim,
    scrape_session_assign,
    scrape_session_forum,
)


class ScannerService:
    """Layanan pemindaian latar belakang (background scanner service) untuk e-learning UT."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db if db is not None else get_db()
        self.is_running: bool = False
        self.progress: int = 0
        self.message: str = "Siap"
        self.session_num: Optional[int] = None
        self.course_id: Optional[str] = None
        self.session_nums: Optional[List[int]] = None
        self.course_ids: Optional[List[str]] = None
        self.error: Optional[str] = None
        self.task: Optional[asyncio.Task] = None

    def get_status(self) -> Dict[str, Any]:
        """Mengambil status pemindaian saat ini."""
        return {
            "is_running": self.is_running,
            "progress": self.progress,
            "message": self.message,
            "session_num": self.session_num,
            "course_id": self.course_id,
            "session_nums": self.session_nums,
            "course_ids": self.course_ids,
            "error": self.error,
        }

    async def start_scan(
        self,
        session_num: Optional[int] = None,
        course_id: Optional[str] = None,
        session_nums: Optional[List[int]] = None,
        course_ids: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Memulai proses pemindaian sesi/kelas di background task."""
        if self.is_running:
            return {"status": "error", "message": "Pemindaian sedang berjalan"}

        self.is_running = True
        self.progress = 0
        self.message = "Memulai pemindaian..."
        self.session_num = session_num
        self.course_id = course_id
        self.session_nums = session_nums
        self.course_ids = course_ids
        self.error = None

        self.task = asyncio.create_task(
            self._run_scan(
                session_num=session_num,
                course_id=course_id,
                session_nums=session_nums,
                course_ids=course_ids,
                dry_run=dry_run,
            )
        )
        return {"status": "started", "message": "Pemindaian dimulai"}

    async def _run_scan(
        self,
        session_num: Optional[int] = None,
        course_id: Optional[str] = None,
        session_nums: Optional[List[int]] = None,
        course_ids: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> None:
        """Loop internal eksekusi pemindaian latar belakang."""
        try:
            self.db.log_scan(
                session_num=session_num,
                course_id=course_id,
                status="started",
                message="Memulai proses pemindaian tuton...",
            )

            if dry_run:
                self.progress = 25
                self.message = "Membuka sesi..."
                await asyncio.sleep(0.02)

                self.progress = 50
                self.message = "Mengekstrak tanggapan mahasiswa..."
                await asyncio.sleep(0.02)

                self.progress = 75
                self.message = "Mengevaluasi rubrik..."
                await asyncio.sleep(0.02)

                self.progress = 90
                self.message = "Menyimpan ke database..."
                await asyncio.sleep(0.02)

                self.progress = 100
                self.message = "Pemindaian selesai"
                self.db.log_scan(
                    session_num=session_num,
                    course_id=course_id,
                    status="success",
                    message="Pemindaian simulasi berhasil diselesaikan",
                )
                return

            if session_nums and len(session_nums) > 0:
                sessions: List[int] = [int(s) for s in session_nums]
            elif session_num is not None:
                sessions = [int(session_num)]
            else:
                sessions = [1, 2, 3, 4, 5]

            if course_ids and len(course_ids) > 0:
                c_set = {str(cid) for cid in course_ids}
                target_courses = [c for c in COURSES if str(c["id"]) in c_set]
                existing_cids = {str(c["id"]) for c in target_courses}
                for cid in course_ids:
                    if str(cid) not in existing_cids:
                        target_courses.append({
                            "id": str(cid),
                            "name": f"Kelas {cid}",
                            "code": f"MKWN4108.{cid}",
                        })
            elif course_id:
                target_courses = [c for c in COURSES if str(c["id"]) == str(course_id)]
                if not target_courses:
                    target_courses = [
                        {"id": str(course_id), "name": f"Kelas {course_id}", "code": f"MKWN4108.{course_id}"}
                    ]
            else:
                target_courses = COURSES

            total_steps = max(1, len(sessions) * len(target_courses))
            completed_steps = 0

            self.progress = 5
            self.message = "Membuka browser & memeriksa autentikasi e-learning..."

            async with async_playwright() as p:
                launch_kwargs = {
                    "headless": True,
                    "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
                }
                if CHROME_PATH and os.path.exists(CHROME_PATH):
                    launch_kwargs["executable_path"] = CHROME_PATH
                browser = await p.chromium.launch(**launch_kwargs)
                try:
                    context = await browser.new_context(
                        storage_state=SESSION_FILE if os.path.exists(SESSION_FILE) else None,
                        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    )
                    page = await context.new_page()
                    await ensure_authenticated_page(context, page)

                    for s_num in sessions:
                        is_assignment = s_num in [3, 5, 7]
                        for c in target_courses:
                            cid = str(c["id"])
                            cname = c.get("name", f"Kelas {cid}")

                            self.message = f"Membuka sesi {s_num} ({cname})..."
                            self.progress = min(95, int(10 + (completed_steps / total_steps) * 80))

                            if is_assignment:
                                self.message = f"Mengekstrak pengumpulan tugas sesi {s_num} - {cname}..."
                                raw_data = await scrape_session_assign(page, cid, s_num)
                                submissions = raw_data.get("submissions", [])

                                self.message = f"Mengevaluasi rubrik & menyimpan ke database ({len(submissions)} mahasiswa)..."
                                existing_map = {
                                    sub["student_nim"]: sub
                                    for sub in self.db.get_submissions(course_id=cid, session_num=s_num)
                                }
                                active_nims: List[str] = []
                                for s in submissions:
                                    author_name, nim = parse_post_author_and_nim(s.get("author", ""), "")
                                    student_nim = nim if nim else author_name
                                    active_nims.append(student_nim)
                                    self.db.upsert_student(nim=student_nim, name=author_name, course_id=cid)

                                    existing_sub = existing_map.get(student_nim)
                                    scraped_score = s.get("score")
                                    scraped_fb = (s.get("feedbackText") or "").strip()

                                    if scraped_score is not None:
                                        # Mahasiswa SUDAH dinilai di web e-learning UT
                                        real_score = int(scraped_score) if float(scraped_score).is_integer() else scraped_score
                                        final_fb = scraped_fb
                                        final_fb = scraped_fb
                                        if not final_fb and existing_sub and existing_sub.get("feedback"):
                                            is_dup = "keunggulan jawaban saudara tampak pada ketepatan merumuskan judul" in existing_sub["feedback"].lower()
                                            if not is_dup:
                                                final_fb = existing_sub["feedback"]
                                        if not final_fb:
                                            eval_fn = evaluate_with_gemini if s_num == 5 else evaluate_submission
                                            eval_res = eval_fn(author_name, s.get("content") or s.get("fileText", ""), s_num)
                                            final_fb = eval_res.get("feedback")

                                        self.db.upsert_submission(
                                            student_nim=student_nim,
                                            course_id=cid,
                                            session_num=s_num,
                                            post_id=s.get("postId") or s.get("userId") or s.get("id"),
                                            content=s.get("content") or s.get("fileText", ""),
                                            score=real_score,
                                            original_score=real_score,
                                            feedback=final_fb,
                                            is_copied=1,
                                            is_grade_copied=1,
                                            status="completed",
                                        )
                                    else:
                                        # Mahasiswa sudah kumpul tugas tetapi BELUM dinilai di web UT
                                        is_dup = existing_sub and "keunggulan jawaban saudara tampak pada ketepatan merumuskan judul" in (existing_sub.get("feedback") or "").lower()
                                        if existing_sub and existing_sub.get("score") is not None and existing_sub.get("feedback") and existing_sub.get("status") in ["pending", "draft"] and existing_sub["score"] >= 88 and not is_dup:
                                            draft_score = existing_sub["score"]
                                            draft_fb = existing_sub["feedback"]
                                        else:
                                            eval_fn = evaluate_with_gemini if s_num == 5 else evaluate_submission
                                            traj = self.db.get_student_trajectory(student_nim, cid)
                                            prev_scores = [t["score"] for t in traj if t["session"] < s_num and t.get("score") is not None]
                                            prev_s = prev_scores[-1] if prev_scores else None
                                            eval_res = eval_fn(author_name, s.get("content") or s.get("fileText", ""), s_num, previous_score=prev_s) if eval_fn == evaluate_with_gemini else eval_fn(author_name, s.get("content") or s.get("fileText", ""), s_num)
                                            draft_score = eval_res.get("score") or 90
                                            if prev_scores:
                                                draft_score = min(max(draft_score, prev_scores[-1] + 1), 95)
                                            draft_fb = scraped_fb or eval_res.get("feedback")

                                        self.db.upsert_submission(
                                            student_nim=student_nim,
                                            course_id=cid,
                                            session_num=s_num,
                                            post_id=s.get("postId") or s.get("userId") or s.get("id"),
                                            content=s.get("content") or s.get("fileText", ""),
                                            score=draft_score,
                                            original_score=draft_score,
                                            feedback=draft_fb,
                                            is_copied=0,
                                            is_grade_copied=0,
                                            status="pending",
                                        )

                                if active_nims and hasattr(self.db, "delete_stale_submissions"):
                                    self.db.delete_stale_submissions(cid, s_num, active_nims)
                            else:
                                self.message = f"Mengekstrak tanggapan mahasiswa forum sesi {s_num} - {cname}..."
                                raw_data = await scrape_session_forum(page, cid, s_num)
                                posts = raw_data.get("posts", [])
                                if posts:
                                    tutor_posts = [
                                        p
                                        for p in posts[1:]
                                        if "ainur" in p.get("author", "").lower()
                                        or "01007726" in p.get("author", "")
                                    ]
                                    student_raw = [p for p in posts[1:] if p not in tutor_posts]
                                else:
                                    tutor_posts = []
                                    student_raw = []

                                student_map: Dict[str, Dict[str, Any]] = {}
                                for sp in student_raw:
                                    author_name, nim = parse_post_author_and_nim(
                                        sp.get("author", ""), sp.get("content", "")
                                    )
                                    key = nim if nim else author_name.lower()
                                    raw_rating = sp.get("rating")
                                    score = (
                                        int(raw_rating)
                                        if raw_rating and str(raw_rating) not in ["-1", "-999", "0", ""]
                                        else None
                                    )
                                    if key not in student_map:
                                        student_map[key] = {
                                            "name": author_name,
                                            "nim": nim if nim else key,
                                            "postId": sp.get("postId"),
                                            "score": score,
                                            "content": sp.get("content", ""),
                                            "feedback": None,
                                        }
                                    else:
                                        if not student_map[key]["score"] and score:
                                            student_map[key]["score"] = score
                                        if len(sp.get("content", "")) > len(student_map[key]["content"]):
                                            student_map[key]["content"] = sp.get("content", "")

                                matched = match_feedbacks_to_students(list(student_map.values()), tutor_posts)
                                self.message = f"Mengevaluasi rubrik & menyimpan ke database ({len(matched)} tanggapan)..."
                                existing_map = {
                                    sub["student_nim"]: sub
                                    for sub in self.db.get_submissions(course_id=cid, session_num=s_num)
                                }
                                active_nims = []
                                for st_item in matched:
                                    nim_val = st_item["nim"]
                                    name_val = st_item["name"]
                                    active_nims.append(nim_val)
                                    self.db.upsert_student(nim=nim_val, name=name_val, course_id=cid)

                                    existing_sub = existing_map.get(nim_val)
                                    real_score = st_item.get("score")
                                    real_feedback = st_item.get("feedback")

                                    if real_score is not None:
                                        # Mahasiswa SUDAH dinilai di forum e-learning UT
                                        final_fb = real_feedback
                                        is_wrong_s6 = s_num == 6 and existing_sub and ("718 bahasa daerah" in (existing_sub.get("feedback") or "").lower() or "tugas 2" in (existing_sub.get("feedback") or "").lower())
                                        if not final_fb and existing_sub and existing_sub.get("feedback") and not is_wrong_s6:
                                            final_fb = existing_sub["feedback"]
                                        if not final_fb:
                                            eval_fn = evaluate_with_gemini if s_num in [5, 6] else evaluate_submission
                                            eval_res = eval_fn(
                                                name_val, st_item.get("content", ""), s_num
                                            )
                                            final_fb = eval_res.get("feedback")

                                        self.db.upsert_submission(
                                            student_nim=nim_val,
                                            course_id=cid,
                                            session_num=s_num,
                                            post_id=st_item.get("postId"),
                                            content=st_item.get("content"),
                                            score=real_score,
                                            original_score=real_score,
                                            feedback=final_fb,
                                            is_copied=1,
                                            is_grade_copied=1,
                                            status="completed",
                                        )
                                    else:
                                        # Mahasiswa belum dinilai di web UT (masih butuh tindakan)
                                        is_wrong_s6 = s_num == 6 and existing_sub and ("718 bahasa daerah" in (existing_sub.get("feedback") or "").lower() or "tugas 2" in (existing_sub.get("feedback") or "").lower())
                                        if (
                                            existing_sub
                                            and existing_sub.get("score") is not None
                                            and existing_sub.get("feedback")
                                            and existing_sub.get("status") in ["pending", "draft"]
                                            and existing_sub.get("content") == st_item.get("content")
                                            and not is_wrong_s6
                                        ):
                                            draft_score = existing_sub["score"]
                                            draft_fb = existing_sub["feedback"]
                                        else:
                                            eval_fn = evaluate_with_gemini if s_num in [5, 6] else evaluate_submission
                                            traj = self.db.get_student_trajectory(nim_val, cid)
                                            prev_scores = [t["score"] for t in traj if t["session"] < s_num and t.get("score") is not None]
                                            prev_s = prev_scores[-1] if prev_scores else None
                                            if eval_fn == evaluate_with_gemini:
                                                eval_res = eval_fn(name_val, st_item.get("content", ""), s_num, previous_score=prev_s)
                                            else:
                                                eval_res = eval_fn(name_val, st_item.get("content", ""), s_num)
                                            draft_score = eval_res.get("score")
                                            draft_fb = real_feedback or eval_res.get("feedback")

                                        self.db.upsert_submission(
                                            student_nim=nim_val,
                                            course_id=cid,
                                            session_num=s_num,
                                            post_id=st_item.get("postId"),
                                            content=st_item.get("content"),
                                            score=draft_score,
                                            feedback=draft_fb,
                                            is_copied=0,
                                            is_grade_copied=0,
                                            status="pending",
                                        )

                                if active_nims and hasattr(self.db, "delete_stale_submissions"):
                                    self.db.delete_stale_submissions(cid, s_num, active_nims)

                            completed_steps += 1
                finally:
                    await browser.close()

            self.progress = 100
            self.message = "Pemindaian selesai"
            self.db.log_scan(
                session_num=session_num,
                course_id=course_id,
                status="success",
                message="Pemindaian e-learning berhasil diselesaikan",
            )
        except Exception as exc:
            self.error = str(exc)
            self.message = f"Gagal memindai: {exc}"
            self.db.log_scan(
                session_num=session_num,
                course_id=course_id,
                status="error",
                message=f"Gagal memindai: {exc}",
            )
        finally:
            self.is_running = False
            if not self.error:
                self.progress = 100


# Singleton tingkat modul
scanner_service = ScannerService()
