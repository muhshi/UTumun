import io
import zipfile
import xml.etree.ElementTree as ET
from tuton.file_extractor import extract_text_from_bytes

def test_extract_text_from_plain_text():
    raw = b"Ini adalah naskah tugas mahasiswa."
    text = extract_text_from_bytes("tugas.txt", raw)
    assert "Ini adalah naskah tugas" in text

def test_extract_text_from_docx():
    # Buat minimal docx zip in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        doc_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
            <w:body>
                <w:p><w:r><w:t>Tugas 2 Bahasa Indonesia - M. Daffa</w:t></w:r></w:p>
            </w:body>
        </w:document>"""
        z.writestr("word/document.xml", doc_xml)
    
    extracted = extract_text_from_bytes("tugas.docx", buf.getvalue())
    assert "Tugas 2 Bahasa Indonesia - M. Daffa" in extracted

def test_extract_text_empty_bytes():
    assert extract_text_from_bytes("empty.pdf", b"") == ""
