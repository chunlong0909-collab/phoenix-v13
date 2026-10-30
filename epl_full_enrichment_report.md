# 英超 20 隊 Full 版升級報告

## 範圍

本次把 AFC Champions League Elite 目錄內的 20 隊英超記錄由 `tier2 / directory_only` 升級為 `tier=full`。原有 574 主檔及既有跨聯賽記錄沒有覆蓋；新增資料以 `AFC-ENG-*` 作為 AFC 專用 scope，避免把英超既有歷史樣本重複覆蓋。

## 官方來源

- 英超 2026/27 官方 20 隊 squad-number 名單：<https://www.premierleague.com/en/news/4725682/all-20-premier-league-clubs-squad-numbers-for-202627>
- 球會及經理來源：Premier League 官方球會／經理頁；Liverpool 使用 Liverpool FC 官方經理頁；Nottingham Forest 使用球會官方任命公告。

## 驗收統計

| 項目 | 結果 |
|---|---:|
| AFC CSV 總隊數 | 173 |
| Full 英超隊數 | 20 |
| 仍為 tier2 目錄隊 | 153 |
| 新增官方名冊球員 | 566 |
| 新增教練 | 20 |
| 教練覆蓋（原有 → 現在） | 325 → 345 |
| 新增球員 `source_url` 非空 | 566 / 566 |
| 新增教練 `source_url` 非空 | 20 / 20 |
| 虛構球員／教練 | 0 |
| 新增比分或賽果 | 0 |

官方文章只確認球員列入 2026/27 squad-number 名單；年齡、國籍、出場、分鐘等未由該頁提供的欄位保持 `null`，沒有補估。399 名球員能以現有已核實主檔取得唯一位置，另外 167 名保留未分類，避免按球衣號碼猜位置。

## 20 隊教練及名冊

所有 20 隊的 `manager`、`squad`、`source_url` 均已填寫；`squad` 指向同一個英超官方 2026/27 名單頁，`manager` 的來源指向對應官方經理／球會任命頁。完整逐名資料在 `data/leagues/afc-champions-league-elite/epl_full_squads.json`。

## 資料檔

- `data/final_574_squads_with_sources.json`：保留原 574 記錄並追加 20 個 AFC 英超 Full scope 記錄，共 596 個容器。
- `assets/data/final_574_squads_with_sources.json`：與 data 主檔同步，供 App 使用。
- `data/player_master_ALL_574_REAL.json`：追加 20 個 AFC 英超 Full scope 記錄，共 594 個 master keys。
- `data/player_master_FRONT_574_REAL.json` / `data/player_master_BACK_574_REAL.json`：同步追加可安全分類的位置資料。
- `data/leagues/afc-champions-league-elite/teams.csv`：173 行、20 行 Full、153 行 Tier 2，唯一隊名 173。

## 原則

本次沒有新增球員年齡、國籍、出場、分鐘、比分或角球估算；未能從官方 squad-number 頁確認的欄位保持 `null`。`directory_only` 隊伍沒有被加入球員或教練資料。
