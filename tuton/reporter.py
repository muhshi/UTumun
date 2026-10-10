from typing import List, Dict, Any

def format_recap_summary_table(summary_data: List[Dict[str, Any]]) -> str:
    """Menghasilkan tabel Markdown ringkasan status per sesi dan per kelas."""
    lines = [
        "| Sesi | Kelas | Kode Kelas | Total Mhs | Selesai | Kurang (Pending) | Status |",
        "|:---:|---|---|:---:|:---:|:---:|:---:|"
    ]
    for s_item in summary_data:
        s_num = s_item["session"]
        for c in s_item["classes"]:
            status_badge = "✅ Tuntas" if c["pending"] == 0 else f"⚠️ {c['pending']} Butuh Penanganan"
            lines.append(
                f"| Sesi {s_num} | {c['name']} | `{c['code']}` | {c['total']} | {c['completed']} | **{c['pending']}** | {status_badge} |"
            )
    return "\n".join(lines)

def format_pending_names_list(pending_grouped: Dict[str, List[Dict[str, Any]]]) -> str:
    """Menampilkan daftar nama mahasiswa yang masih kurang per kelas dan per sesi."""
    lines = []
    for group_title, students in pending_grouped.items():
        lines.append(f"### {group_title}")
        if not students:
            lines.append("- *(Semua mahasiswa sudah selesai dinilai dan diberi feedback)*\n")
            continue
        for idx, s in enumerate(students, 1):
            curr_score = f" (Nilai saat ini: {s['score']})" if s.get("score") else " (Belum ada nilai)"
            has_fb = "Sudah ada feedback" if s.get("feedback") else "Belum ada feedback"
            lines.append(f"{idx}. **{s['name']}** (NIM: {s.get('nim') or 'N/A'}) — Status: {has_fb}{curr_score}")
        lines.append("")
    return "\n".join(lines)

def format_pending_student_card(s: Dict[str, Any]) -> str:
    """Menghasilkan kotak feedback siap salin dengan blok kode ```text."""
    nim_str = f" (NIM: {s['nim']})" if s.get("nim") else ""
    return (
        f"#### {s['name']}{nim_str} — {s['course_name']} (Sesi {s['session']})\n"
        f"- **Status:** {s['status_desc']}\n"
        f"- **Rekomendasi Nilai:** **{s['score']}**\n"
        f"- **Draf Feedback Siap Salin:**\n"
        f"```text\n"
        f"{s['feedback']}\n"
        f"```\n"
    )
