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

COURSES = [
    {
        "id": "413073",
        "code": "MKWN4108.2137",
        "name": "Bahasa Indonesia 2137",
        "forums": {
            1: {"cmid": "47302993", "name": "Forum Diskusi.1"},
            2: {"cmid": "47303004", "name": "Forum Diskusi.2"},
        }
    },
    {
        "id": "413077",
        "code": "MKWN4108.2141",
        "name": "Bahasa Indonesia 2141",
        "forums": {
            1: {"cmid": "47303711", "name": "Forum Diskusi.1"},
            2: {"cmid": "47303722", "name": "Forum Diskusi.2"},
        }
    },
    {
        "id": "413081",
        "code": "MKWN4108.2145",
        "name": "Bahasa Indonesia 2145",
        "forums": {
            1: {"cmid": "47304429", "name": "Forum Diskusi.1"},
            2: {"cmid": "47304452", "name": "Forum Diskusi.2"},
        }
    },
    {
        "id": "411401",
        "code": "MKWN4108.465",
        "name": "Bahasa Indonesia 465",
        "forums": {
            1: {"cmid": "46978721", "name": "Forum Diskusi.1"},
            2: {"cmid": "46978750", "name": "Forum Diskusi.2"},
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
