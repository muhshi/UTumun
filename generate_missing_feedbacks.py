import json

with open("data/sessions/matched_students.json", "r", encoding="utf-8") as f:
    students = json.load(f)

nilai_only = [s for s in students if s["score"] and not s["feedback"]]
print(f"Total Nilai Saja (Butuh Feedback): {len(nilai_only)}")
for s in nilai_only:
    print(f"- {s['name']} (NIM: {s['nim']}) -> Nilai: {s['score']}")
