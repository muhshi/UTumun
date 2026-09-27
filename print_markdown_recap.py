import json

with open("data/sessions/matched_students.json", "r", encoding="utf-8") as f:
    students = json.load(f)

print(f"| No | Nama Mahasiswa | NIM | Status | Nilai | Feedback Bu Ainur |")
print(f"|---|---|---|---|---|---|")
for idx, s in enumerate(students, 1):
    status_icon = "✅ Lengkap" if s["score"] and s["feedback"] else ("⚠️ Ada Nilai Saja" if s["score"] else "❌ Belum Dinilai")
    nilai_str = s["score"] if s["score"] else "-"
    fb_str = "Sudah ada" if s["feedback"] else "-"
    print(f"| {idx} | {s['name']} | {s['nim']} | {status_icon} | {nilai_str} | {fb_str} |")
