"""
Utilitas Ekstraksi Berkas Tugas Mahasiswa (.pdf, .docx, .doc, .txt)
Mendukung pembacaan dokumen tugas mahasiswa UT dari memori bytes tanpa perlu menulis ke disk.
"""

import io
import logging
import zipfile
import xml.etree.ElementTree as ET
import pypdf

logger = logging.getLogger("tuton.file_extractor")

def extract_text_from_bytes(filename: str, content_bytes: bytes) -> str:
    """
    Mengekstrak teks isi tugas dari berkas bytes berdasarkan ekstensi file.
    Mendukung format PDF, DOCX, DOC, dan TXT.
    """
    if not content_bytes:
        return ""

    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if ext == "pdf":
        try:
            reader = pypdf.PdfReader(io.BytesIO(content_bytes))
            texts = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    texts.append(t)
            return "\n".join(texts).strip()
        except Exception as e:
            logger.warning(f"Gagal mengekstrak PDF {filename}: {e}")
            return ""

    elif ext in ["docx", "doc"]:
        try:
            # DOCX merupakan arsip zip yang berisi word/document.xml
            with zipfile.ZipFile(io.BytesIO(content_bytes)) as z:
                xml_content = z.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                texts = []
                for node in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"):
                    if node.text:
                        texts.append(node.text)
                return " ".join(texts).strip()
        except Exception as e:
            logger.warning(f"Gagal mengekstrak DOCX/DOC {filename}: {e}")
            # Fallback jika plain text
            try:
                return content_bytes.decode("utf-8", errors="ignore").strip()
            except Exception:
                return ""

    elif ext in ["txt", "rtf", "html", "htm"]:
        try:
            return content_bytes.decode("utf-8", errors="ignore").strip()
        except Exception:
            return ""

    else:
        # Percobaan decoding biner umum
        try:
            return content_bytes.decode("utf-8", errors="ignore").strip()
        except Exception:
            return ""
