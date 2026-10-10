import re
from typing import Dict, Any, List, Tuple
from playwright.async_api import Page
from tuton.config import get_course_info, get_forum_cmid, COURSES
from tuton.matcher import clean_student_name

def build_flat_topic_url(raw_topic_url: str) -> str:
    r"""Mengekstrak d=(\d+) dan membangun URL flat mode bersih tanpa fragment hash."""
    d_match = re.search(r'[?&]d=(\d+)', raw_topic_url)
    if not d_match:
        raise ValueError(f"Tidak dapat mengekstrak ID diskusi dari URL: {raw_topic_url}")
    return f"https://elearning.ut.ac.id/mod/forum/discuss.php?d={d_match.group(1)}&mode=1"

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
