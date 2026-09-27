import asyncio
import json
import os
import re
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("UT_USERNAME", "")
PASSWORD = os.getenv("UT_PASSWORD", "")
SESSION_FILE = ".auth/session.json"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

TARGET_COURSES = [
    {
        "id": "413073",
        "code": "MKWN4108.2137",
        "name": "Bahasa Indonesia 2137",
        "forum_cmid": "47302993",
        "forum_url": "https://elearning.ut.ac.id/mod/forum/view.php?id=47302993"
    },
    {
        "id": "413077",
        "code": "MKWN4108.2141",
        "name": "Bahasa Indonesia 2141",
        "forum_cmid": "47303711",
        "forum_url": "https://elearning.ut.ac.id/mod/forum/view.php?id=47303711"
    },
    {
        "id": "413081",
        "code": "MKWN4108.2145",
        "name": "Bahasa Indonesia 2145",
        "forum_cmid": "47304429",
        "forum_url": "https://elearning.ut.ac.id/mod/forum/view.php?id=47304429"
    },
    {
        "id": "411401",
        "code": "MKWN4108.465",
        "name": "Bahasa Indonesia 465",
        "forum_cmid": "46978721",
        "forum_url": "https://elearning.ut.ac.id/mod/forum/view.php?id=46978721"
    }
]

async def ensure_login(context, page):
    print("Checking session validity...")
    await page.goto("https://elearning.ut.ac.id/my/", wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)
    
    # Check if login is needed
    needs_login = False
    if "/login/" in page.url or await page.locator("#btnLoginMyUT").count() > 0:
        needs_login = True
    else:
        # Check if "Sesi Anda telah habis" modal or text is present
        expired_text = await page.evaluate("() => document.body.innerText.includes('Sesi Anda telah habis')")
        if expired_text:
            needs_login = True

    if needs_login:
        print("Session expired or not logged in. Logging in...")
        await page.goto("https://elearning.ut.ac.id/login/index.php", wait_until="domcontentloaded")
        await page.click("#btnLoginMyUT")
        await page.wait_for_timeout(1000)
        await page.click("#btnTutorEksternal")
        await page.wait_for_timeout(1000)
        await page.fill("#username_modal", USERNAME)
        await page.fill("#password_modal", PASSWORD)
        modal_submit = page.locator('#modalLogin, .modal-content, .modal-body').locator('button[type="submit"], input[type="submit"], button:has-text("Masuk")').first
        if await modal_submit.count() > 0:
            await modal_submit.click()
        else:
            await page.locator("#password_modal").press("Enter")
        await page.wait_for_url(lambda u: "/my/" in u, timeout=30000)
        await context.storage_state(path=SESSION_FILE)
        print("Logged in successfully and session saved!")
    else:
        print("Session is active and valid.")

async def scrape_course_forum(page, course):
    print(f"\n=======================================================")
    print(f"Scraping {course['name']} ({course['code']})...")
    print(f"Forum URL: {course['forum_url']}")
    print(f"=======================================================")

    await page.goto(course["forum_url"], wait_until="domcontentloaded")
    await page.wait_for_timeout(2500)

    # Find discussion link
    topic_url = await page.evaluate('''() => {
        const a = document.querySelector('a[href*="/mod/forum/discuss.php?d="]');
        return a ? a.href : null;
    }''')

    # Extract discussion ID d=(\d+) cleanly without URL fragment
    d_match = re.search(r'[?&]d=(\d+)', topic_url)
    if not d_match:
        print(f"ERROR: Could not parse discussion ID from {topic_url}!")
        return []
    
    d_id = d_match.group(1)
    flat_url = f"https://elearning.ut.ac.id/mod/forum/discuss.php?d={d_id}&mode=1"
    print(f"Opening discussion topic in flat mode: {flat_url}")
    await page.goto(flat_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(4000)

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
    print(f"Extracted {len(posts)} total posts for {course['name']}.")
    return posts

def analyze_posts(posts):
    if not posts:
        return {"topic": None, "feedbacks": [], "students": []}

    topic = posts[0]
    feedbacks = []
    students_raw = []

    for p in posts[1:]:
        content = p["content"]
        author_lower = p["author"].lower()
        if "ainur" in author_lower or (content.startswith("Halo ") and ("terima kasih" in content.lower() or "diskusi" in content.lower())):
            p["is_feedback"] = True
            feedbacks.append(p)
        else:
            p["is_feedback"] = False
            students_raw.append(p)

    student_dict = {}
    for s in students_raw:
        author = s["author"]
        nim_match = re.search(r"\b\d{9}\b", author) or re.search(r"NIM\s*[:\.]?\s*(\d{9})", s["content"], re.IGNORECASE)
        nim = nim_match.group(0) if nim_match else ""

        name = re.sub(r"\b\d{9}\b", "", author)
        for prefix in ["Re: Forum Diskusi.1 by", "Forum Diskusi.1 by", "Re:"]:
            name = name.replace(prefix, "")
        name = name.strip()

        pid = s["postId"]
        rating = s["rating"]
        score = rating if rating and rating not in ["-1", "-999", "0", ""] else None

        key = nim if nim else name.lower()
        if key not in student_dict:
            student_dict[key] = {
                "name": name,
                "nim": nim,
                "postId": pid,
                "time": s["time"],
                "score": score,
                "content": s["content"],
                "feedback": None
            }
        else:
            # Keep highest score if available
            if not student_dict[key]["score"] and score:
                student_dict[key]["score"] = score
            # Keep longest content (primary response vs brief reply)
            if len(s["content"]) > len(student_dict[key]["content"]):
                student_dict[key]["content"] = s["content"]
                student_dict[key]["postId"] = pid

    # Associate existing feedback to student
    for fb in feedbacks:
        fb_text = fb["content"]
        for key, stu in student_dict.items():
            first_word = stu["name"].split()[0] if stu["name"] else ""
            if len(first_word) >= 3 and first_word.lower() in fb_text.lower():
                student_dict[key]["feedback"] = fb_text
                break

    all_students = list(student_dict.values())
    all_students.sort(key=lambda x: x["name"])
    return {
        "topic": topic,
        "feedbacks": feedbacks,
        "students": all_students
    }

async def main():
    os.makedirs("data/sessions", exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROME_PATH, headless=True)
        context = await browser.new_context(
            storage_state=SESSION_FILE if os.path.exists(SESSION_FILE) else None,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        await ensure_login(context, page)

        all_results = {}
        for c in TARGET_COURSES:
            posts = await scrape_course_forum(page, c)
            analysis = analyze_posts(posts)
            all_results[c["id"]] = {
                "course": c,
                "total_posts": len(posts),
                "analysis": analysis
            }

        with open("data/sessions/all_classes_scraped.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        print("\nAll 4 courses successfully scraped and saved to data/sessions/all_classes_scraped.json!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
