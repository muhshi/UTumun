import pytest
from tuton.scraper import build_flat_topic_url, parse_post_author_and_nim

def test_build_flat_topic_url():
    url_with_hash = "https://elearning.ut.ac.id/mod/forum/discuss.php?d=11190918#p122494901"
    assert build_flat_topic_url(url_with_hash) == "https://elearning.ut.ac.id/mod/forum/discuss.php?d=11190918&mode=1"

    url_plain = "https://elearning.ut.ac.id/mod/forum/discuss.php?d=12345"
    assert build_flat_topic_url(url_plain) == "https://elearning.ut.ac.id/mod/forum/discuss.php?d=12345&mode=1"

def test_parse_post_author_and_nim():
    author, nim = parse_post_author_and_nim("Re: Forum Diskusi.1 by 058104929 SAFIRA DIAH", "Halo...")
    assert author == "SAFIRA DIAH"
    assert nim == "058104929"

    author2, nim2 = parse_post_author_and_nim("ROSI ANINDHITA", "NIM: 057625959 dari Prodi Sistem Informasi")
    assert author2 == "ROSI ANINDHITA"
    assert nim2 == "057625959"
