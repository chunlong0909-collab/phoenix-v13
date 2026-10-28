# Phoenix 最終封存審計報告（2025/26）

## 結論

已將最終封存檔限制為 8 隊已核實德甲 Full 名冊，共 207 名球員。每名球員均保留 `season=2025/26`、Transfermarkt、FBref、官方來源及 `source_urls`。其餘 241 隊只保留目錄，不放入封存名冊。

## 封存統計

- `teams.csv` 總隊數：249
- `teams.csv` 唯一隊名：249
- `tier=1` Full 隊：8
- `tier=0` 非 Full／目錄隊：241
- 封存球員：207
- 封存教練：8
- 假隊：0
- 虛構球員：0
- 跨賽季混入：0
- `season`：全部為 2025/26

## 8 隊 Full 清單

- Augsburg (Ger)：34 名球員；教練：Sandro Wagner (2025-07-01 to 2025-12-01); Manuel Baum (from 2025-12-01 through 2025/26)
- Bayer Leverkusen (Ger)：23 名球員；教練：Erik ten Hag (2025-07-01 to 2025-09-01); Kasper Hjulmand (2025-09-08 to 2026-06-30)
- Eintracht Frankfurt (Ger)：30 名球員；教練：Dino Toppmöller (until 2026-01-18); Albert Riera (from 2026-01-30)
- Freiburg (Ger)：22 名球員；教練：Julian Schuster
- Heidenheim (Ger)：31 名球員；教練：Frank Schmidt
- Mainz 05 (Ger)：28 名球員；教練：Bo Henriksen (至2025-12-03)；Benjamin Hoffmann（其后）
- RB Leipzig (Ger)：22 名球員；教練：Ole Werner
- Wolfsburg (Ger)：17 名球員；教練：Paul Simonis

## 保留為 tier=0 的原因

所有未列入封存的隊伍都只保留官方／真實隊名目錄，不加入球員或教練。未能完成 2025/26 Transfermarkt、FBref、官方三源逐人核對的隊伍，統一標為非 Full；不以 2026/27 現役頁面回填。

### 德甲剩餘10隊
Bayern Munich (Ger)、Borussia Dortmund (Ger)、VfB Stuttgart (Ger)、Hoffenheim (Ger)、Union Berlin (Ger)、Borussia Monchengladbach (Ger)、Werder Bremen (Ger)、Hamburg (Ger)、Cologne (Ger)、St. Pauli (Ger)

### 法甲18隊
Angers (Fra)、Auxerre (Fra)、Monaco (Fra)、Brest (Fra)、Lorient (Fra)、Le Havre (Fra)、Lille (Fra)、Nice (Fra)、Lyon (Fra)、Marseille (Fra)、Paris FC (Fra)、PSG (Fra)、Lens (Fra)、Rennes (Fra)、Strasbourg (Fra)、Toulouse (Fra)、Metz (Fra)、Nantes (Fra)

### 西甲20隊
Athletic Club (Esp)、Atletico Madrid (Esp)、CA Osasuna (Esp)、Celta (Esp)、Deportivo Alaves (Esp)、Elche CF (Esp)、Barcelona (Esp)、Getafe CF (Esp)、Levante UD (Esp)、Malaga CF (Esp)、Racing Santander (Esp)、Rayo Vallecano (Esp)、Deportivo La Coruna (Esp)、Espanyol (Esp)、Real Betis (Esp)、Real Madrid (Esp)、Real Sociedad (Esp)、Sevilla (Esp)、Valencia CF (Esp)、Villarreal CF (Esp)

### 意甲20隊
AC Milan (Ita)、Atalanta (Ita)、Bologna (Ita)、Cagliari (Ita)、Como (Ita)、Fiorentina (Ita)、Frosinone (Ita)、Genoa (Ita)、Inter Milan (Ita)、Juventus (Ita)、Lazio (Ita)、Lecce (Ita)、Monza (Ita)、Napoli (Ita)、Parma (Ita)、Roma (Ita)、Sassuolo (Ita)、Torino (Ita)、Udinese (Ita)、Venezia (Ita)

## 完整性保證

封存腳本只從已驗收的 `players.csv` 與 `coaches.csv` 生成；不重新抓取、不估算、不改寫球員或教練資料。原封存大檔已在本地保留為 `final_574_squads_with_sources.pre_archive_2026-10-29.json`。
