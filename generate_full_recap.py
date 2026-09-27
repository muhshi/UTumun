import json
import re

with open("data/sessions/course_413073_complete.json", "r", encoding="utf-8") as f:
    data = json.load(f)

students = data["students"]
feedbacks = data["feedbacks"]

# Create a map of feedbacks by searching student name / NIM in feedback text
# Feedback format: "Halo [Nama] (NIM: [NIM]), ..."
feedback_by_student = {}
for fb in feedbacks:
    content = fb.get("content", "")
    m = re.search(r"Halo\s+([^(]+?)\s*\(NIM:\s*(\d+)\)", content, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        nim = m.group(2).strip()
        key = f"{name}_{nim}".lower()
        feedback_by_student[key] = fb
        # Also map by NIM alone
        feedback_by_student[nim] = fb

print(f"Total Feedback Posts parsed: {len(feedbacks)}")
print(f"Total Student Submissions: {len(students)}")

recap = []
for s in students:
    author = s.get("author", "")
    content = s.get("content", "")
    rating = s.get("rating")
    post_id = s.get("postId")
    time = s.get("time")

    # Extract NIM from author or content if available
    nim_m = re.search(r"\b(0\d{8}|\d{9})\b", author) or re.search(r"NIM\s*[:\.]?\s*(\d{9})", content, re.IGNORECASE)
    nim = nim_m.group(1) if nim_m else ""

    # Clean name (remove NIM and common prefixes)
    name_clean = re.sub(r"\b\d{9}\b", "", author).replace("Re:", "").replace("Forum Diskusi.1 by", "").strip()

    # Check rating status
    has_score = rating and rating not in ["-1", "-999", "0", ""]
    score_val = rating if has_score else None

    # Check feedback status
    matched_fb = None
    if nim and nim in feedback_by_student:
        matched_fb = feedback_by_student[nim]
    else:
        for k, fb in feedback_by_student.items():
            if name_clean and name_clean.lower() in k:
                matched_fb = fb
                break

    has_feedback = matched_fb is not None

    status = "LENGKAP" if (has_score and has_feedback) else ("NILAI_ONLY" if has_score else ("FEEDBACK_ONLY" if has_feedback else "BELUM_DINILAI"))

    recap.append({
        "post_id": post_id,
        "author": author,
        "name": name_clean,
        "nim": nim,
        "time": time,
        "score": score_val,
        "has_score": has_score,
        "has_feedback": has_feedback,
        "feedback_text": matched_fb.get("content") if matched_fb else None,
        "feedback_post_id": matched_fb.get("postId") if matched_fb else None,
        "student_content": content,
        "status": status
    })

# Deduplicate by student (some students post multiple times e.g. reply to others)
student_recap_map = {}
for r in recap:
    # Key by NIM if present, otherwise by name
    key = r["nim"] if r["nim"] else r["name"].lower()
    if key not in student_recap_map:
        student_recap_map[key] = r
    else:
        # If existing didn't have score but this one has, update
        existing = student_recap_map[key]
        if not existing["has_score"] and r["has_score"]:
            existing["score"] = r["score"]
            existing["has_score"] = True
            existing["status"] = "LENGKAP" if existing["has_feedback"] else "NILAI_ONLY"
        if not existing["has_feedback"] and r["has_feedback"]:
            existing["feedback_text"] = r["feedback_text"]
            existing["has_feedback"] = True
            existing["status"] = "LENGKAP" if existing["has_score"] else "FEEDBACK_ONLY"

final_list = list(student_recap_map.values())
print(f"Total Unique Students: {len(final_list)}")

lengkap = [s for s in final_list if s["status"] == "LENGKAP"]
nilai_only = [s for s in final_list if s["status"] == "NILAI_ONLY"]
belum = [s for s in final_list if s["status"] in ["BELUM_DINILAI", "FEEDBACK_ONLY"]]

print(f"- Lengkap (Nilai + Feedback): {len(lengkap)}")
print(f"- Nilai saja (Belum Feedback): {len(nilai_only)}")
print(f"- Belum Dinilai sama sekali: {len(belum)}")

with open("data/sessions/recap_413073.json", "w", encoding="utf-8") as f:
    json.dump(final_list, f, ensure_ascii=False, indent=2)

