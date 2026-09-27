import json
import requests

with open(".auth/session.json") as f:
    session_data = json.load(f)

cookies = {}
for c in session_data.get("cookies", []):
    cookies[c["name"]] = c["value"]

url = "https://elearning.ut.ac.id/mod/resource/view.php?id=47303005"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

res = requests.get(url, cookies=cookies, headers=headers, allow_redirects=True)
print("Status Code:", res.status_code)
print("Content-Type:", res.headers.get("Content-Type"))
print("Content-Disposition:", res.headers.get("Content-Disposition"))
print("Final URL:", res.url)

# Save file
filename = "rambu_diskusi_2.docx"
if "filename=" in str(res.headers.get("Content-Disposition")):
    import re
    m = re.search(r'filename="?([^";]+)"?', res.headers.get("Content-Disposition"))
    if m:
        filename = m.group(1)

with open(f"data/{filename}", "wb") as f:
    f.write(res.content)

print(f"Saved {len(res.content)} bytes to data/{filename}")
