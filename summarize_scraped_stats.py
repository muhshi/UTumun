import json

with open("data/sessions/all_classes_scraped.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for cid, cdata in data.items():
    cinfo = cdata["course"]
    analysis = cdata["analysis"]
    students = analysis["students"]
    feedbacks = analysis["feedbacks"]

    graded_and_fb = [s for s in students if s["score"] and s["feedback"]]
    graded_no_fb = [s for s in students if s["score"] and not s["feedback"]]
    uncompleted = [s for s in students if not s["score"]]

    print(f"\n==========================================")
    print(f"{cinfo['name']} ({cinfo['code']}) - ID: {cid}")
    print(f"Total Posts: {cdata['total_posts']}")
    print(f"Total Unique Students: {len(students)}")
    print(f"Tutor Feedbacks Found: {len(feedbacks)}")
    print(f"1. Sudah Nilai & Sudah Ada Feedback: {len(graded_and_fb)}")
    print(f"2. Sudah Ada Nilai tapi Belum Feedback: {len(graded_no_fb)}")
    print(f"3. Belum Ada Nilai Sama Sekali: {len(uncompleted)}")
    print(f"Total Butuh Diproses (2 + 3): {len(graded_no_fb) + len(uncompleted)}")
