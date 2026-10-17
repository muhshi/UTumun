import html
import re
from typing import Dict, Any, List, Tuple, Optional, Union
from playwright.async_api import Page
from tuton.config import get_course_info, get_forum_cmid, get_assign_cmid, COURSES
from tuton.matcher import clean_student_name
from tuton.file_extractor import extract_text_from_bytes

def build_flat_topic_url(raw_topic_url: str) -> str:
    r"""Mengekstrak d=(\d+) dan membangun URL flat mode bersih tanpa fragment hash."""
    d_match = re.search(r'[?&]d=(\d+)', raw_topic_url)
    if not d_match:
        raise ValueError(f"Tidak dapat mengekstrak ID diskusi dari URL: {raw_topic_url}")
    return f"https://elearning.ut.ac.id/mod/forum/discuss.php?d={d_match.group(1)}&mode=1"

def build_assignment_grading_url(cmid: str, perpage: int = 100) -> str:
    """Membangun URL grading tugas dengan perpage=100 dan reset filter inisial nama."""
    return (
        f"https://elearning.ut.ac.id/mod/assign/view.php?"
        f"id={cmid}&action=grading&perpage={perpage}&filter=&tifirst=&tilast=&page=0"
    )

def clean_html_feedback(raw_html: str) -> str:
    """Membersihkan tag HTML dari komentar feedback Moodle menjadi teks 2 paragraf yang rapi."""
    if not raw_html:
        return ""
    text = raw_html.strip()
    if text.lower() == "feedback comments":
        return ""
    text = re.sub(r"</(div|p|li|h[1-6])>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    paragraphs = []
    for line in text.splitlines():
        cleaned_line = " ".join(line.split())
        if cleaned_line:
            paragraphs.append(cleaned_line)
    return "\n\n".join(paragraphs)

def parse_assignment_grade_and_status(grade_text: str) -> Tuple[Optional[Union[int, float]], str]:
    """Mengekstrak skor numerik dan status ('completed'/'pending') dari teks nilai."""
    if not grade_text:
        return None, "pending"
    # Bersihkan bagian penyebut '/ 100.00' dan label 'Grade User grade'
    cleaned = grade_text.split("/")[0]
    cleaned = re.sub(r"(?i)\b(grade|user\s+grade|nilai)\b", "", cleaned).strip()
    if not cleaned or cleaned == "-":
        return None, "pending"
    match = re.search(r'\d+(?:[.,]\d+)?', cleaned)
    if not match:
        return None, "pending"
    val = float(match.group(0).replace(',', '.'))
    if val < 0:
        return None, "pending"
    score = int(val) if val.is_integer() else val
    return score, "completed"

def parse_post_author_and_nim(author_raw: str, content: str) -> Tuple[str, str]:
    """Mengekstrak nama bersih dan NIM 9 digit dari header/konten."""
    clean_name = clean_student_name(author_raw)
    nim_match = re.search(r"\b\d{9}\b", author_raw) or re.search(r"\b\d{9}\b", content)
    nim = nim_match.group(0) if nim_match else ""
    return clean_name, nim

async def scrape_session_forum(page: Page, course_id: str, session_num: int) -> Dict[str, Any]:
    """Menarik seluruh postingan forum diskusi suatu sesi untuk kelas tertentu."""
    cmid = get_forum_cmid(course_id, session_num)
    course_info = get_course_info(course_id)
    if not cmid or not course_info:
        raise ValueError(f"Konfigurasi tidak ditemukan untuk course {course_id} sesi {session_num}")

    forum_url = f"https://elearning.ut.ac.id/mod/forum/view.php?id={cmid}"
    print(f"[SCRAPER] Membuka {course_info['name']} Sesi {session_num} ({forum_url})...")

    await page.goto(forum_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(2500)

    # Ambil tautan topik diskusi pertama
    topic_url = await page.evaluate('''() => {
        const a = document.querySelector('a[href*="/mod/forum/discuss.php?d="]');
        return a ? a.href : null;
    }''')

    if not topic_url:
        print(f"[SCRAPER] Peringatan: Tidak ditemukan topik diskusi pada {forum_url}")
        return {"course": course_info, "session": session_num, "posts": []}

    flat_url = build_flat_topic_url(topic_url)
    print(f"[SCRAPER] Membuka topik dalam flat mode: {flat_url}...")
    await page.goto(flat_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(3500)

    posts = await page.evaluate('''() => {
        const articles = document.querySelectorAll('article.forum-post-container');
        const res = [];
        articles.forEach(art => {
            const postId = art.getAttribute('data-post-id');
            const header = art.querySelector('header');
            const userLink = header ? header.querySelector('a[href*="/user/view.php"]') : null;
            const author = userLink ? userLink.innerText.trim() : (header ? header.innerText.trim().split('\\n')[0] : 'Unknown');
            
            const timeEl = art.querySelector('time');
            const time = timeEl ? timeEl.innerText.trim() : '';

            const contentEl = art.querySelector('.post-content-container');
            const content = contentEl ? contentEl.innerText.trim() : '';

            const rateSelect = art.querySelector(`select#menurating${postId}`) || art.querySelector('select[name="rating"]');
            let rating = null;
            if (rateSelect) {
                const sel = rateSelect.querySelector('option[selected]');
                rating = sel ? sel.value : rateSelect.value;
            }

            res.push({
                postId: postId,
                author: author,
                time: time,
                rating: rating,
                content: content
            });
        });
        return res;
    }''')

    print(f"[SCRAPER] Berhasil mengekstrak {len(posts)} postingan dari {course_info['name']} Sesi {session_num}")
    return {"course": course_info, "session": session_num, "posts": posts}

async def scrape_session_assign(page: Page, course_id: str, session_num: int) -> Dict[str, Any]:
    """Menarik seluruh pengumpulan tugas (assignment) suatu sesi untuk kelas tertentu."""
    cmid = get_assign_cmid(course_id, session_num)
    course_info = get_course_info(course_id)
    if not cmid or not course_info:
        raise ValueError(f"Konfigurasi tugas tidak ditemukan untuk course {course_id} sesi {session_num}")

    # Buka daftar pengumpulan langsung pada tabel grading (action=grading)
    grading_url = build_assignment_grading_url(cmid, perpage=100)
    print(f"[SCRAPER] Membuka tabel grading tugas {course_info['name']} Sesi {session_num}: {grading_url}...")
    await page.goto(grading_url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(1500)

    # Pastikan preferensi filter Moodle disetel ke 'submitted' (hanya menampilkan mahasiswa yang sudah
    # mengumpulkan tugas, baik yang sudah dinilai maupun belum dinilai, sehingga baris 'No submission'
    # tidak ikut tampil membingungkan di halaman e-learning UT) dan perpage '-1' (Semua).
    prefs = await page.evaluate('''() => {
        const f = document.querySelector("select[name='filter']");
        const p = document.querySelector("select[name='perpage']");
        const hasSubmittedOpt = f ? Array.from(f.options).some(o => o.value === "submitted") : false;
        return {
            hasForm: Boolean((f || p) && (f || p).closest("form")),
            filter: f ? f.value : "",
            targetFilter: hasSubmittedOpt ? "submitted" : "",
            perpage: p ? p.value : "-1"
        };
    }''')
    if isinstance(prefs, dict) and prefs.get("hasForm"):
        cur_filter = prefs.get("filter", "")
        target_filter = prefs.get("targetFilter", "submitted")
        cur_perpage = str(prefs.get("perpage", "-1"))
        if cur_filter != target_filter or cur_perpage not in ["-1", "100"]:
            print(f"[SCRAPER] Menyesuaikan filter ({cur_filter!r}->{target_filter!r}) & perpage ({cur_perpage!r}->'-1')...")
            async with page.expect_navigation(wait_until="domcontentloaded", timeout=30000):
                await page.evaluate('''(targetFilter) => {
                    const f = document.querySelector("select[name='filter']");
                    const p = document.querySelector("select[name='perpage']");
                    if (f) f.value = targetFilter;
                    if (p) p.value = "-1";
                    const form = (f || p).closest("form");
                    if (form) form.submit();
                }''', target_filter)
            await page.wait_for_timeout(1500)

    students = await page.evaluate('''() => {
        let trs = Array.from(document.querySelectorAll("table.generaltable tbody tr")).filter(
            tr => tr.id && tr.id.startsWith("mod_assign_grading") && !tr.classList.contains("emptyrow")
        );
        if (trs.length === 0) {
            trs = Array.from(document.querySelectorAll("table.generaltable tbody tr")).filter(
                tr => !tr.classList.contains("ygtvrow") && !tr.classList.contains("emptyrow")
            );
        }
        let list = [];
        trs.forEach(tr => {
            const userLink = tr.querySelector("td.cell.c2 a, td.fullname a, td:nth-child(3) a");
            const statusCell = tr.querySelector("td.cell.c4, td.status");
            const gradeCell = tr.querySelector("td.cell.c5, td.grade");
            const fileCell = tr.querySelector("td.cell.c8, td.files");
            const feedbackCell = tr.querySelector("td.cell.c10, td.feedback");
            const finalGradeCell = tr.querySelector("td.cell.c11, td.finalgrade");

            if (userLink && statusCell) {
                const name = userLink.innerText.trim();
                const statusRaw = statusCell.innerText.trim().replace(/\\s+/g, " ");
                const statusLower = statusRaw.toLowerCase();

                let userId = null;
                if (userLink && userLink.href) {
                    const match = userLink.href.match(/[?&]id=(\\d+)/);
                    if (match) userId = match[1];
                }

                const quickInput = gradeCell ? gradeCell.querySelector("input.quickgrade, input[type='text']") : null;
                if (!userId && quickInput && quickInput.name) {
                    const match = quickInput.name.match(/quickgrade_(\\d+)/);
                    if (match) userId = match[1];
                }

                let gradeText = "";
                if (quickInput) {
                    gradeText = quickInput.value.trim();
                } else if (finalGradeCell && finalGradeCell.innerText.trim() !== "-") {
                    gradeText = finalGradeCell.innerText.split("/")[0].trim();
                } else if (gradeCell) {
                    gradeText = gradeCell.innerText.split("/")[0].replace(/Grade|User grade/gi, "").trim();
                }

                const fileLinks = fileCell
                    ? Array.from(fileCell.querySelectorAll(".fileuploadsubmission a, a[href*='pluginfile.php']"))
                        .map(a => ({ name: a.innerText.trim(), href: a.href }))
                        .filter(x => Boolean(x.name && x.href))
                    : [];
                const fileNames = fileLinks.map(f => f.name).filter(Boolean);
                const fileText = fileNames.length > 0
                    ? fileNames.join(", ")
                    : (fileCell ? fileCell.innerText.trim().replace(/\\s+/g, " ") : "");

                const fbTextarea = feedbackCell ? feedbackCell.querySelector("textarea") : null;
                const feedbackRaw = fbTextarea
                    ? fbTextarea.value.trim()
                    : (feedbackCell ? feedbackCell.innerText.replace(/^Feedback comments$/i, "").trim() : "");

                const isNoSub = (
                    statusLower.includes("no submission") ||
                    statusLower.includes("belum ada") ||
                    statusLower.includes("tidak ada pengumpulan")
                );
                const hasGrade = gradeText !== "" && gradeText !== "-" && /[0-9]/.test(gradeText);

                // Hanya masukkan mahasiswa yang benar-benar sudah mengumpulkan tugas atau sudah memiliki nilai
                if (isNoSub && !hasGrade && !fileText) {
                    return;
                }

                list.push({
                    id: tr.id || null,
                    userId: userId,
                    author: name,
                    statusRaw: statusRaw,
                    status: "pending",
                    score: null,
                    gradeText: gradeText,
                    fileText: fileText,
                    files: fileLinks,
                    feedbackText: feedbackRaw
                });
            }
        });
        return list;
    }''')

    # Ekstrak konten berkas tugas (PDF/DOCX) secara otomatis dari e-learning UT
    for s in students:
        extracted_content = ""
        for f_obj in s.get("files", []):
            f_url = f_obj.get("href")
            f_name = f_obj.get("name", "")
            if f_url and ("pluginfile.php" in f_url or f_name.lower().endswith((".pdf", ".docx", ".doc"))):
                try:
                    resp = await page.context.request.get(f_url)
                    if resp.status == 200:
                        raw_bytes = await resp.body()
                        text = extract_text_from_bytes(f_name, raw_bytes)
                        if text:
                            extracted_content = text
                            break
                except Exception as e:
                    print(f"[SCRAPER] Peringatan: Gagal mengunduh berkas {f_name}: {e}")

        s["content"] = extracted_content if extracted_content else s.get("fileText", "")
        s["postId"] = s.get("userId")

    # Kembalikan filter Moodle ke 'requiregrading' (Requires grading) agar saat Ibu Tutor membuka
    # halaman tugas di elearning.ut.ac.id, yang tampil hanya tugas mahasiswa yang belum dinilai saja.
    if isinstance(prefs, dict) and prefs.get("hasForm"):
        try:
            async with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
                await page.evaluate('''() => {
                    const f = document.querySelector("select[name='filter']");
                    if (f && Array.from(f.options).some(o => o.value === "requiregrading")) {
                        f.value = "requiregrading";
                        const form = f.closest("form");
                        if (form) form.submit();
                    }
                }''')
        except Exception:
            pass

    for s in students:
        parsed_score, parsed_status = parse_assignment_grade_and_status(s.get("gradeText", ""))
        s["score"] = parsed_score
        s["status"] = parsed_status
        s["feedbackText"] = clean_html_feedback(s.get("feedbackText", ""))

    pending_count = sum(1 for s in students if s.get("status") != "completed")
    summary = {
        "Submitted": str(len(students)),
        "Needs grading": str(pending_count),
    }

    print(f"[SCRAPER] Berhasil mengekstrak {len(students)} pengumpulan tugas pada {course_info['name']} Sesi {session_num}")
    return {
        "course": course_info,
        "session": session_num,
        "summary": summary,
        "submissions": students
    }

