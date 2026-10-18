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
        if is_assignment:
            cmid = get_assign_cmid(course_id, session_num)
            if not cmid:
                return {"success": False, "message": f"CMID tugas tidak ditemukan untuk kelas {course_id} sesi {session_num}"}
        else:
            cmid = get_forum_cmid(course_id, session_num)
            if not cmid:
                return {"success": False, "message": f"CMID forum diskusi tidak ditemukan untuk kelas {course_id} sesi {session_num}"}

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

                    # 2. Isi komentar feedback (Universal untuk Moodle Atto, TinyMCE, dan Textarea)
                    feedback_saved = await page.evaluate('''({rawFeedback}) => {
                        // Format ke paragraf HTML yang rapi untuk editor Moodle
                        const paragraphs = rawFeedback.split(/\\n\\s*\\n/).map(p => p.trim()).filter(Boolean);
                        const htmlFeedback = paragraphs.map(p => `<p>${p.replace(/\\n/g, "<br>")}</p>`).join("");
                        
                        let applied = false;

                        // 1. Coba Atto Editor (contenteditable div)
                        const attoDiv = document.querySelector("#id_assignfeedbackcomments_editoreditable, div[id*='assignfeedbackcomments'][contenteditable='true']");
                        if (attoDiv) {
                            attoDiv.innerHTML = htmlFeedback;
                            attoDiv.dispatchEvent(new Event("input", { bubbles: true }));
                            attoDiv.dispatchEvent(new Event("change", { bubbles: true }));
                            applied = true;
                        }

                        // 2. Coba TinyMCE iframe
                        const tinyIframe = document.querySelector("iframe#id_assignfeedbackcomments_editor_ifr, iframe[id*='assignfeedbackcomments']");
                        if (tinyIframe && tinyIframe.contentDocument && tinyIframe.contentDocument.body) {
                            tinyIframe.contentDocument.body.innerHTML = htmlFeedback;
                            tinyIframe.contentDocument.body.dispatchEvent(new Event("input", { bubbles: true }));
                            applied = true;
                        }

                        // 3. Selalu perbarui juga hidden textarea Moodle agar form submission valid
                        const textareas = Array.from(document.querySelectorAll("textarea")).filter(
                            t => (t.id && t.id.includes("assignfeedbackcomments")) || (t.name && t.name.includes("assignfeedbackcomments"))
                        );
                        for (const ta of textareas) {
                            ta.value = htmlFeedback;
                            ta.dispatchEvent(new Event("input", { bubbles: true }));
                            ta.dispatchEvent(new Event("change", { bubbles: true }));
                            applied = true;
                        }

                        // 4. Sinkronisasi via API TinyMCE jika tersedia di window
                        if (window.tinyMCE) {
                            try {
                                for (const editor of Object.values(window.tinyMCE.editors || {})) {
                                    if (editor.id && editor.id.includes("assignfeedbackcomments")) {
                                        editor.setContent(htmlFeedback);
                                        applied = true;
                                    }
                                }
                            } catch(e) {}
                        }

                        return applied;
                    }''', {"rawFeedback": feedback})

                    if not feedback_saved:
                        logger.warning(f"Editor feedback Moodle tidak terdeteksi via selector standar untuk {student_nim}")

                    # 3. Klik tombol Simpan Perubahan (Save changes)
                    save_clicked = await page.evaluate('''() => {
                        const btn = document.querySelector(
                            "button[name='savechanges'], input[name='savechanges'], button.btn-primary[type='submit'], input.btn-primary[type='submit']"
                        ) || Array.from(document.querySelectorAll("button, input[type='submit'], input[type='button']")).find(
                            el => (el.value || el.innerText || "").toLowerCase().includes("save changes") || (el.value || el.innerText || "").toLowerCase().includes("simpan perubahan")
                        );

                        if (btn) {
                            btn.scrollIntoView({ behavior: 'instant', block: 'center' });
                            btn.click();
                            return true;
                        }
                        return false;
                    }''')

                    if not save_clicked:
                        save_btn = page.locator("button[name='savechanges'], input[name='savechanges'], button:has-text('Save changes'), button:has-text('Simpan perubahan')").first
                        if await save_btn.count() > 0:
                            await save_btn.click()
                        else:
                            return {"success": False, "message": "Tombol simpan nilai tidak ditemukan pada halaman grader UT"}

                    await page.wait_for_timeout(3000)

                    logger.info(f"Berhasil menyimpan nilai {score} untuk NIM {student_nim} pada Tugas Sesi {session_num}")

                else:
                    # Sesi Diskusi Forum (Sesi 1, 2, 4, 6, 8)
                    forum_url = f"https://elearning.ut.ac.id/mod/forum/view.php?id={cmid}"
                    await page.goto(forum_url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(1500)

                    # Dapatkan link topik diskusi pertama
                    topic_href = await page.evaluate('''() => {
                        const a = document.querySelector(".discussionname a, .topic a, a[href*='/mod/forum/discuss.php?d=']");
                        return a ? a.href : null;
                    }''')
                    if not topic_href:
                        return {"success": False, "message": "Topik forum diskusi tidak ditemukan di halaman kelas UT"}

                    discuss_url = build_flat_topic_url(topic_href)
                    await page.goto(discuss_url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(1500)

                    # Cari postingan mahasiswa, atur rating nilai, dan periksa balasan tutor
                    forum_action = await page.evaluate('''({nim, studentName, targetScore}) => {
                        const articles = Array.from(document.querySelectorAll("article.forum-post-container, div.forumpost"));
                        let studentPost = null;
                        let postId = null;
                        let rated = false;
                        let replyHref = null;

                        for (const art of articles) {
                            const text = art.innerText.toLowerCase();
                            const header = art.querySelector("header") ? art.querySelector("header").innerText.toLowerCase() : "";
                            const isMatch = (nim && (text.includes(nim.toLowerCase()) || header.includes(nim.toLowerCase()))) ||
                                            (studentName && (header.includes(studentName.toLowerCase()) || text.includes(studentName.toLowerCase())));
                            const isTutor = header.includes("ainur") || header.includes("01007726");

                            if (isMatch && !isTutor) {
                                studentPost = art;
                                postId = art.getAttribute("data-post-id");
                                break;
                            }
                        }

                        if (!studentPost) {
                            return { success: false, message: `Postingan forum untuk mahasiswa ${nim || studentName} tidak ditemukan` };
                        }

                        // Rating nilai pada postingan mahasiswa
                        const rateSelect = studentPost.querySelector(`select#menurating${postId}`) || studentPost.querySelector("select[name*='rating']");
                        if (rateSelect) {
                            rateSelect.value = String(targetScore);
                            rateSelect.dispatchEvent(new Event('change', { bubbles: true }));
                            rated = true;
                        }

                        // Cek apakah tutor sudah pernah membalas postingan ini untuk mencegah spam
                        const tutorPosts = articles.filter(art => {
                            const header = art.querySelector("header") ? art.querySelector("header").innerText.toLowerCase() : "";
                            const text = art.innerText.toLowerCase();
                            return header.includes("ainur") || header.includes("01007726") || text.includes("01007726");
                        });

                        const alreadyReplied = tutorPosts.some(art => {
                            const text = art.innerText.toLowerCase();
                            return (nim && text.includes(nim.toLowerCase())) || (studentName && text.includes(studentName.toLowerCase()));
                        });

                        const replyLink = studentPost.querySelector("a[href*='post.php?reply='], a[data-action='reply']");
                        if (replyLink) {
                            replyHref = replyLink.href;
                        }

                        return {
                            success: true,
                            postId: postId,
                            rated: rated,
                            alreadyReplied: alreadyReplied,
                            replyHref: replyHref
                        };
                    }''', {"nim": student_nim, "studentName": student_name, "targetScore": score})

                    if not isinstance(forum_action, dict) or forum_action.get("success") is False:
                        return {
                            "success": False,
                            "message": (forum_action.get("message") if isinstance(forum_action, dict) else None) or f"Gagal memproses postingan forum untuk mahasiswa {student_nim}"
                        }

                    if not forum_action.get("rated"):
                        logger.warning(f"Opsi dropdown rating tidak ditemukan untuk NIM {student_nim}")

                    # Tunggu hingga permintaan AJAX rating Moodle tersimpan
                    await page.wait_for_timeout(2500)

                    # Jika belum dibalas dan tautan reply tersedia, kirim draf feedback sebagai balasan forum
                    already_replied = forum_action.get("alreadyReplied") or forum_action.get("already_replied")
                    reply_url = forum_action.get("replyHref") or forum_action.get("reply_href")

                    if already_replied:
                        logger.info(f"Tutor sudah pernah membalas postingan mahasiswa {student_nim}. Melewati pengiriman balasan forum.")
                    elif reply_url and feedback:
                        logger.info(f"Membuka halaman balasan forum untuk {student_nim}: {reply_url}")
                        await page.goto(reply_url, wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(1500)

                        # Injeksi draf feedback ke editor Moodle (Atto / TinyMCE / Textarea)
                        feedback_injected = await page.evaluate('''({rawFeedback}) => {
                            let applied = false;
                            const paragraphs = rawFeedback.split("\\n\\n").filter(p => p.trim());
                            const htmlFeedback = paragraphs.map(p => `<p>${p.trim()}</p>`).join("");

                            // 1. Editor Atto Moodle
                            const attoEditors = document.querySelectorAll(
                                "div.editor_atto_content, div#id_message_editor[contenteditable='true'], div[role='textbox']"
                            );
                            for (const ed of attoEditors) {
                                ed.innerHTML = htmlFeedback;
                                ed.dispatchEvent(new Event("input", { bubbles: true }));
                                ed.dispatchEvent(new Event("change", { bubbles: true }));
                                applied = true;
                            }

                            // 2. Editor TinyMCE via iframe
                            const tinyIframes = document.querySelectorAll("div.tox-edit-area__iframe, iframe[id*='message']");
                            for (const ifr of tinyIframes) {
                                try {
                                    const doc = ifr.contentDocument || ifr.contentWindow.document;
                                    if (doc && doc.body) {
                                        doc.body.innerHTML = htmlFeedback;
                                        applied = true;
                                    }
                                } catch(e) {}
                            }

                            // 3. Fallback ke Textarea Moodle
                            const textareas = document.querySelectorAll(
                                "textarea#id_message, textarea[name='message[text]'], textarea[name='message']"
                            );
                            for (const ta of textareas) {
                                ta.value = htmlFeedback;
                                ta.dispatchEvent(new Event("input", { bubbles: true }));
                                ta.dispatchEvent(new Event("change", { bubbles: true }));
                                applied = true;
                            }

                            // 4. Sinkronisasi via API TinyMCE jika tersedia
                            if (window.tinyMCE) {
                                try {
                                    for (const editor of Object.values(window.tinyMCE.editors || {})) {
                                        if (editor.id && editor.id.includes("message")) {
                                            editor.setContent(htmlFeedback);
                                            applied = true;
                                        }
                                    }
                                } catch(e) {}
                            }

                            return applied;
                        }''', {"rawFeedback": feedback})

                        if not feedback_injected:
                            logger.warning(f"Editor balasan forum Moodle tidak terdeteksi via selector standar untuk {student_nim}")

                        # Klik tombol Kirim ke forum (Post to forum)
                        post_clicked = await page.evaluate('''() => {
                            const btn = document.querySelector(
                                "input#id_submitbutton, button#id_submitbutton, input[name='submitbutton'], button[type='submit'][name='submitbutton']"
                            ) || Array.from(document.querySelectorAll("input[type='submit'], button[type='submit']")).find(
                                el => (el.value || el.innerText || "").toLowerCase().includes("forum") ||
                                      (el.value || el.innerText || "").toLowerCase().includes("kirim") ||
                                      (el.value || el.innerText || "").toLowerCase().includes("post")
                            );
                            if (btn) {
                                btn.click();
                                return true;
                            }
                            return false;
                        }''')

                        if not post_clicked:
                            post_btn = page.locator("input#id_submitbutton, button#id_submitbutton, button:has-text('Kirim ke forum'), button:has-text('Post to forum')").first
                            if await post_btn.count() > 0:
                                await post_btn.click()

                        await page.wait_for_timeout(3000)
                        logger.info(f"Balasan feedback forum berhasil dikirim untuk {student_nim}")

                # Update database aktif (SQLite atau MySQL via get_db)
                db.upsert_submission(
                    student_nim=student_nim,
                    course_id=course_id,
                    session_num=session_num,
                    score=score,
                    feedback=feedback,
                    is_copied=1,
                    is_grade_copied=1,
                    status="completed"
                )

                # Jika MySQL aktif namun instance db di atas adalah SQLite, pastikan juga tersimpan ke MySQL
                if DB_ENGINE == "mysql" and type(db).__name__ != "MySQLDatabase":
                    try:
                        from tuton.mysql_db import MySQLDatabase
                        m_db = MySQLDatabase()
                        m_db.upsert_submission(
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
