# M批：法甲PSG／馬賽／里昂三源交叉審計報告

- 目標：3隊
- 成功Full：0隊
- 原有tier1：52隊
- 最終tier1：52隊
- 法甲Full：0/18 → 0/18
- players.csv：1,371人
- coaches.csv：52隊
- teams.csv：252隊，唯一252
- 假隊：0
- Al Ahli / Al Hilal 模糊匹配：PASS
- Streamlit 8501：待驗證
- 新增球員：0人
- source_type：cross_verified_ligue1_official_cutover（本批未達通過門檻）

## blocked原因

- PSG：Ligue1官方頁沒有可提取的逐人姓名、位置、背號、國籍及賽季欄位。
- 馬賽：Transfermarkt、ESPN及官方cutover存在背號不一致與缺失。
- 里昂：Transfermarkt及ESPN存在跨季污染，Ligue1官方頁沒有可提取完整名單。

由於三源沒有逐人完全一致，本批沒有修改teams.csv、players.csv或coaches.csv；沒有產生虛構截圖或球員資料。
