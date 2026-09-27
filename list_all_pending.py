import json

with open("data/sessions/course_413073_complete.json", "r", encoding="utf-8") as f:
    data = json.load(f)

students = data["students"]
pending = [s for s in students if not s["rating"] or s["rating"] in ["-1", "-999", "0", ""]]

print(f"Total Pending: {len(pending)}\n")
for idx, p in enumerate(pending, 1):
    print(f"[{idx}] {p['author']} | Post ID: {p['postId']}")
    print(f"Tanggal: {p['time']}")
    print(f"Jawaban:\n{p['content']}\n")
    print("="*60)
