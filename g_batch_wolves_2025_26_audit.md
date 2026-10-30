# G批：Wolves Premier League official source graduation audit

- 目標：1隊
- 成功 Full：0隊
- 原有 tier1：50隊
- 最終 tier1：50隊
- Wolves：tier0，沒有新增球員或教練
- players.csv：1,319人
- coaches.csv：50隊
- teams.csv：252隊，唯一252
- 假隊：0
- Al Ahli / Al Hilal 模糊匹配：PASS
- Streamlit 8501：待驗證

## 誠實原因

blocked: no reliable way was found to close every eligible 2025/26 first-team player with name, position, shirt_number, nationality, season=2025/26, at least two public URLs, and at least one official URL. The official Premier League historical list is names-only in accessible content, while the Wolves team page is not archived to 2025/26; therefore no player records are emitted and no guesses are made.

官方來源已核查：
- https://www.premierleague.com/en/news/4580687/202526-premier-league-squad-lists
- https://www.premierleague.com/en/clubs/39/wolverhampton-wanderers/squad
- https://www.wolves.co.uk/teams/mens-first-team/
- https://www.wolves.co.uk/news/mens-first-team/20251007-the-official-202526-squad-photo/
- https://www.transfermarkt.us/wolverhampton-wanderers/kader/verein/543/saison_id/2025
- https://www.bbc.com/sport/football/articles/crm4xdzekmxo

沒有把不完整背號名單寫入資料庫。
