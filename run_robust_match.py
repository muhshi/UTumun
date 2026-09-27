import json
import re

with open("data/sessions/all_classes_scraped.json", "r", encoding="utf-8") as f:
    data = json.load(f)

def clean_str(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

def get_name_tokens(s):
    s = re.sub(r'[^a-zA-Z\s]', ' ', s).lower()
    return [w for w in s.split() if len(w) >= 2]

GREETING_WORDS = {
    'halo', 'saudara', 'saudari', 'waalaikumsalam', 'warahmatullahi', 'wabarakatuh',
    'wr', 'wb', 'selamat', 'pagi', 'siang', 'sore', 'malam', 'rekan', 'teman', 'mahasiswa',
    'terima', 'kasih', 'jawaban', 'anda', 'yang', 'sampaikan', 'berikan', 'sudah', 'sangat',
    'baik', 'dan', 'menunjukkan', 'pemahaman', 'terhadap', 'mengenai', 'izin', 'menjawab',
    'ibu', 'bapak', 'tutor', 'dosen', 'assalamualaikum', 'assalamu', 'alaikum'
}

for cid, cdata in data.items():
    cname = cdata["course"]["name"]
    raw_feedbacks = cdata["analysis"]["feedbacks"]
    raw_students = cdata["analysis"]["students"]

    # Extract actual tutor posts
    tutor_fbs = []
    student_posts = []
    for p in raw_feedbacks + raw_students:
        author = p.get("author", "").lower()
        if "ainur" in author or "01007726" in author:
            if p not in tutor_fbs:
                tutor_fbs.append(p)
        else:
            student_posts.append(p)

    # Deduplicate students
    students = {}
    for s in student_posts:
        author = s.get("author") or s.get("name") or ""
        for prefix in ["Re: Forum Diskusi.1 by", "Forum Diskusi.1 by", "Re:"]:
            author = author.replace(prefix, "")
        clean_name = re.sub(r"\b\d{9}\b", "", author).strip()
        nim = s.get("nim", "")
        if not nim:
            m = re.search(r"\b\d{9}\b", s.get("author", "")) or re.search(r"NIM\s*[:\.]?\s*(\d{9})", s.get("content", ""), re.IGNORECASE)
            nim = m.group(0) if m else ""

        key = nim if nim else clean_str(clean_name)
        score = s.get("score")
        if score in ["-1", "-999", "0", ""]:
            score = None

        if key not in students:
            students[key] = {
                "name": clean_name,
                "nim": nim,
                "postId": s.get("postId"),
                "time": s.get("time"),
                "score": score,
                "content": s.get("content", ""),
                "feedback": None
            }
        else:
            if not students[key]["score"] and score:
                students[key]["score"] = score
            if len(s.get("content", "")) > len(students[key]["content"]):
                students[key]["content"] = s.get("content", "")
                students[key]["postId"] = s.get("postId")

    # Match each tutor feedback to student
    unmatched_fbs = []
    for fb in tutor_fbs:
        content = fb.get("content", "")
        header = content[:180]
        tokens = [w for w in get_name_tokens(header) if w not in GREETING_WORDS]
        header_clean = clean_str(header)

        matched_key = None
        
        # 1. Direct NIM match in feedback
        nim_match = re.search(r"\b\d{9}\b", header)
        if nim_match and nim_match.group(0) in students:
            matched_key = nim_match.group(0)

        # 2. Check full student name in header
        if not matched_key:
            for key, stu in students.items():
                stu_clean = clean_str(stu["name"])
                if stu_clean and stu_clean in header_clean:
                    matched_key = key
                    break

        # 3. Check tokens (first 3 words of recipient in feedback)
        if not matched_key and tokens:
            target_tokens = tokens[:4]
            best_score = 0
            best_stu = None
            for key, stu in students.items():
                stu_tokens = set(get_name_tokens(stu["name"]))
                match_count = sum(1 for t in target_tokens if t in stu_tokens)
                if match_count > best_score:
                    best_score = match_count
                    best_stu = key
            if best_score >= 1:
                matched_key = best_stu

        if matched_key:
            students[matched_key]["feedback"] = content
        else:
            unmatched_fbs.append(header)

    student_list = list(students.values())
    student_list.sort(key=lambda x: x["name"])

    completed = [s for s in student_list if s["score"] and s["feedback"]]
    pending_score = [s for s in student_list if not s["score"] and s["feedback"]]
    pending_fb = [s for s in student_list if s["score"] and not s["feedback"]]
    pending_both = [s for s in student_list if not s["score"] and not s["feedback"]]

    print(f"\n=======================================================")
    print(f"Course: {cname} ({cid})")
    print(f"Total Unique Students: {len(student_list)}")
    print(f"Total Tutor Feedbacks Posted: {len(tutor_fbs)}")
    print(f"  [SELESAI] Sudah Ada Nilai & Feedback: {len(completed)}")
    print(f"  [BUTUH NILAI] Sudah Ada Feedback tapi Nilai Kosong: {len(pending_score)}")
    print(f"  [BUTUH FEEDBACK] Sudah Ada Nilai tapi Feedback Kosong: {len(pending_fb)}")
    print(f"  [BELUM KEDUANYA] Belum Nilai & Belum Feedback: {len(pending_both)}")

    if pending_score:
        print("  --> Siswa Butuh Nilai Saja:")
        for s in pending_score:
            print(f"      * {s['name']} (NIM: {s['nim']})")

    if pending_fb:
        print("  --> Siswa Butuh Feedback Saja (Nilai sudah ada):")
        for s in pending_fb:
            print(f"      * {s['name']} (NIM: {s['nim']}) | Nilai Saat Ini: {s['score']}")

    if pending_both:
        print("  --> Siswa Belum Nilai & Belum Feedback:")
        for s in pending_both:
            print(f"      * {s['name']} (NIM: {s['nim']})")

    if unmatched_fbs:
        print(f"  (Unmatched feedback posts: {len(unmatched_fbs)})")
        for u in unmatched_fbs:
            print(f"    - {u[:80]}...")
