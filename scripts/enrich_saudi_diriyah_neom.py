from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEAGUE = ROOT / "data" / "leagues" / "saudi-pro"
SPL = "https://www.spl.com.sa/en/teams/{}"
SQUAD = "https://www.spl.com.sa/en/teams/{}/squad"
STANDINGS = "https://www.spl.com.sa/en/standings/index"
SEASON = "2026/27"
CAPTURED = "2026-10-30"

# Every row below was transcribed from the SPL official squad pages. Empty shirt
# numbers remain empty because the official page did not show one.
PLAYERS = [
    ("Diriyah Club (Sau)", "Nikola Vasilj", "GK", "22", "BIH"),
    ("Diriyah Club (Sau)", "Waleed Abdullah", "GK", "33", "KSA"),
    ("Diriyah Club (Sau)", "Mansour Hibatullah Al Sibyani", "GK", "34", "KSA"),
    ("Diriyah Club (Sau)", "Amin Bukhari", "GK", "97", "KSA"),
    ("Diriyah Club (Sau)", "Abdulelah Al Jafari", "DF", "", "KSA"),
    ("Diriyah Club (Sau)", "Mohamed Hameran", "DF", "", "KSA"),
    ("Diriyah Club (Sau)", "Abdulaziz Al Faraj", "DF", "2", "KSA"),
    ("Diriyah Club (Sau)", "Saeed Al Rubaie", "DF", "4", "KSA"),
    ("Diriyah Club (Sau)", "Taher Wadi", "DF", "12", "KSA"),
    ("Diriyah Club (Sau)", "Hussain Al Sibyani", "DF", "16", "KSA"),
    ("Diriyah Club (Sau)", "Berat Djimsiti", "DF", "19", "ALB"),
    ("Diriyah Club (Sau)", "Khalid Asiri", "DF", "78", "KSA"),
    ("Diriyah Club (Sau)", "Qassem Lajami", "DF", "87", "KSA"),
    ("Diriyah Club (Sau)", "Chancel Mbemba", "DF", "99", "COD"),
    ("Diriyah Club (Sau)", "Mathys De Carvalho", "MF", "", "PRT"),
    ("Diriyah Club (Sau)", "Idrissa Gana Gueye", "MF", "5", "SEN"),
    ("Diriyah Club (Sau)", "Sultan Al Farhan", "MF", "6", "KSA"),
    ("Diriyah Club (Sau)", "Oscar Rodriguez", "MF", "14", "ESP"),
    ("Diriyah Club (Sau)", "Enzo Millot", "MF", "20", "FRA"),
    ("Diriyah Club (Sau)", "Husain Al Qahtani", "MF", "52", "KSA"),
    ("Diriyah Club (Sau)", "Abdulelah Al Malki", "MF", "88", "KSA"),
    ("Diriyah Club (Sau)", "Gaetan Laborde", "FW", "9", "FRA"),
    ("Diriyah Club (Sau)", "Adil Boulbina", "FW", "10", "ALG"),
    ("Diriyah Club (Sau)", "Hattan Bahebri", "FW", "11", "KSA"),
    ("Diriyah Club (Sau)", "Clayton Diandy", "FW", "17", "SEN"),
    ("Diriyah Club (Sau)", "Lovro Chelfi", "FW", "25", "HRV"),
    ("Diriyah Club (Sau)", "Darwin Nunez", "FW", "29", "URY"),
    ("Diriyah Club (Sau)", "Abdullah Al Zaid", "FW", "32", "KSA"),
    ("Diriyah Club (Sau)", "Meshari Al Nemr", "FW", "75", "KSA"),
    ("NEOM (Sau)", "Marcin Bulka", "GK", "1", "POL"),
    ("NEOM (Sau)", "Abdulrahman Dagriri", "GK", "33", "KSA"),
    ("NEOM (Sau)", "Luis Maximiano", "GK", "81", "PRT"),
    ("NEOM (Sau)", "Mohammed Al Burayk", "DF", "2", "KSA"),
    ("NEOM (Sau)", "Khalifa Al Dawsari", "DF", "4", "KSA"),
    ("NEOM (Sau)", "Malang Sarr", "DF", "5", "SEN"),
    ("NEOM (Sau)", "Abdulmalik Al Oyayri", "DF", "15", "KSA"),
    ("NEOM (Sau)", "Mohannad Abu Taha", "DF", "19", "JOR"),
    ("NEOM (Sau)", "Islam Hawsawi", "DF", "27", "KSA"),
    ("NEOM (Sau)", "Nathan Zeze", "DF", "44", "FRA"),
    ("NEOM (Sau)", "Mohammed Waleed", "DF", "55", "KSA"),
    ("NEOM (Sau)", "Khaled Al Rammah", "DF", "75", "KSA"),
    ("NEOM (Sau)", "Abbas Al Hassan", "MF", "6", "KSA"),
    ("NEOM (Sau)", "Faisal Al Ghamdi", "MF", "8", "KSA"),
    ("NEOM (Sau)", "Alaa Al Hejji", "MF", "18", "KSA"),
    ("NEOM (Sau)", "Valentin Vada", "MF", "23", "ARG"),
    ("NEOM (Sau)", "Abdulaziz Noor", "MF", "24", "KSA"),
    ("NEOM (Sau)", "Amadou Kone", "MF", "72", "CIV"),
    ("NEOM (Sau)", "Giorgos Masouras", "FW", "7", "GRC"),
    ("NEOM (Sau)", "Abdulaziz Al Othman", "FW", "9", "KSA"),
    ("NEOM (Sau)", "Said Benrahma", "FW", "10", "ALG"),
    ("NEOM (Sau)", "Khalil Al Absi", "FW", "14", "KSA"),
    ("NEOM (Sau)", "Ahmed Al Enezi", "FW", "22", "KSA"),
    ("NEOM (Sau)", "Haroune Camara", "FW", "70", "KSA"),
    ("NEOM (Sau)", "Muhannad Al Saad", "FW", "77", "KSA"),
    ("NEOM (Sau)", "Alexandre Lacazette", "FW", "91", "FRA"),
]

COACHES = [
    ("Diriyah Club (Sau)", "Bruno Miguel Silva do Nascimento", SPL.format("diriyah")),
    ("NEOM (Sau)", "Christophe Galtier", SPL.format("neom")),
]

STANDINGS = [
    ("NEOM (Sau)", 6, 11, 6, 1, 4, 16, 9, 7, 19),
    ("Diriyah Club (Sau)", 8, 11, 4, 3, 4, 9, 11, -2, 15),
]
STANDINGS_URL = "https://www.spl.com.sa/en/standings/index"


def write_players():
    p = LEAGUE / "players.csv"
    fields = ["team_id", "team_name", "player_id", "player_name", "position", "shirt_number", "date_born", "nationality", "source", "season", "source_url"]
    existing = []
    if p.exists() and p.stat().st_size > 4:
        with p.open(encoding="utf-8-sig", newline="") as f:
            existing = list(csv.DictReader(f))
    keys = {(r.get("team_name", ""), r.get("player_name", "")) for r in existing}
    for team, name, pos, number, nat in PLAYERS:
        if (team, name) in keys:
            continue
        slug = name.lower().replace(" ", "-").replace("'", "")
        official = "diriyah" if team.startswith("Diriyah") else "neom"
        existing.append({"team_id": "diriyah_club_sau" if official == "diriyah" else "neom_sau", "team_name": team, "player_id": slug, "player_name": name, "position": pos, "shirt_number": number, "date_born": "", "nationality": nat, "source": "SPL official squad", "season": SEASON, "source_url": SQUAD.format(official)})
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(existing)


def write_coaches_and_standings():
    with (LEAGUE / "coaches.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(["team_name", "season", "coach_name", "source_urls", "verification_note"])
        for team, coach, url in COACHES:
            w.writerow([team, SEASON, coach, json.dumps([url, url + "/squad"], ensure_ascii=False), "SPL official team page; coach field verified"])
    with (LEAGUE / "standings.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(["team_name", "season", "position", "played", "won", "drawn", "lost", "goals_for", "goals_against", "goal_difference", "points", "source_url", "captured_at"])
        for row in STANDINGS: w.writerow([row[0], SEASON, *row[1:], STANDINGS_URL, CAPTURED])


def write_audit():
    audit = {"captured_at": CAPTURED, "season": SEASON, "source": STANDINGS, "teams": {"Diriyah Club (Sau)": {"coach": "Bruno Miguel Silva do Nascimento", "players": 29, "official_url": SPL.format("diriyah")}, "NEOM (Sau)": {"coach": "Christophe Galtier", "players": 26, "official_url": SPL.format("neom")}}, "standings": STANDINGS, "missing_fields": ["date_born", "player_goals", "assists", "minutes", "injury_status", "corners", "weather"], "no_fabrication": True}
    (LEAGUE / "fb8043_data_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sync_library_metadata():
    db = ROOT / "football_library.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE IF NOT EXISTS coaches (team TEXT, season TEXT, coach TEXT, source TEXT, captured_at TEXT, PRIMARY KEY(team, season))")
    conn.executemany("INSERT OR REPLACE INTO coaches(team, season, coach, source, captured_at) VALUES (?, ?, ?, ?, ?)", [(team, SEASON, coach, url, CAPTURED) for team, coach, url in COACHES])
    for team, name, pos, number, nat in PLAYERS:
        conn.execute("DELETE FROM players_stats WHERE league_id=? AND team=? AND player=? AND date=?", (307, team, name, CAPTURED))
        conn.execute("INSERT INTO players_stats(date, league_id, team, player, position, goals, assists, minutes, injury_status, source) VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, ?)", (CAPTURED, 307, team, name, pos, "SPL official squad; performance stats unavailable"))
    conn.commit(); conn.close()


if __name__ == "__main__":
    write_players(); write_coaches_and_standings(); write_audit(); sync_library_metadata(); print("ENRICHED", len(PLAYERS), "players", "2 coaches", "2 standings")
