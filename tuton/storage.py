import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

STORAGE_DIR = Path(__file__).resolve().parent.parent / "data" / "sessions"

def get_session_storage_path(session_num: int) -> Path:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return STORAGE_DIR / f"session_{session_num}_data.json"

def save_session_data(session_num: int, session_type: str, data: Dict[str, Any]) -> str:
    """Menyimpan data lengkap sesi beserta metadata waktu sinkronisasi ke file JSON lokal."""
    filepath = get_session_storage_path(session_num)
    payload = {
        "session": session_num,
        "type": session_type,
        "last_synced_at": datetime.now().isoformat(),
        "courses": data
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return str(filepath)

def load_session_data(session_num: int) -> Dict[str, Any]:
    """Membaca data cache sesi lokal jika tersedia."""
    filepath = get_session_storage_path(session_num)
    if not filepath.exists():
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
