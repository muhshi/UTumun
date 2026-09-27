import json

with open("data/sessions/course_413073_complete.json") as f:
    d = json.load(f)

p = [s for s in d["students"] if not s["rating"] or s["rating"] in ["-1", "-999", "0", ""]]
print(f"Total Pending: {len(p)}")
for idx, s in enumerate(p, 1):
    print(f"[{idx}] {s['author']} (ID: {s['postId']}, Date: {s['time']})")
    print(f"    Snippet: {s['content'][:120]}...\n")
