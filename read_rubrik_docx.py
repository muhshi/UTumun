import zipfile
import xml.etree.ElementTree as ET

docx_path = "data/Rubrik Penilaian diskusi 2_2026 rev (1).docx"
with zipfile.ZipFile(docx_path) as z:
    xml_content = z.read("word/document.xml")

root = ET.fromstring(xml_content)
namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

paragraphs = []
for p in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
    texts = [node.text for node in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if node.text]
    if texts:
        paragraphs.append("".join(texts))

print("\n--- OFFICIAL UT RUBRIC CONTENT ---")
print("\n".join(paragraphs))
