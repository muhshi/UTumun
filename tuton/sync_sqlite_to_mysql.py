#!/usr/bin/env python3
"""Skrip utilitas untuk menyinkronkan seluruh data dari SQLite lokal ke MySQL server."""

import sys
from tuton.db import Database
from tuton.mysql_db import MySQLDatabase


def sync_sqlite_to_mysql(sqlite_path: str = "data/tuton.db"):
    print(f"[1/4] Membuka SQLite dari {sqlite_path}...")
    sqlite_db = Database(sqlite_path)
    
    print("[2/4] Menghubungkan ke MySQL & menginisialisasi skema tabel...")
    mysql_db = MySQLDatabase()
    mysql_db.init_db()

    # 1. Sync students
    students = sqlite_db.get_students()
    print(f"[3/4] Menyinkronkan {len(students)} data mahasiswa ke MySQL...")
    with mysql_db.get_connection() as conn:
        with conn.cursor() as cur:
            for st in students:
                cur.execute("""
                    INSERT INTO students (nim, name, course_id)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE name = VALUES(name)
                """, (st["nim"], st["name"], st["course_id"]))

    # 2. Sync submissions
    submissions = sqlite_db.get_submissions()
    print(f"[4/4] Menyinkronkan {len(submissions)} pengumpulan tugas/diskusi ke MySQL...")
    with mysql_db.get_connection() as conn:
        with conn.cursor() as cur:
            for sub in submissions:
                cur.execute("""
                    INSERT INTO submissions (
                        student_nim, course_id, session_num, post_id, content,
                        score, original_score, feedback, is_copied, is_grade_copied,
                        status, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        post_id = VALUES(post_id),
                        content = VALUES(content),
                        score = VALUES(score),
                        original_score = VALUES(original_score),
                        feedback = VALUES(feedback),
                        is_copied = VALUES(is_copied),
                        is_grade_copied = VALUES(is_grade_copied),
                        status = VALUES(status),
                        updated_at = VALUES(updated_at)
                """, (
                    sub["student_nim"], sub["course_id"], sub["session_num"],
                    sub.get("post_id"), sub.get("content"), sub.get("score"),
                    sub.get("original_score"), sub.get("feedback"),
                    sub.get("is_copied", 0), sub.get("is_grade_copied", 0),
                    sub.get("status", "draft"), sub.get("updated_at")
                ))

    print("[✓] Sinkronisasi data ke MySQL BERHASIL!")
    metrics = mysql_db.get_recap_metrics()
    print(f"[✓] Verifikasi Metrik MySQL: {metrics['completed']} selesai, {metrics['pending']} pending (Tingkat: {metrics['completion_rate']}%)")


if __name__ == "__main__":
    sync_sqlite_to_mysql()
