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

COURSES_SESI2 = [
    {
        "id": "413073",
        "code": "MKWN4108.2137",
        "name": "Bahasa Indonesia 2137",
        "forum_url": "https://elearning.ut.ac.id/mod/forum/view.php?id=47303004"
    },
    {
        "id": "413077",
        "code": "MKWN4108.2141",
        "name": "Bahasa Indonesia 2141",
        "forum_url": "https://elearning.ut.ac.id/mod/forum/view.php?id=47303722"
    },
    {
        "id": "413081",
        "code": "MKWN4108.2145",
        "name": "Bahasa Indonesia 2145",
        "forum_url": "https://elearning.ut.ac.id/mod/forum/view.php?id=47304452"
    },
    {
        "id": "411401",
        "code": "MKWN4108.465",
        "name": "Bahasa Indonesia 465",
        "forum_url": "https://elearning.ut.ac.id/mod/forum/view.php?id=46978750"
    }
]

async def scrape_course_sesi2(page, course):
    print(f"\n=======================================================")
    print(f"Scraping Sesi 2 for {course['name']} ({course['code']})...")
    print(f"Forum URL: {course['forum_url']}")
    print(f"=======================================================")

    await page.goto(course["forum_url"], wait_until="domcontentloaded")
    await page.wait_for_timeout(2500)

    topic_url = await page.evaluate('''() => {
        const a = document.querySelector('a[href*="/mod/forum/discuss.php?d="]');
        return a ? a.href : null;
    }''')

    if not topic_url:
        print(f"ERROR: No discussion topic found in {course['name']}!")
        return []

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
    print(f"Extracted {len(posts)} total posts for Sesi 2 {course['name']}.")
    return posts

def analyze_sesi2_posts(posts):
    if not posts:
        return {"topic": None, "feedbacks": [], "students": []}

    topic = posts[0]
    tutor_fbs = []
    student_posts = []

    for p in posts[1:]:
        author = p["author"].lower()
        if "ainur" in author or "01007726" in author:
            tutor_fbs.append(p)
        else:
            student_posts.append(p)

    student_dict = {}
    for s in student_posts:
        author = s["author"]
        for prefix in ["Re: Forum Diskusi.2 by", "Forum Diskusi.2 by", "Re:"]:
            author = author.replace(prefix, "")
        clean_name = re.sub(r"\b\d{9}\b", "", author).strip()
        
        nim_match = re.search(r"\b\d{9}\b", s["author"]) or re.search(r"NIM\s*[:\.]?\s*(\d{9})", s["content"], re.IGNORECASE)
        nim = nim_match.group(0) if nim_match else ""

        key = nim if nim else clean_name.lower()
        rating = s["rating"]
        score = rating if rating and rating not in ["-1", "-999", "0", ""] else None

        if key not in student_dict:
            student_dict[key] = {
                "name": clean_name,
                "nim": nim,
                "postId": s["postId"],
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
                student_dict[key]["postId"] = s["postId"]

    # Match existing tutor feedbacks
    for fb in tutor_fbs:
        header = fb["content"][:150].lower()
        for key, stu in student_dict.items():
            name_parts = [p for p in stu["name"].lower().split() if len(p) >= 3]
            if not name_parts:
                continue
            if stu["name"].lower() in header or (len(name_parts) >= 2 and all(p in header for p in name_parts[:2])):
                student_dict[key]["feedback"] = fb["content"]
                break

    all_students = list(student_dict.values())
    all_students.sort(key=lambda x: x["name"])
    return {
        "topic": topic,
        "feedbacks": tutor_fbs,
        "students": all_students
    }

async def main():
    os.makedirs("data/sessions", exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROME_PATH, headless=True)
        context = await browser.new_context(storage_state=SESSION_FILE)
        page = await context.new_page()

        results = {}
        for c in COURSES_SESI2:
            posts = await scrape_course_sesi2(page, c)
            analysis = analyze_sesi2_posts(posts)
            results[c["id"]] = {
                "course": c,
                "total_posts": len(posts),
                "analysis": analysis
            }

        with open("data/sessions/sesi2_raw_scraped.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print("\nAll 4 courses Sesi 2 scraped successfully!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
