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

COURSES = [
    {"id": "413073", "name": "Bahasa Indonesia 2137", "code": "MKWN4108.2137"},
    {"id": "413077", "name": "Bahasa Indonesia 2141", "code": "MKWN4108.2141"},
    {"id": "413081", "name": "Bahasa Indonesia 2145", "code": "MKWN4108.2145"},
    {"id": "411401", "name": "Bahasa Indonesia 465",  "code": "MKWN4108.465"}
]

async def ensure_login(context, page):
    print("Checking session validity...")
    await page.goto("https://elearning.ut.ac.id/my/", wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)
    
    if "/login/" in page.url or await page.locator("#btnLoginMyUT").count() > 0:
        print("Session expired or not logged in. Performing login...")
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
        await page.wait_for_url(lambda u: "/my/" in u, timeout=20000)
        await context.storage_state(path=SESSION_FILE)
        print("Logged in successfully and session saved!")
    else:
        print("Existing session is valid!")

async def find_sesi1_forum_url(page, course_id):
    url = f"https://elearning.ut.ac.id/course/view.php?id={course_id}"
    print(f"Opening course {course_id} at {url}...")
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

    # Find Forum Diskusi.1
    forum_href = await page.evaluate('''() => {
        const links = Array.from(document.querySelectorAll('a[href*="/mod/forum/view.php?id="]'));
        for (const l of links) {
            if (l.innerText.includes("Forum Diskusi.1") || l.innerText.includes("Diskusi.1") || l.innerText.includes("Diskusi 1")) {
                return l.href;
            }
        }
        return links.length > 0 ? links[0].href : null;
    }''')
    print(f"Course {course_id} Sesi 1 Forum URL: {forum_href}")
    return forum_href

async def scrape_forum(page, forum_url):
    print(f"Opening forum {forum_url}...")
    await page.goto(forum_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

    # Get discussion topic link
    topic_url = await page.evaluate('''() => {
        const a = document.querySelector('a[href*="/mod/forum/discuss.php?d="]');
        return a ? a.href : null;
    }''')
    
    if not topic_url:
        print("No discussion topic link found on forum page.")
        return []

    # Switch to flat mode (&mode=1)
    if "mode=1" not in topic_url:
        if "?" in topic_url:
            topic_url += "&mode=1"
        else:
            topic_url += "?mode=1"

    print(f"Opening topic in flat mode: {topic_url}...")
    await page.goto(topic_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

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
    print(f"Extracted {len(posts)} total posts.")
    return posts

def analyze_course_posts(posts):
    if not posts:
        return {"students": [], "feedbacks": [], "topic": None}

    topic = posts[0]
    feedbacks = []
    students_raw = []

    for p in posts[1:]:
        content = p["content"]
        if "ainur" in p["author"].lower() or (content.startswith("Halo ") and ("terima kasih" in content.lower() or "diskusi" in content.lower())):
            p["is_feedback"] = True
            feedbacks.append(p)
        else:
            p["is_feedback"] = False
            students_raw.append(p)

    # Process and deduplicate students
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
            if not student_dict[key]["score"] and score:
                student_dict[key]["score"] = score
            if len(s["content"]) > len(student_dict[key]["content"]):
                student_dict[key]["content"] = s["content"]
                student_dict[key]["postId"] = pid

    # Match feedbacks to students
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
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True
        )
        context = await browser.new_context(
            storage_state=SESSION_FILE if os.path.exists(SESSION_FILE) else None,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        await ensure_login(context, page)

        results = {}
        for c in COURSES:
            cid = c["id"]
            cname = c["name"]
            print(f"\n==========================================")
            print(f"Scanning Course: {cname} ({cid})...")
            print(f"==========================================")
            forum_url = await find_sesi1_forum_url(page, cid)
            if forum_url:
                posts = await scrape_forum(page, forum_url)
                analysis = analyze_course_posts(posts)
                results[cid] = {
                    "info": c,
                    "forum_url": forum_url,
                    "analysis": analysis
                }
            else:
                print(f"Could not find Forum Diskusi 1 for {cname}")

        with open("data/sessions/all_courses_scan.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print("\nAll courses scanned and saved to data/sessions/all_courses_scan.json!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
