import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import tuton.config as config
from tuton.db import Database, get_db
from tuton.matcher import clean_student_name

logger = logging.getLogger(__name__)

COURSE_CODE_MAP = {
    "2137": "413073",
    "MKWN4108.2137": "413073",
    "Bahasa Indonesia 2137": "413073",
    "413073": "413073",

    "2141": "413077",
    "MKWN4108.2141": "413077",
    "Bahasa Indonesia 2141": "413077",
    "413077": "413077",

    "2145": "413081",
    "MKWN4108.2145": "413081",
    "Bahasa Indonesia 2145": "413081",
    "413081": "413081",

    "465": "411401",
    "MKWN4108.465": "411401",
    "Bahasa Indonesia 465": "411401",
    "411401": "411401",
}


def resolve_course_id(text: Optional[str]) -> Optional[str]:
    """Mencari course_id (413073, 413077, 413081, 411401) dari teks nama/kode kelas."""
    if not text:
        return None
    text_str = str(text)
    for key, cid in COURSE_CODE_MAP.items():
        if key in text_str:
            return cid
    return None


def parse_markdown_report(file_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """Mem-parsing berkas laporan markdown evaluasi (SESI1 s.d. SESI4)
    dan mengekstrak data evaluasi mahasiswa per kelas.
    """
    path = Path(file_path)
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8")

    # Deteksi nomor sesi dari nama file atau isi dokumen
    m_sess = re.search(r"SESI\s*(\d+)", path.name, re.IGNORECASE)
    if not m_sess:
        m_sess = re.search(r"Sesi\s*(\d+)", content[:500], re.IGNORECASE)
    session_num = int(m_sess.group(1)) if m_sess else None

    lines = content.splitlines()
    current_course = None
    current_head = None
    current_block: List[str] = []
    results: List[Dict[str, Any]] = []

    def save_item(head: Optional[str], block: List[str], default_cid: Optional[str]):
        if not head:
            return
        m_head = re.search(r"###\s+\d+\.\s+([^\n\(]+)\s*\(NIM:\s*(\d+)\)\s*(?:—|-)?\s*([^\n]*)", head)
        if not m_head:
            m_head = re.search(r"\d+\.\s+([^\n\(]+)\s*\(NIM:\s*(\d+)\)\s*(?:—|-)?\s*([^\n]*)", head)
        if not m_head:
            return

        name = clean_student_name(m_head.group(1).strip())
        nim = m_head.group(2).strip()
        extra = m_head.group(3).strip() if len(m_head.groups()) >= 3 else ""
        cid = resolve_course_id(extra) or default_cid

        text = "\n".join(block)

        m_score = re.search(r"Rekomendasi Nilai:[\*\s]+(\d+)", text)
        score = int(m_score.group(1)) if m_score else None

        m_fb = re.search(r"```text\s*\n(.*?)\n```", text, re.DOTALL)
        fb = m_fb.group(1).strip() if m_fb else None

        m_status = re.search(r"Status:[\*\s]+([^\n]+)", text)
        status_raw = m_status.group(1).strip() if m_status else ""
        if "sudah" in status_raw.lower():
            status = "completed"
        elif "belum" in status_raw.lower():
            status = "pending"
        else:
            status = "completed" if score is not None and fb else "pending"

        if nim and cid:
            results.append({
                "name": name,
                "nim": nim,
                "course_id": cid,
                "session_num": session_num,
                "score": score,
                "feedback": fb,
                "status": status,
            })

    for line in lines:
        if line.startswith("## "):
            save_item(current_head, current_block, current_course)
            current_head = None
            current_block = []
            cid = resolve_course_id(line)
            if cid:
                current_course = cid
        elif line.startswith("### "):
            save_item(current_head, current_block, current_course)
            current_head = line
            current_block = []
        else:
            current_block.append(line)

    save_item(current_head, current_block, current_course)
    return results


def seed_from_markdown_reports(
    db: Database,
    base_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Mengimpor data historis mahasiswa dan submission dari file markdown
    laporan evaluasi dan berkas scraping JSON di data/sessions/.
    """
    if base_dir is None:
        base_path = Path(getattr(config, "BASE_DIR", Path.cwd()))
    else:
        base_path = Path(base_dir)

    data_dir = base_path / "data"
    sessions_dir = data_dir / "sessions"

    # Pastikan database telah diinisialisasi
    db.init_db()

    # 1. Impor Sesi 1 dari all_classes_scraped.json
    s1_file = sessions_dir / "all_classes_scraped.json"
    if s1_file.exists():
        try:
            with open(s1_file, "r", encoding="utf-8") as f:
                s1_data = json.load(f)
            for cid_key, cdata in s1_data.items():
                cid = resolve_course_id(cid_key) or str(cid_key)
                analysis = cdata.get("analysis", {})
                students = analysis.get("students", [])
                for st in students:
                    nim = str(st.get("nim", "")).strip()
                    if not nim:
                        continue
                    name = clean_student_name(st.get("name") or st.get("student_name") or f"Mahasiswa {nim}")
                    post_id = st.get("postId") or st.get("post_id")
                    content = st.get("content")
                    raw_score = st.get("score")
                    score = int(raw_score) if raw_score is not None and str(raw_score).isdigit() else None
                    feedback = st.get("feedback")
                    status = "completed"

                    db.upsert_student(nim=nim, name=name, course_id=cid)
                    db.upsert_submission(
                        student_nim=nim,
                        course_id=cid,
                        session_num=1,
                        post_id=post_id,
                        content=content,
                        score=score,
                        feedback=feedback,
                        status=status,
                    )
        except Exception as e:
            logger.warning(f"Gagal memuat {s1_file}: {e}")

    # Fallback/pelengkap Sesi 1 untuk kelas 413073 jika ada matched_students.json
    matched_file = sessions_dir / "matched_students.json"
    if matched_file.exists():
        try:
            with open(matched_file, "r", encoding="utf-8") as f:
                matched_data = json.load(f)
            for st in matched_data:
                nim = str(st.get("nim", "")).strip()
                if not nim:
                    continue
                name = clean_student_name(st.get("name") or st.get("student_name") or f"Mahasiswa {nim}")
                post_id = st.get("postId") or st.get("post_id")
                content = st.get("content")
                raw_score = st.get("score")
                score = int(raw_score) if raw_score is not None and str(raw_score).isdigit() else None
                feedback = st.get("feedback")
                status = "completed"

                db.upsert_student(nim=nim, name=name, course_id="413073")
                db.upsert_submission(
                    student_nim=nim,
                    course_id="413073",
                    session_num=1,
                    post_id=post_id,
                    content=content,
                    score=score,
                    feedback=feedback,
                    status=status,
                )
        except Exception as e:
            logger.warning(f"Gagal memuat {matched_file}: {e}")

    # 2. Impor Sesi 2 dari sesi2_raw_scraped.json
    s2_file = sessions_dir / "sesi2_raw_scraped.json"
    if s2_file.exists():
        try:
            with open(s2_file, "r", encoding="utf-8") as f:
                s2_data = json.load(f)
            for cid_key, cdata in s2_data.items():
                cid = resolve_course_id(cid_key) or str(cid_key)
                analysis = cdata.get("analysis", {})
                students = analysis.get("students", [])
                for st in students:
                    nim = str(st.get("nim", "")).strip()
                    if not nim:
                        continue
                    name = clean_student_name(st.get("name") or st.get("student_name") or f"Mahasiswa {nim}")
                    post_id = st.get("postId") or st.get("post_id")
                    content = st.get("content")
                    raw_score = st.get("score")
                    score = int(raw_score) if raw_score is not None and str(raw_score).isdigit() else None
                    feedback = st.get("feedback")
                    status = "completed" if score is not None else "pending"

                    db.upsert_student(nim=nim, name=name, course_id=cid)
                    db.upsert_submission(
                        student_nim=nim,
                        course_id=cid,
                        session_num=2,
                        post_id=post_id,
                        content=content,
                        score=score,
                        feedback=feedback,
                        status=status,
                    )
        except Exception as e:
            logger.warning(f"Gagal memuat {s2_file}: {e}")

    # Pelengkap Sesi 2 dari sesi2_evaluated_ready.json
    s2_ready_file = sessions_dir / "sesi2_evaluated_ready.json"
    if s2_ready_file.exists():
        try:
            with open(s2_ready_file, "r", encoding="utf-8") as f:
                s2_ready_data = json.load(f)
            for cid_key, cdata in s2_ready_data.items():
                cid = resolve_course_id(cid_key) or str(cid_key)
                students = cdata.get("students", [])
                for st in students:
                    nim = str(st.get("nim", "")).strip()
                    if not nim:
                        continue
                    raw_name = st.get("student_name") or st.get("name")
                    name = clean_student_name(raw_name) if raw_name else f"Mahasiswa {nim}"
                    post_id = st.get("postId") or st.get("post_id")
                    raw_score = st.get("score")
                    score = int(raw_score) if raw_score is not None and str(raw_score).isdigit() else None
                    feedback = st.get("feedback")
                    status = "completed" if score is not None else "pending"

                    if raw_name:
                        db.upsert_student(nim=nim, name=name, course_id=cid)
                    db.upsert_submission(
                        student_nim=nim,
                        course_id=cid,
                        session_num=2,
                        post_id=post_id,
                        score=score,
                        feedback=feedback,
                        status=status,
                    )
        except Exception as e:
            logger.warning(f"Gagal memuat {s2_ready_file}: {e}")

    # 3. Impor dari laporan markdown (SESI1 s.d. SESI4)
    md_reports = [
        base_path / "SESI1_EVALUATION_REPORT.md",
        base_path / "SESI2_EVALUATION_REPORT.md",
        base_path / "SESI3_EVALUATION_REPORT.md",
        base_path / "SESI4_EVALUATION_REPORT.md",
    ]

    for md_path in md_reports:
        if not md_path.exists():
            continue
        parsed_entries = parse_markdown_report(md_path)
        for item in parsed_entries:
            nim = item["nim"]
            name = item["name"]
            cid = item["course_id"]
            s_num = item["session_num"]
            score = item["score"]
            feedback = item["feedback"]
            status = item["status"]

            db.upsert_student(nim=nim, name=name, course_id=cid)
            db.upsert_submission(
                student_nim=nim,
                course_id=cid,
                session_num=s_num,
                score=score,
                feedback=feedback,
                status=status,
            )

    all_students = db.get_students()
    all_subs = db.get_submissions()

    return {
        "total_students": len(all_students),
        "total_submissions": len(all_subs),
        "by_session": {
            s: len(db.get_submissions(session_num=s))
            for s in range(1, 9)
        },
    }


if __name__ == "__main__":
    db = get_db()
    db.init_db()
    print("Memulai proses seeding data historis ke SQLite database...")
    summary = seed_from_markdown_reports(db)
    print("Seeding berhasil diselesaikan!")
    print(f"Total mahasiswa terdaftar: {summary['total_students']}")
    print(f"Total submission tersimpan: {summary['total_submissions']}")
    for s_num in range(1, 9):
        cnt = summary["by_session"].get(s_num, 0)
        if cnt > 0:
            print(f"  - Sesi {s_num}: {cnt} pengumpulan")
