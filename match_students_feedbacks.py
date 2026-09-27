import json
import re

with open("data/sessions/course_413073_complete.json", "r", encoding="utf-8") as f:
    data = json.load(f)

students = data["students"]
feedbacks = data["feedbacks"]

# Clean student objects
student_dict = {}
for s in students:
    author = s["author"]
    nim_match = re.search(r"\b\d{9}\b", author) or re.search(r"NIM\s*[:\.]?\s*(\d{9})", s["content"], re.IGNORECASE)
    nim = nim_match.group(0) if nim_match else ""
    
    # clean name
    name = re.sub(r"\b\d{9}\b", "", author)
    for prefix in ["Re: Forum Diskusi.1 by", "Forum Diskusi.1 by", "Re:"]:
        name = name.replace(prefix, "")
    name = name.strip()

    pid = s["postId"]
    rating = s["rating"]
    score = rating if rating and rating not in ["-1", "-999", "0", ""] else None

    # Key by clean name lowercase or nim
    key = nim if nim else name.lower()
    
    # Store primary submission (usually the longer post if multiple)
    if key not in student_dict:
        student_dict[key] = {
            "name": name,
            "nim": nim,
            "postId": pid,
            "time": s["time"],
            "score": score,
            "content": s["content"],
            "feedback": None,
            "feedback_time": None
        }
    else:
        # If existing has no score but this one has
        if not student_dict[key]["score"] and score:
            student_dict[key]["score"] = score
        # Keep the one with longer content (the actual answer)
        if len(s["content"]) > len(student_dict[key]["content"]):
            student_dict[key]["content"] = s["content"]
            student_dict[key]["postId"] = pid

# Now match feedbacks to students
for fb in feedbacks:
    fb_text = fb["content"]
    matched_key = None
    
    # Check if student name is mentioned in feedback text
    for key, stu in student_dict.items():
        stu_name = stu["name"]
        first_word = stu_name.split()[0] if stu_name else ""
        if len(first_word) >= 3 and first_word.lower() in fb_text.lower():
            matched_key = key
            break

    if matched_key:
        student_dict[matched_key]["feedback"] = fb_text
        student_dict[matched_key]["feedback_time"] = fb["time"]

# Final classification
all_students = list(student_dict.values())
# Sort by name
all_students.sort(key=lambda x: x["name"])

lengkap = [s for s in all_students if s["score"] and s["feedback"]]
nilai_saja = [s for s in all_students if s["score"] and not s["feedback"]]
feedback_saja = [s for s in all_students if not s["score"] and s["feedback"]]
belum_keduanya = [s for s in all_students if not s["score"] and not s["feedback"]]

print(f"TOTAL MAHASISWA UNIK: {len(all_students)}")
print(f"1. Lengkap (Nilai + Feedback)  : {len(lengkap)}")
print(f"2. Nilai saja (Belum Feedback) : {len(nilai_saja)}")
print(f"3. Feedback saja (Belum Nilai) : {len(feedback_saja)}")
print(f"4. Belum Nilai & Belum Feedback: {len(belum_keduanya)}")

with open("data/sessions/matched_students.json", "w", encoding="utf-8") as f:
    json.dump(all_students, f, ensure_ascii=False, indent=2)

