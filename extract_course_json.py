import json
import re

with open("/Users/saiful/.gemini/antigravity/brain/2396782e-81f5-4b17-bd69-54511ecd34b4/.system_generated/logs/transcript_full.jsonl") as f:
    for idx, line in enumerate(f):
        if idx in [7, 8, 9, 10]:
            try:
                data = json.loads(line)
                content = data.get("content", "")
                if "Forum Diskusi" in content or "413073" in content:
                    print(f"Found match on line {idx+1} (step {data.get('step_index')})")
                    # Find all course modules or forum IDs mentioned
                    forums = re.findall(r'(\{"id":\s*"\d+".*?Forum Diskusi\.1.*?\})', content)
                    print(f"Direct forum matches: {len(forums)}")
                    for m in forums:
                        print("  Forum match:", m[:200])
                    
                    # Also look for mod_forum view.php?id=(\d+)
                    forum_urls = re.findall(r'https:[^"]*mod[^"]*forum[^"]*view\.php\?id=\d+', content)
                    print("Unique forum URLs found:", set(forum_urls))
            except Exception as e:
                print(f"Error parsing line {idx+1}: {e}")
