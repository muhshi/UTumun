import re
from typing import List, Dict, Any

GREETING_STOPWORDS = {
    'halo', 'saudara', 'saudari', 'waalaikumsalam', 'warahmatullahi', 'wabarakatuh',
    'wr', 'wb', 'selamat', 'pagi', 'siang', 'sore', 'malam', 'rekan', 'teman', 'mahasiswa',
    'terima', 'kasih', 'jawaban', 'anda', 'yang', 'sampaikan', 'berikan', 'sudah', 'sangat',
    'baik', 'dan', 'menunjukkan', 'pemahaman', 'terhadap', 'mengenai', 'izin', 'menjawab',
    'ibu', 'bapak', 'tutor', 'dosen', 'assalamualaikum', 'assalamu', 'alaikum'
}

def normalize_name(name: str) -> str:
    """Membersihkan simbol dan merapikan spasi."""
    n = re.sub(r'[^a-zA-Z0-9\s]', ' ', name.lower())
    return ' '.join(n.split())

def clean_student_name(author: str) -> str:
    """Membersihkan awalan Moodle dan NIM dari nama mahasiswa."""
    for prefix in [
        "Re: Forum Diskusi.1 by", "Forum Diskusi.1 by",
        "Re: Forum Diskusi.2 by", "Forum Diskusi.2 by",
        "Re: Forum Diskusi by", "Forum Diskusi by", "Re:"
    ]:
        author = author.replace(prefix, "")
    author = re.sub(r"\b\d{9}\b", "", author).strip()
    return author

def match_feedbacks_to_students(students: List[Dict[str, Any]], tutor_posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Mencocokkan postingan feedback tutor ke mahasiswa yang bersangkutan
    menggunakan pencocokan NIM, nama lengkap, dan fuzzy token sapaan pembuka.
    """
    # Clone student list
    res_students = [dict(s) for s in students]

    for fb in tutor_posts:
        content = fb.get("content", "")
        header = content[:200]
        header_norm = normalize_name(header)
        header_clean = re.sub(r'[^a-z0-9]', '', header_norm)

        matched_idx = None

        # 1. Cek kecocokan NIM langsung di teks feedback
        nim_match = re.search(r"\b\d{9}\b", header)
        if nim_match:
            nim_val = nim_match.group(0)
            for idx, s in enumerate(res_students):
                if s.get("nim") == nim_val:
                    matched_idx = idx
                    break

        # 2. Cek kecocokan nama lengkap (tanpa spasi/tanda baca)
        if matched_idx is None:
            for idx, s in enumerate(res_students):
                stu_clean = re.sub(r'[^a-z0-9]', '', normalize_name(s.get("name", "")))
                if stu_clean and len(stu_clean) >= 4 and stu_clean in header_clean:
                    matched_idx = idx
                    break

        # 3. Cek kecocokan multi-token nama pada 5 kata pertama penerima
        if matched_idx is None:
            header_words = [w for w in normalize_name(header).split() if w not in GREETING_STOPWORDS and len(w) >= 3]
            target_tokens = header_words[:4]
            best_score = 0
            best_idx = None
            for idx, s in enumerate(res_students):
                stu_tokens = set(normalize_name(s.get("name", "")).split())
                matches = sum(1 for t in target_tokens if t in stu_tokens)
                if matches > best_score:
                    best_score = matches
                    best_idx = idx
            if best_score >= 1:
                matched_idx = best_idx

        if matched_idx is not None:
            res_students[matched_idx]["feedback"] = content

    return res_students
