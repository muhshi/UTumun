"""
Modul Pengiriman Nilai & Feedback ke E-learning UT (elearning.ut.ac.id)
Mendukung pengiriman nilai (grade) dan komentar feedback per mahasiswa dengan proteksi single-flight (idempotency lock)
untuk mencegah pengiriman ganda.
"""

import asyncio
import logging
import os
import re
from typing import Dict, Any, Optional

from playwright.async_api import async_playwright

from tuton.auth import ensure_authenticated_page
from tuton.config import (
    CHROME_PATH,
    SESSION_FILE,
    get_assign_cmid,
    get_course_info,
    get_forum_cmid,
    DB_ENGINE,
)
from tuton.db import get_db
from tuton.scraper import build_assignment_grading_url, build_flat_topic_url

logger = logging.getLogger("tuton.submitter")

# Kunci concurrency untuk proteksi single-flight (mencegah pengiriman ganda secara paralel)
_in_flight_submissions = set()
_lock = asyncio.Lock()

async def submit_single_grade_to_ut(
    course_id: str,
    session_num: int,
    student_nim: str,
    score: int,
    feedback: str,
    student_name: Optional[str] = None,
    userid: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mengirimkan nilai dan draf feedback untuk SATU mahasiswa secara langsung ke web e-learning UT.
    Dilengkapi penguncian (lock) agar tombol tidak dapat ditekan berulang kali atau menghasilkan duplikasi request.
    """
    lock_key = f"{course_id}:{session_num}:{student_nim}"

    async with _lock:
        if lock_key in _in_flight_submissions:
            return {
                "success": False,
                "message": "Pengiriman ke UT untuk mahasiswa ini sedang diproses. Mohon tunggu sejenak."
            }
        _in_flight_submissions.add(lock_key)

    try:
        db = get_db()
        course_info = get_course_info(course_id)
        if not course_info:
            return {"success": False, "message": f"Kelas {course_id} tidak ditemukan dalam konfigurasi"}

        # Periksa apakah userid Moodle tersimpan di tabel submissions (kolom post_id)
        if not userid:
            existing = db.get_submission(student_nim, course_id, session_num)
            if existing and existing.get("post_id") and existing["post_id"].isdigit():
                userid = existing["post_id"]

        is_assignment = session_num in [3, 5, 7]

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

                if is_assignment:
                    cmid = get_assign_cmid(course_id, session_num)
                    if not cmid:
                        return {"success": False, "message": f"CMID tugas tidak ditemukan untuk kelas {course_id} sesi {session_num}"}

                    # Jika userid belum diketahui, cari di tabel grading tugas terlebih dahulu
                    if not userid:
                        grading_url = build_assignment_grading_url(cmid, perpage=100)
                        await page.goto(grading_url, wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(1500)

                        # Cari baris mahasiswa berdasarkan NIM atau Nama
                        found_userid = await page.evaluate('''(searchKey) => {
                            const trs = Array.from(document.querySelectorAll("table.generaltable tbody tr")).filter(
                                tr => tr.id && tr.id.startsWith("mod_assign_grading")
                            );
                            for (const tr of trs) {
                                const text = tr.innerText.toLowerCase();
                                if (text.includes(searchKey.toLowerCase())) {
                                    const userLink = tr.querySelector("td.cell.c2 a, td.fullname a");
                                    if (userLink && userLink.href) {
                                        const m = userLink.href.match(/[?&]id=(\\d+)/);
                                        if (m) return m[1];
                                    }
                                    const q = tr.querySelector("input.quickgrade");
                                    if (q && q.name) {
                                        const m = q.name.match(/quickgrade_(\\d+)/);
                                        if (m) return m[1];
                                    }
                                }
                            }
                            return null;
                        }''', student_nim or (student_name or ""))

                        if found_userid:
                            userid = found_userid

                    if not userid:
                        return {
                            "success": False,
                            "message": f"Tidak dapat menemukan profil pengumpulan mahasiswa {student_nim} di tabel tugas UT."
                        }

                    # Buka halaman Grader tunggal Moodle untuk mahasiswa tersebut
                    grader_url = f"https://elearning.ut.ac.id/mod/assign/view.php?id={cmid}&action=grader&userid={userid}"
                    logger.info(f"Membuka Moodle Grader: {grader_url}")
                    await page.goto(grader_url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(2000)

                    # 1. Isi input nilai (Grade)
                    grade_locator = page.locator("input#id_grade, input[name='grade']")
                    if await grade_locator.count() == 0:
                        return {"success": False, "message": "Kolom input nilai tidak ditemukan pada halaman grader UT"}
                    await grade_locator.fill(str(score))

                    # 2. Isi komentar feedback
                    fb_editable = page.locator("#id_assignfeedbackcomments_editoreditable")
                    if await fb_editable.count() > 0 and await fb_editable.is_visible():
                        await fb_editable.fill(feedback)
                    else:
                        fb_textarea = page.locator("textarea#id_assignfeedbackcomments_editor, textarea[name='assignfeedbackcomments_editor[text]']")
                        if await fb_textarea.count() > 0:
                            await fb_textarea.fill(feedback)

                    # 3. Klik tombol Simpan Perubahan (Save changes)
                    save_btn = page.locator("button[name='savechanges'], input[name='savechanges'], button:has-text('Save changes')").first
                    if await save_btn.count() == 0:
                        return {"success": False, "message": "Tombol simpan nilai tidak ditemukan pada halaman grader UT"}

                    await save_btn.click()
                    await page.wait_for_timeout(2500)

                    logger.info(f"Berhasil menyimpan nilai {score} untuk NIM {student_nim} pada Tugas Sesi {session_num}")

                else:
                    # Sesi Diskusi Forum (Sesi 1, 2, 4, 6, 8)
                    cmid = get_forum_cmid(course_id, session_num)
                    if not cmid:
                        return {"success": False, "message": f"CMID forum diskusi tidak ditemukan untuk kelas {course_id} sesi {session_num}"}

                    forum_url = f"https://elearning.ut.ac.id/mod/forum/view.php?id={cmid}"
                    await page.goto(forum_url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(1500)

                    # Dapatkan link topik diskusi
                    topic_href = await page.evaluate('''() => {
                        const a = document.querySelector(".discussionname a, .topic a");
                        return a ? a.href : null;
                    }''')
                    if not topic_href:
                        return {"success": False, "message": "Topik forum diskusi tidak ditemukan di halaman kelas UT"}

                    discuss_url = build_flat_topic_url(topic_href)
                    await page.goto(discuss_url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(1500)

                    # Cari postingan mahasiswa dan atur nilai pada dropdown rating
                    rated = await page.evaluate('''({nim, targetScore}) => {
                        const articles = Array.from(document.querySelectorAll("article.forum-post-container, div.forumpost"));
                        for (const art of articles) {
                            const text = art.innerText;
                            if (text.includes(nim)) {
                                const rateSelect = art.querySelector("select[name*='rating']");
                                if (rateSelect) {
                                    rateSelect.value = String(targetScore);
                                    rateSelect.dispatchEvent(new Event('change', { bubbles: true }));
                                    return true;
                                }
                            }
                        }
                        return false;
                    }''', {"nim": student_nim, "targetScore": score})

                    if not rated:
                        return {
                            "success": False,
                            "message": f"Tidak dapat menemukan opsi rating penilaian untuk postingan mahasiswa {student_nim}"
                        }
                    await page.wait_for_timeout(2000)

                # Update database lokal SQLite & MySQL server
                db.update_submission(
                    student_nim=student_nim,
                    course_id=course_id,
                    session_num=session_num,
                    score=score,
                    feedback=feedback,
                    is_copied=1,
                    is_grade_copied=1,
                    status="completed"
                )

                # Jika MySQL aktif, update juga di MySQL
                if DB_ENGINE == "mysql":
                    try:
                        from tuton.mysql_db import MySQLDatabase
                        m_db = MySQLDatabase()
                        m_db.update_submission(
                            student_nim=student_nim,
                            course_id=course_id,
                            session_num=session_num,
                            score=score,
                            feedback=feedback,
                            is_copied=1,
                            is_grade_copied=1,
                            status="completed"
                        )
                    except Exception as me:
                        logger.warning(f"Gagal memperbarui status ke MySQL: {me}")

                return {
                    "success": True,
                    "message": f"Nilai {score} dan draf feedback untuk {student_name or student_nim} berhasil dikirim ke e-learning UT!"
                }

            finally:
                await browser.close()

    except Exception as e:
        logger.error(f"Gagal mengirim nilai ke UT untuk {student_nim}: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Terjadi kesalahan saat menghubungkan ke e-learning UT: {str(e)}"
        }

    finally:
        async with _lock:
            _in_flight_submissions.discard(lock_key)
