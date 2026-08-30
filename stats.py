import requests
import os
import re
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv('OSU_CLIENT_ID')
CLIENT_SECRET = os.getenv('OSU_CLIENT_SECRET')
USER_ID = os.getenv('OSU_USER_ID')

# Absoluter Pfad, damit wir immer die richtige Datei treffen
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(SCRIPT_DIR, '1star', 'sidequest.md')

def get_token():
    print("🔑 Authenticating with osu! API...")
    url = 'https://osu.ppy.sh/oauth/token'
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials',
        'scope': 'public'
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()['access_token']

def get_user_stats(token):
    print(f"📊 Fetching exact SS counts from profile...")
    headers = {'Authorization': f'Bearer {token}'}
    url = f'https://osu.ppy.sh/api/v2/users/{USER_ID}/osu'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    data = response.json()
    ss_count = data['statistics']['grade_counts']['ss']
    ssh_count = data['statistics']['grade_counts']['ssh']
    total_mastered = ss_count + ssh_count
    
    print(f"   -> Online Stats: {ss_count} Gold SS | {ssh_count} Silver SS | {total_mastered} Total")
    
    # JETZT geben wir alle DREI Werte zurück!
    return str(ss_count), str(ssh_count), str(total_mastered)

def get_top_ss_plays(token):
    print(f"📡 Fetching RECENT scores (last 24 hours) for user {USER_ID}...")
    headers = {'Authorization': f'Bearer {token}'}
    url = f'https://osu.ppy.sh/api/v2/users/{USER_ID}/scores/recent?mode=osu&limit=100&include_fails=0'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    plays = response.json()
    ss_plays = []
    
    for play in plays:
        if play['rank'] in ['X', 'XH']:
            bm = play['beatmap']
            bms = play['beatmapset']
            
            length_sec = bm['total_length']
            formatted_length = f"{length_sec // 60}:{length_sec % 60:02d}"
            stars = round(bm['difficulty_rating'], 2)
            
            ss_plays.append({
                'title': f"{bms['artist']} - {bms['title']} [{bm['version']}]",
                'link': f"https://osu.ppy.sh/beatmapsets/{bms['id']}#osu/{bm['id']}",
                'stars': stars,
                'bpm': bm['bpm'],
                'length': formatted_length,
                'ar': bm['ar'],
                'od': bm.get('accuracy', '?')
            })
            
    return ss_plays

def update_markdown_file(plays, ss_count, ssh_count, total_mastered):
    os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)

    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = ""

    if "Current Gold SS:" not in content:
        print("🏗️ Datei ist leer oder fehlerhaft: Generiere das Basis-Layout neu...")
        content = """# 🗺️ Naomi's 1-Star Completionist Sidequest Log 

> "All or nothing."

---

## 📊 The Master Counter
*   **Current Gold SS:** 0
*   **Current Silver SS:** 0
*   **Total Mastered Maps:** 0

---

## 🔍 Pre-Scouting & Active Targets
*All mapped data points are currently held here for calibration before final sorting.*

"""

    # ALLE drei Zähler knallhart überschreiben
    content = re.sub(r'(Current Gold SS:[\*\s]*)(\d+)', rf'\g<1>{ss_count}', content, flags=re.IGNORECASE)
    content = re.sub(r'(Current Silver SS:[\*\s]*)(\d+)', rf'\g<1>{ssh_count}', content, flags=re.IGNORECASE)
    content = re.sub(r'(Total Mastered Maps:[\*\s]*)(\d+)', rf'\g<1>{total_mastered}', content, flags=re.IGNORECASE)

    new_plays = []
    seen_links = set()
    
    for play in plays:
        if play['link'] not in content and play['link'] not in seen_links:
            new_plays.append(play)
            seen_links.add(play['link'])

    if new_plays:
        print(f"✨ Found {len(new_plays)} BRAND NEW SS ranks! Füge sie ein...")
        new_content = ""
        for play in new_plays:
            new_content += f"*   **[{play['title']}]({play['link']})**\n"
            new_content += f"    *   **Stats:** {play['stars']}★ | {play['bpm']} BPM | {play['length']} Length | AR{play['ar']} | OD{play['od']}\n"
            new_content += f"    *   **Status:** **SS ACHIEVED!** 🥇\n"
            new_content += f"    *   **Naomi's Verdict:** *Verdict pending...*\n"
        
        injection_point = r"(\*All mapped data points are currently held here for calibration before final sorting\.\*\s*)"
        if re.search(injection_point, content, flags=re.IGNORECASE):
            content = re.sub(injection_point, rf"\1\n{new_content}", content, flags=re.IGNORECASE)
        else:
            content += "\n\n" + new_content
    else:
        print("ℹ️ Keine neuen Maps in den letzten 24 Stunden gespielt (oder schon eingetragen).")

    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n✅ ERFOLG: Ich habe alles in EXAKT DIESE DATEI geschrieben:")
    print(f"👉 {FILE_PATH} 👈")

if __name__ == "__main__":
    try:
        token = get_token()
        ss_count, ssh_count, total_mastered = get_user_stats(token)
        ss_plays = get_top_ss_plays(token)
        ss_plays.sort(key=lambda x: x['stars'])
        
        update_markdown_file(ss_plays, ss_count, ssh_count, total_mastered)
            
    except Exception as e:
        print(f"❌ An error occurred: {e}")