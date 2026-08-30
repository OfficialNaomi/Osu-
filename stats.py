import requests
import json
import subprocess
import os
from dotenv import load_dotenv

# Lade die versteckten Keys aus der .env Datei
load_dotenv()

# --- CONFIGURATION (Sicher aus .env geladen) ---
CLIENT_ID = os.getenv('OSU_CLIENT_ID')
CLIENT_SECRET = os.getenv('OSU_CLIENT_SECRET')
USER_ID = os.getenv('OSU_USER_ID')
FILE_PATH = '1star/sidequest.md' # Pfad anpassen, falls nötig
# ---------------------

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
    response.raise_for_status() # Wenn hier wieder 401 kommt, check deine .env Datei!
    return response.json()['access_token']

# ... (Ab hier kommt genau der gleiche Code wie vorher: get_top_ss_plays, update_markdown_file, etc.)

def get_top_ss_plays(token):
    print(f"📡 Fetching RECENT scores for user {USER_ID}...")
    headers = {'Authorization': f'Bearer {token}'}
    # HIER GEÄNDERT: 'recent' statt 'best' und 'include_fails=0' (damit er keine Fails zieht)
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

def update_markdown_file(plays):
    print(f"✨ Found {len(plays)} SS ranks! Updating {FILE_PATH}...")
    
    if len(plays) == 0:
        print("Keine SS Ranks gefunden. Beende das Update.")
        return

    # Ordner erstellen, falls das Skript von woanders ausgeführt wird
    os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)
    
    # Hier generieren wir den Text-Block für die Maps
    new_content = ""
    for play in plays:
        new_content += f"*   **[{play['title']}]({play['link']})**\n"
        new_content += f"    *   **Stats:** {play['stars']}★ | {play['bpm']} BPM | {play['length']} Length | AR{play['ar']} | OD{play['od']}\n"
        new_content += f"    *   **Status:** **SS ACHIEVED!** 🥇\n"
        new_content += f"    *   **Naomi's Verdict:** *Verdict pending...*\n"
    
    # Lies die alte Datei (oder erstelle sie, falls leer)
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = "## 🔍 Pre-Scouting & Active Targets\n*All mapped data points are currently held here for calibration before final sorting.*\n\n"

    # Füge die neuen Maps an der richtigen Stelle ein (simples Replace für dieses Setup)
    injection_point = r"(\*All mapped data points are currently held here for calibration before final sorting\.\*\n\n)"
    import re
    if re.search(injection_point, content):
        content = re.sub(injection_point, rf"\1{new_content}", content)
    else:
        content += "\n" + new_content

    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Markdown file updated locally.")

def git_commit_and_push():
    print("🚀 Uploading to GitHub...")
    try:
        # HIER GEÄNDERT: shell=True für Windows-Kompatibilität, Befehle als Strings
        subprocess.run(f'git add "{FILE_PATH}"', check=True, shell=True)
        subprocess.run('git commit -m "Auto-update: Synced recent SS ranks from osu! API"', check=True, shell=True)
        subprocess.run('git push', check=True, shell=True)
        print("✅ Successfully pushed to GitHub! Real lazy automation complete.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git failed! Stelle sicher, dass Git installiert ist und du im richtigen Ordner bist.")

if __name__ == "__main__":
    try:
        token = get_token()
        ss_plays = get_top_ss_plays(token)
        
        # HIER GEÄNDERT: Wir stoppen, wenn 0 Maps gefunden wurden!
        if len(ss_plays) == 0:
            print("🛑 Kein Update nötig, breche ab bevor Git gestartet wird.")
        else:
            ss_plays.sort(key=lambda x: x['stars'])
            update_markdown_file(ss_plays)
            git_commit_and_push()
            
    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    try:
        # 1. API Token holen
        token = get_token()
        # 2. Maps von osu! ziehen
        ss_plays = get_top_ss_plays(token)
        # 3. Sortieren nach Sternen
        ss_plays.sort(key=lambda x: x['stars'])
        # 4. In die Markdown Datei schreiben
        update_markdown_file(ss_plays)
        # 5. Zu GitHub pushen
        git_commit_and_push()
        
    except Exception as e:
        print(f"❌ An error occurred: {e}")