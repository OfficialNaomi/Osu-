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

def get_user_stats(token):
    print(f"📊 Fetching exact SS counts from profile...")
    headers = {'Authorization': f'Bearer {token}'}
    # Zieht die kompletten User-Statistiken
    url = f'https://osu.ppy.sh/api/v2/users/{USER_ID}/osu'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    data = response.json()
    ss_count = data['statistics']['grade_counts']['ss']   # Gold SS
    ssh_count = data['statistics']['grade_counts']['ssh'] # Silber SS (Silver SS)
    total_mastered = ss_count + ssh_count
    
    print(f"   -> Online Stats: {ss_count} Gold SS | {ssh_count} Silver SS | {total_mastered} Total")
    return ss_count, total_mastered

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

def update_markdown_file(plays, ss_count, total_mastered):
    os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)
    
    # 1. Alte Datei laden
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = "## 🔍 Pre-Scouting & Active Targets\n*All mapped data points are currently held here for calibration before final sorting.*\n\n"

    original_content = content

    # 2. Zähler IMMER mit den echten Live-Zahlen überschreiben
    content = re.sub(
        r'(\*\s+\*\*Current Gold SS:\*\*\s+)\d+', 
        rf'\g<1>{ss_count}', 
        content
    )
    content = re.sub(
        r'(\*\s+\*\*Total Mastered Maps:\*\*\s+)\d+', 
        rf'\g<1>{total_mastered}', 
        content
    )

    # 3. Neue Maps filtern
    new_plays = []
    seen_links = set()
    
    for play in plays:
        if play['link'] not in content and play['link'] not in seen_links:
            new_plays.append(play)
            seen_links.add(play['link'])

    if new_plays:
        print(f"✨ Found {len(new_plays)} BRAND NEW SS ranks for the list!")
        # Text-Block generieren
        new_content = ""
        for play in new_plays:
            new_content += f"*   **[{play['title']}]({play['link']})**\n"
            new_content += f"    *   **Stats:** {play['stars']}★ | {play['bpm']} BPM | {play['length']} Length | AR{play['ar']} | OD{play['od']}\n"
            new_content += f"    *   **Status:** **SS ACHIEVED!** 🥇\n"
            new_content += f"    *   **Naomi's Verdict:** *Verdict pending...*\n"
        
        # Maps einfügen
        injection_point = r"(\*All mapped data points are currently held here for calibration before final sorting\.\*\n\n)"
        if re.search(injection_point, content):
            content = re.sub(injection_point, rf"\1{new_content}", content)
        else:
            content += "\n" + new_content
    else:
        print("ℹ️ Keine neuen Maps für die Liste gefunden.")

    # 4. Prüfen, ob sich ÜBERHAUPT etwas geändert hat (Maps oder Zahlen)
    if content != original_content:
        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Markdown file updated locally (Stats and/or Maps synced)!")
        return True # Es gab Änderungen, Git soll hochladen
    else:
        print("🛑 Nichts zu tun! Zahlen sind aktuell und keine neuen Maps.")
        return False # Keine Änderungen

def git_commit_and_push():
    print("\n🚀 Uploading to GitHub...")
    try:
        subprocess.run(["git", "add", FILE_PATH], check=True)
        subprocess.run(["git", "commit", "-m", "Auto-update: Synced Live SS Stats and recent maps"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Successfully pushed to GitHub! Real lazy automation complete.")
    except FileNotFoundError:
        print("\n❌ FEHLER: Windows kennt den Befehl 'git' nicht!")
        print("💡 Lösung: Starte dieses Skript in 'Git Bash' oder im Terminal von VS Code.")
    except subprocess.CalledProcessError:
        print(f"\n❌ Git failed! (Oder es gab schlicht nichts Neues zum Committen).")

if __name__ == "__main__":
    try:
        token = get_token()
        
        # Hol erst die exakten Account-Stats
        ss_count, total_mastered = get_user_stats(token)
        
        # Hol dann die Recent Plays
        ss_plays = get_top_ss_plays(token)
        ss_plays.sort(key=lambda x: x['stars'])
        
        # Update die Datei und gib True zurück, wenn sich was geändert hat
        has_changes = update_markdown_file(ss_plays, ss_count, total_mastered)
        
        # Git Upload NUR ausführen, wenn die Datei wirklich verändert wurde
        if has_changes:
            git_commit_and_push()
            
    except Exception as e:
        print(f"❌ An error occurred: {e}")