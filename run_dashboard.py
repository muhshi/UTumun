#!/usr/bin/env python3
"""Script peluncur Web Dashboard Asisten Tutor Online UT.

Menyediakan antarmuka grafis lokal untuk mempermudah evaluasi,
pengecekan trajektori nilai, dan penyalinan feedback mahasiswa MKWN4108.
"""

import argparse
import sys
from pathlib import Path

import uvicorn

import tuton.config as config
from tuton.db import Database, get_db
from tuton.seed_db import seed_from_markdown_reports


def ensure_database_populated(db: Database) -> None:
    """Memeriksa apakah database sudah ada dan memiliki data mahasiswa.
    Jika belum ada atau masih kosong, lakukan seeding otomatis.
    """
    db.init_db()
    students = db.get_students()
    submissions = db.get_submissions()
    if len(students) == 0 or len(submissions) == 0:
        print("[i] Database belum terisi data. Mengimpor data awal secara otomatis...")
        summary = seed_from_markdown_reports(db)
        print(f"[✓] Data awal berhasil dimuat: {summary['total_students']} mahasiswa, {summary['total_submissions']} submission.")

    if hasattr(db, "clean_all_stored_signatures"):
        try:
            cleaned = db.clean_all_stored_signatures()
            if isinstance(cleaned, int) and cleaned > 0:
                print(f"[✓] Berhasil merapikan {cleaned} feedback (menghapus salam/signature asisten yang tidak diinginkan).")
        except Exception:
            pass


def build_parser() -> argparse.ArgumentParser:
    """Membangun argument parser untuk CLI dashboard."""
    parser = argparse.ArgumentParser(
        description="Jalankan Web Dashboard Asisten Tutor Online UT (MKWN4108)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Alamat host server (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port server (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Aktifkan mode auto-reload untuk pengembangan",
    )
    return parser


def print_greeting(host: str, port: int, db_path_str: str = "data/tuton.db") -> None:
    """Menampilkan sambutan ramah untuk Ibu Ainur di terminal."""
    url = f"http://{host}:{port}"
    print("========================================================================")
    print(" SISTEM ASISTEN TUTOR ONLINE UT (MKWN4108 BAHASA INDONESIA)")
    print(" Tutor: Ainur Rosyidah Azmie Putry, S.Pd., M.Pd. (NIP: 01007726)")
    print("========================================================================")
    print(f"[✓] Database terhubung: {db_path_str}")
    print("[✓] Tema Visual: Warm Honey & Sunlight Gold")
    print(f"[✓] Server berjalan di: {url}")
    print("Buka tautan di atas pada Google Chrome untuk memulai evaluasi mahasiswa.")
    print("Tekan Ctrl+C untuk menghentikan server.")


def main(args_list=None):
    parser = build_parser()
    args = parser.parse_args(args_list)

    # Siapkan database dengan graceful fallback
    db = get_db()
    is_fallback = False
    try:
        ensure_database_populated(db)
    except Exception as e:
        if getattr(config, "DB_ENGINE", "sqlite").lower() == "mysql":
            print(f"[!] Gagal terhubung ke MySQL ({e}).")
            print("[!] Beralih otomatis (fallback) ke database SQLite lokal (data/tuton.db)...")
            from tuton.db import Database
            db = Database()
            ensure_database_populated(db)
            is_fallback = True
        else:
            raise

    db_display = "SQLite (data/tuton.db)"
    if getattr(config, "DB_ENGINE", "sqlite").lower() == "mysql" and not is_fallback:
        db_display = f"MySQL ({config.MYSQL_HOST}:{config.MYSQL_PORT}/{config.MYSQL_DATABASE})"
    elif hasattr(db, "db_path") and str(db.db_path) != ":memory:":
        try:
            db_display = f"SQLite ({Path(db.db_path).relative_to(config.BASE_DIR)})"
        except Exception:
            db_display = f"SQLite ({db.db_path})"

    # Sambutan ramah
    print_greeting(args.host, args.port, db_display)

    # Jalankan server FastAPI via uvicorn
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
