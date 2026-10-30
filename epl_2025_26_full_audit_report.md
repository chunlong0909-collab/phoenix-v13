# 英超 2025/26 第四批 Full 化審計報告

## 結論

20 支英超目錄隊逐隊核查完成，但沒有任何一隊同時通過 Premier League 官方主源、球會官網、FBref／Transfermarkt 輔助來源、官方背號、完整 22–30 人一隊名單及所有硬欄位要求。故本批英超 0 隊升級，20 隊全部保留 tier0。

## 統計

- 遠端總隊數：249
- 唯一隊名：249
- tier1（原有德甲）：8
- tier0：241
- 英超新 Full：0 隊
- 英超保留 tier0：20 隊
- 新增球員：0
- 新增教練：0
- 現有 players.csv：207 人，未修改
- 假隊：0
- Al Ahli / Al Hilal 模糊匹配：PASS
- Elversberg / Paderborn / Schalke：已移除

## 英超保留 tier0

Arsenal (Eng)、Aston Villa (Eng)、Bournemouth (Eng)、Brentford (Eng)、Brighton and Hove Albion (Eng)、Chelsea (Eng)、Coventry City (Eng)、Crystal Palace (Eng)、Everton (Eng)、Fulham (Eng)、Hull City (Eng)、Ipswich Town (Eng)、Leeds United (Eng)、Liverpool (Eng)、Manchester City (Eng)、Manchester United (Eng)、Newcastle United (Eng)、Nottingham Forest (Eng)、Sunderland (Eng)、Tottenham Hotspur (Eng)

## 主要阻塞原因

- Premier League 官方 squad 頁面多數已切換到 2026/27。
- 部分 2025/26 官方 squad-list 只提供登記名單，沒有完整逐人背號、出生年及所有硬欄位。
- FBref／Transfermarkt 只能作輔助，不能取代指定的英超官方 2025/26 背號主源。
- Bournemouth 只有 21 人，低於 22 人門檻。
- Liverpool 的英超官方頁及 FBref 受到阻擋。
- Hull City、Ipswich Town 等核查結果顯示並非符合目標英超 2025/26完整一隊條件。
- 所有缺失欄位均沒有補填，沒有創造球員或背號。

## 封存檔

`data/final_epl_20_squads_with_sources.json` 為空 JSON 物件 `{}`，代表本批沒有任何通過硬門檻的英超 Full 隊伍；不會把不完整名單冒充 Full。

本批只新增審計及空候選封存檔，沒有修改 players.csv、teams.csv、教練資料或主檔。
