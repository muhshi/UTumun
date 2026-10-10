import asyncio
import argparse
import os
from playwright.async_api import async_playwright
from tuton.config import COURSES, CHROME_PATH, SESSION_FILE
from tuton.auth import ensure_authenticated_page
from tuton.scraper import scrape_session_forum, parse_post_author_and_nim
from tuton.matcher import match_feedbacks_to_students
from tuton.evaluator import evaluate_submission
from tuton.reporter import (
    format_recap_summary_table,
    format_pending_names_list,
    format_pending_student_card
)

async def run_pipeline(session_target: str = "all", mode: str = "full"):
    """
    Menjalankan pipeline terpadu:
    mode='recap': Tahap 1 saja (Ringkasan & Daftar Nama yang Kurang)
    mode='grade': Tahap 2 saja (Nilai & Feedback)
    mode='full': Tahap 1 kemudian Tahap 2
    """
    sessions = [1, 2] if session_target == "all" else [int(session_target)]

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROME_PATH, headless=True)
        context = await browser.new_context(
            storage_state=SESSION_FILE if os.path.exists(SESSION_FILE) else None,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Step 1: Auto login & session check
        await ensure_authenticated_page(context, page)

        summary_table_data = []
        all_pending_grouped = {}
        all_evaluations = []

        for s_num in sessions:
            class_summaries = []
            for c in COURSES:
                cid = c["id"]
                raw_data = await scrape_session_forum(page, cid, s_num)
                posts = raw_data["posts"]

                topic_post = posts[0] if posts else None
                tutor_posts = [p for p in posts[1:] if "ainur" in p["author"].lower() or "01007726" in p["author"]]
                student_raw = [p for p in posts[1:] if p not in tutor_posts]

                # Deduplikasi mahasiswa
                student_map = {}
                for sp in student_raw:
                    cname, nim = parse_post_author_and_nim(sp["author"], sp["content"])
                    key = nim if nim else cname.lower()
                    score = sp["rating"] if sp["rating"] and sp["rating"] not in ["-1", "-999", "0", ""] else None
                    if key not in student_map:
                        student_map[key] = {
                            "name": cname,
                            "nim": nim,
                            "postId": sp["postId"],
                            "score": score,
                            "content": sp["content"],
                            "feedback": None
                        }
                    else:
                        if not student_map[key]["score"] and score:
                            student_map[key]["score"] = score
                        if len(sp["content"]) > len(student_map[key]["content"]):
                            student_map[key]["content"] = sp["content"]

                # Rekonsiliasi feedback
                matched_students = match_feedbacks_to_students(list(student_map.values()), tutor_posts)
                matched_students.sort(key=lambda x: x["name"])

                completed = [s for s in matched_students if s["score"] and s["feedback"]]
                pending = [s for s in matched_students if not (s["score"] and s["feedback"])]

                class_summaries.append({
                    "name": c["name"],
                    "code": c["code"],
                    "total": len(matched_students),
                    "completed": len(completed),
                    "pending": len(pending)
                })

                group_key = f"Sesi {s_num} — {c['name']} ({c['code']})"
                all_pending_grouped[group_key] = pending

                # Siapkan evaluasi draf nilai & feedback untuk mahasiswa yang pending
                for ps in pending:
                    status_desc = "Belum ada nilai & belum ada feedback"
                    if ps["score"] and not ps["feedback"]:
                        status_desc = f"Sudah ada nilai ({ps['score']}), butuh teks feedback"
                    elif not ps["score"] and ps["feedback"]:
                        status_desc = "Sudah ada feedback, butuh input nilai di web"

                    eval_res = evaluate_submission(ps["name"], ps["content"], s_num)
                    all_evaluations.append({
                        "name": eval_res["name"],
                        "nim": ps.get("nim"),
                        "course_name": c["name"],
                        "session": s_num,
                        "score": ps["score"] if ps["score"] else eval_res["score"],
                        "status_desc": status_desc,
                        "feedback": eval_res["feedback"]
                    })

            summary_table_data.append({"session": s_num, "classes": class_summaries})

        await browser.close()

    # OUTPUT TAHAP 1: REKAPITULASI STATUS
    print("\n" + "="*70)
    print(" TAHAP 1: REKAPITULASI STATUS KELAS & MAHASISWA KURANG")
    print("="*70 + "\n")
    print(format_recap_summary_table(summary_table_data))
    print("\n" + "-"*70)
    print(" DAFTAR MAHASISWA YANG MASIH KURANG (PENDING)")
    print("-"*70 + "\n")
    print(format_pending_names_list(all_pending_grouped))

    # OUTPUT TAHAP 2: NILAI DAN FEEDBACK (Jika mode full atau grade)
    if mode in ["full", "grade"]:
        print("\n" + "="*70)
        print(" TAHAP 2: REKOMENDASI NILAI & DRAF FEEDBACK SIAP SALIN")
        print("="*70 + "\n")
        if not all_evaluations:
            print("Luar biasa! Semua mahasiswa di sesi yang dipilih telah selesai dinilai dan memiliki feedback.")
        else:
            for s_eval in all_evaluations:
                print(format_pending_student_card(s_eval))

def main():
    parser = argparse.ArgumentParser(description="UT Tuton Automation & Evaluation Assistant")
    parser.add_argument("--session", choices=["1", "2", "all"], default="all", help="Pilih sesi yang diproses (1, 2, atau all)")
    parser.add_argument("--mode", choices=["recap", "grade", "full"], default="full", help="recap: ringkasan saja; grade: nilai & feedback; full: keduanya")
    args = parser.parse_args()

    asyncio.run(run_pipeline(session_target=args.session, mode=args.mode))

if __name__ == "__main__":
    main()
