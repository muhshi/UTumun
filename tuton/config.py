import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SESSION_FILE = str(BASE_DIR / ".auth" / "session.json")
DATA_DIR = str(BASE_DIR / "data")
CHROME_PATH = os.getenv("CHROME_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

UT_USERNAME = os.getenv("UT_USERNAME", "")
UT_PASSWORD = os.getenv("UT_PASSWORD", "")

TUTOR_NAME = "AINUR ROSYIDAH AZMIE PUTRY"
TUTOR_ID = "01007726"

# Database Configuration (Mendukung SQLite lokal dan MySQL server)
DB_ENGINE = os.getenv("DB_ENGINE", "sqlite").lower()
MYSQL_HOST = os.getenv("MYSQL_HOST", "10.133.21.24")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "demak3321")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "muhshi_utumun")

COURSES = [
    {
        "id": "413073",
        "code": "MKWN4108.2137",
        "name": "Bahasa Indonesia 2137",
        "forums": {
            1: {"cmid": "47302993", "name": "Forum Diskusi.1"},
            2: {"cmid": "47303004", "name": "Forum Diskusi.2"},
            4: {"cmid": "47303026", "name": "Forum Diskusi.4"},
        },
        "assignments": {
            3: {"cmid": "47303015", "name": "Tugas.1"},
        }
    },
    {
        "id": "413077",
        "code": "MKWN4108.2141",
        "name": "Bahasa Indonesia 2141",
        "forums": {
            1: {"cmid": "47303711", "name": "Forum Diskusi.1"},
            2: {"cmid": "47303722", "name": "Forum Diskusi.2"},
            4: {"cmid": "47303744", "name": "Forum Diskusi.4"},
        },
        "assignments": {
            3: {"cmid": "47303733", "name": "Tugas.1"},
        }
    },
    {
        "id": "413081",
        "code": "MKWN4108.2145",
        "name": "Bahasa Indonesia 2145",
        "forums": {
            1: {"cmid": "47304429", "name": "Forum Diskusi.1"},
            2: {"cmid": "47304452", "name": "Forum Diskusi.2"},
            4: {"cmid": "47304490", "name": "Forum Diskusi.4"},
        },
        "assignments": {
            3: {"cmid": "47304472", "name": "Tugas.1"},
        }
    },
    {
        "id": "411401",
        "code": "MKWN4108.465",
        "name": "Bahasa Indonesia 465",
        "forums": {
            1: {"cmid": "46978721", "name": "Forum Diskusi.1"},
            2: {"cmid": "46978750", "name": "Forum Diskusi.2"},
            4: {"cmid": "46978799", "name": "Forum Diskusi.4"},
        },
        "assignments": {
            3: {"cmid": "46978783", "name": "Tugas.1"},
        }
    }
]

def get_course_info(course_id: str):
    for c in COURSES:
        if c["id"] == str(course_id):
            return c
    return None

def get_forum_cmid(course_id: str, session_num: int):
    c = get_course_info(course_id)
    if not c:
        return None
    forum = c.get("forums", {}).get(int(session_num))
    return forum["cmid"] if forum else None

def get_assign_cmid(course_id: str, session_num: int):
    c = get_course_info(course_id)
    if not c:
        return None
    assign = c.get("assignments", {}).get(int(session_num))
    return assign["cmid"] if assign else None
