"""
Skrip Regenerasi Evaluasi Sesi 5 (Tugas 2) Berbasis Gemini 3.8 Flash
Menggunakan scrape_session_assign untuk mengekstrak pengumpulan dan berkas tugas,
kemudian mengevaluasi menggunakan Gemini 3.8 Flash berdasarkan Rubrik Resmi Penskoran Tugas 2 (MKWN4108).
"""

import asyncio
import logging
import os
from typing import Dict, Any, List

from playwright.async_api import async_playwright

from tuton.auth import ensure_authenticated_page
from tuton.config import (
    CHROME_PATH,
    COURSES,
    SESSION_FILE,
    get_assign_cmid,
    DB_ENGINE,
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
)
from tuton.db import get_db
from tuton.gemini_evaluator import evaluate_with_gemini
from tuton.scraper import scrape_session_assign, parse_post_author_and_nim

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("regenerate_session5")

DUPLICATE_PHRASE = "keunggulan jawaban saudara tampak pada ketepatan merumuskan judul"

async def regenerate_all_session5(dry_run: bool = False):
    db = get_db()
    session_num = 5

    logger.info("=== MEMULAI REGENERASI FEEDBACK SPESIFIK SESI 5 (TUGAS 2) ===")

    launch_kwargs = {
        "headless": True,
        "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    }
    if CHROME_PATH and os.path.exists(CHROME_PATH):
        launch_kwargs["executable_path"] = CHROME_PATH

    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_kwargs)
        try:
            context = await browser.new_context(
                storage_state=SESSION_FILE if os.path.exists(SESSION_FILE) else None,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            )
            page = await context.new_page()
            await ensure_authenticated_page(context, page)

            total_regenerated = 0

            for c in COURSES:
                cid = c["id"]
                cname = c["name"]
                cmid = get_assign_cmid(cid, session_num)
                if not cmid:
                    continue

                logger.info(f"--- Memproses Kelas {cname} (ID: {cid}, CMID: {cmid}) ---")
                data = await scrape_session_assign(page, cid, session_num)
                submissions = data.get("submissions", [])

                logger.info(f"Ditemukan {len(submissions)} mahasiswa pengumpul tugas pada {cname}")

                for s in submissions:
                    name_raw = s.get("author", "")
                    if not name_raw:
                        continue

                    author_name, student_nim = parse_post_author_and_nim(name_raw, "")
                    if not student_nim:
                        student_nim = name_raw

                    db.upsert_student(nim=student_nim, name=author_name, course_id=cid)

                    # Cek existing status
                    existing = db.get_submission(student_nim, cid, session_num)
                    is_dup = False
                    if existing and existing.get("feedback"):
                        if DUPLICATE_PHRASE in existing["feedback"].lower():
                            is_dup = True

                    content = s.get("content") or s.get("fileText", "")
                    scraped_score = s.get("score")
                    scraped_fb = (s.get("feedbackText") or "").strip()

                    # Jika tugas sudah dinilai resmi di UT e-learning dan memiliki feedback bukan duplikat
                    if scraped_score is not None and not is_dup:
                        real_score = int(scraped_score) if float(scraped_score).is_integer() else scraped_score
                        final_fb = scraped_fb or (existing["feedback"] if existing and existing.get("feedback") else "")
                        if not final_fb:
                            eval_res = evaluate_with_gemini(author_name, content, session_num)
                            final_fb = eval_res["feedback"]

                        db.upsert_submission(
                            student_nim=student_nim,
                            course_id=cid,
                            session_num=session_num,
                            post_id=s.get("postId") or s.get("userId"),
                            content=content,
                            score=real_score,
                            original_score=real_score,
                            feedback=final_fb,
                            is_copied=1,
                            is_grade_copied=1,
                            status="completed"
                        )
                        continue

                    # Jika belum dinilai resmi di UT, atau feedback-nya adalah duplikat template
                    logger.info(f"  [*] Mengevaluasi dengan Gemini untuk {author_name} ({student_nim})...")
                    traj = db.get_student_trajectory(student_nim, cid)
                    prev_scores = [t["score"] for t in traj if t["session"] < session_num and t.get("score") is not None]
                    prev_s = prev_scores[-1] if prev_scores else None

                    eval_res = evaluate_with_gemini(
                        student_name=author_name,
                        submission_text=content,
                        session_num=session_num,
                        previous_score=prev_s
                    )

                    new_score = eval_res["score"]
                    new_fb = eval_res["feedback"]

                    if not dry_run:
                        # 1. Simpan ke SQLite lokal
                        db.upsert_submission(
                            student_nim=student_nim,
                            course_id=cid,
                            session_num=session_num,
                            post_id=s.get("postId") or s.get("userId"),
                            content=content,
                            score=new_score,
                            original_score=new_score,
                            feedback=new_fb,
                            is_copied=0,
                            is_grade_copied=0,
                            status="pending"
                        )

                        # 2. Simpan ke MySQL Server
                        if DB_ENGINE == "mysql":
                            try:
                                import pymysql
                                conn = pymysql.connect(
                                    host=MYSQL_HOST,
                                    port=MYSQL_PORT,
                                    user=MYSQL_USER,
                                    password=MYSQL_PASSWORD,
                                    database=MYSQL_DATABASE,
                                )
                                with conn.cursor() as cur:
                                    cur.execute("""
                                        INSERT INTO submissions 
                                        (student_nim, course_id, session_num, post_id, content, score, original_score, feedback, is_copied, is_grade_copied, status)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 0, 'pending')
                                        ON DUPLICATE KEY UPDATE
                                            post_id = VALUES(post_id),
                                            content = VALUES(content),
                                            score = VALUES(score),
                                            original_score = VALUES(original_score),
                                            feedback = VALUES(feedback),
                                            is_copied = 0,
                                            is_grade_copied = 0,
                                            status = 'pending'
                                    """, (student_nim, cid, session_num, s.get("postId") or s.get("userId"), content, new_score, new_score, new_fb))
                                    conn.commit()
                                conn.close()
                            except Exception as me:
                                logger.warning(f"Gagal simpan ke MySQL: {me}")

                        total_regenerated += 1
                        logger.info(f"  [✓] Sukses dievaluasi: {author_name} -> Nilai {new_score}, status=pending")

            logger.info(f"=== SELESAI: Berhasil meregenerasi {total_regenerated} pengumpulan Sesi 5 ===")

        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(regenerate_all_session5())
