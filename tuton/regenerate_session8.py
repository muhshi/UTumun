"""
Skrip Regenerasi Evaluasi Sesi 8 (Forum Diskusi 8: Rancangan Artikel Ilmiah Mandiri)
Memperbarui seluruh draf penilaian dan feedback mahasiswa Sesi 8 agar sesuai dengan penemuan artikel ilmiah mereka
serta menyertakan penutup terima kasih partisipasi Sesi 1-8 dan permohonan maaf dari Ibu Tutor.
"""

import sys
import logging
from tuton.db import get_db
from tuton.evaluator import evaluate_submission, clean_title_name

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("regenerate_session8")

def regenerate_session8_submissions():
    db = get_db()
    logger.info("Memulai regenerasi feedback Sesi 8 dari database...")

    # Ambil seluruh submission sesi 8
    submissions = db.get_submissions(session_num=8)
    if not submissions:
        logger.warning("Tidak ditemukan submission untuk Sesi 8 di database.")
        return

    logger.info(f"Ditemukan {len(submissions)} submission Sesi 8. Memulai pembaruan...")

    students = {s["nim"]: s["name"] for s in db.get_students()}
    count = 0

    for sub in submissions:
        nim = sub["student_nim"]
        cid = sub["course_id"]
        content = sub.get("content") or ""
        st_name = students.get(nim) or nim

        clean_name = clean_title_name(st_name)
        eval_res = evaluate_submission(clean_name, content, session_num=8)

        new_score = eval_res["score"]
        new_feedback = eval_res["feedback"]

        # Pertahankan original_score jika mahasiswa sudah memiliki nilai di UT
        orig_score = sub.get("original_score") or new_score

        # Hanya perbarui jika belum berstatus selesai di web UT atau jika feedbacknya masih versi lama
        status = sub.get("status", "pending")
        if status != "completed":
            status = "pending"

        db.upsert_submission(
            student_nim=nim,
            course_id=cid,
            session_num=8,
            post_id=sub.get("post_id"),
            content=content,
            score=new_score,
            original_score=orig_score,
            feedback=new_feedback,
            is_copied=0,
            is_grade_copied=0,
            status=status
        )
        count += 1
        logger.info(f"[{count}/{len(submissions)}] Berhasil memperbarui {clean_name} ({nim}) Kelas {cid} -> Skor: {new_score}")

    logger.info(f"=== SELESAI: Berhasil meregenerasi {count} draf feedback Sesi 8! ===")

if __name__ == "__main__":
    regenerate_session8_submissions()
