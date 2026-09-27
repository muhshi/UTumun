import json
import re

with open("data/sessions/sesi2_raw_scraped.json") as f:
    d = json.load(f)

pending_students = []

for cid, cdata in d.items():
    cinfo = cdata["course"]
    analysis = cdata["analysis"]
    students = analysis["students"]

    for s in students:
        # If no score or score is empty
        if not s.get("score") and not s.get("feedback"):
            pending_students.append({
                "course_name": cinfo["name"],
                "course_code": cinfo["code"],
                "course_id": cid,
                "student_name": s["name"],
                "nim": s["nim"],
                "content": s["content"]
            })

print(f"Total pending students across all courses: {len(pending_students)}")
for idx, p in enumerate(pending_students, 1):
    print(f"{idx}. [{p['course_name']}] {p['student_name']} (NIM: {p['nim'] or 'N/A'}) - Answer len: {len(p['content'])}")
