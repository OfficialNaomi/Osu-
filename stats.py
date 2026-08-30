import requests
import os
import re
import subprocess
from dotenv import load_dotenv

# Lade die versteckten Keys aus der .env Datei
load_dotenv()

CLIENT_ID = os.getenv('OSU_CLIENT_ID')
CLIENT_SECRET = os.getenv('OSU_CLIENT_SECRET')
USER_ID = os.getenv('OSU_USER_ID')
FILE_PATH = '1star/sidequest.md' 

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

def get_top_ss_plays(token):
    print(f"📡 Fetching RECENT scores for user {USER_ID}...")
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

def update_markdown_file(plays):
    if len(plays) == 0:
        print("🛑 Keine SS Ranks in der Recent-Historie gefunden.")
        return 0 # Gibt 0 zurück, damit Git weiß, dass nichts zu tun ist

    os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)
    
    # 1. Alte Datei laden
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = "## 🔍 Pre-Scouting & Active Targets\n*All mapped data points are currently held here for calibration before final sorting.*\n\n"

    # 2. Duplikate filtern
    new_plays = []
    seen_links = set()
    
    for play in plays:
        if play['link'] not in content and play['link'] not in seen_links:
            new_plays.append(play)
            seen_links.add(play['link'])

    if not new_plays:
        print("🛑 Alle gefundenen SS Ranks stehen bereits im Log. Nichts Neues hinzuzufügen.")
        return 0

    print(f"✨ Found {len(new_plays)} BRAND NEW SS ranks! Updating {FILE_PATH}...")

    # 3. Zähler automatisch hochsetzen
    content = re.sub(
        r'(\*\s+\*\*Current Gold SS:\*\*\s+)(\d+)', 
        lambda m: f"{m.group(1)}{int(m.group(2)) + len(new_plays)}", 
        content
    )
    content = re.sub(
        r'(\*\s+\*\*Total Mastered Maps:\*\*\s+)(\d+)', 
        lambda m: f"{m.group(1)}{int(m.group(2)) + len(new_plays)}", 
        content
    )

    # 4. Text-Block generieren
    new_content = ""
    for play in new_plays:
        new_content += f"*   **[{play['title']}]({play['link']})**\n"
        new_content += f"    *   **Stats:** {play['stars']}★ | {play['bpm']} BPM | {play['length']} Length | AR{play['ar']} | OD{play['od']}\n"
        new_content += f"    *   **Status:** **SS ACHIEVED!** 🥇\n"
        new_content += f"    *   **Naomi's Verdict:** *Verdict pending...*\n"
    
    # 5. Maps einfügen
    injection_point = r"(\*All mapped data points are currently held here for calibration before final sorting\.\*\n\n)"
    if re.search(injection_point, content):
        content = re.sub(injection_point, rf"\1{new_content}", content)
    else:
        content += "\n" + new_content

    # 6. Speichern
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Markdown file updated locally! Counter increased by {len(new_plays)}.")
    return len(new_plays) # Gibt die Anzahl der neuen Maps zurück

def git_commit_and_push(added_count):
    print("\n🚀 Uploading to GitHub...")
    try:
        # Führe Git-Befehle aus (als Liste, das ist sicherer)
        subprocess.run(["git", "add", FILE_PATH], check=True)
        commit_msg = f"Auto-update: Added {added_count} new SS ranks from osu! API"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Successfully pushed to GitHub! Real lazy automation complete.")
    except FileNotFoundError:
        print("\n❌ FEHLER: Windows kennt den Befehl 'git' nicht!")
        print("💡 Lösung: Starte dieses Skript in 'Git Bash' oder im Terminal von VS Code.")
        print("   Alternativ: Installiere Git neu und setze den Haken bei 'Add to PATH'.")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Git failed! (Vielleicht gibt es nichts zu committen oder du hast keine Push-Rechte).")

if __name__ == "__main__":
    try:
        token = get_token()
        ss_plays = get_top_ss_plays(token)
        ss_plays.sort(key=lambda x: x['stars'])
        
        # update_markdown_file gibt jetzt die Anzahl der NEUEN Maps zurück
        new_maps_count = update_markdown_file(ss_plays)
        
        # Git Upload wird NUR ausgeführt, wenn es auch neue Maps gab!
        if new_maps_count > 0:
            git_commit_and_push(new_maps_count)
            
    except Exception as e:
        print(f"❌ An error occurred: {e}")