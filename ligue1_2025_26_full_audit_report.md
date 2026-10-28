# 法甲 2025/26 第二批 Full 化審計報告

## 結論

本批沒有安全合併任何法甲隊伍。Brest 與 Marseille 的三源身份核查標記為候選，但逐人輸出缺少指定硬欄位 `shirt_number` 及／或 `source_urls`，因此全部保留 tier2。沒有修改 teams.csv、players.csv 或 coaches.csv。

## 數字

- 遠端總隊數：249
- 唯一隊名：249
- 法甲候選：2 隊（Brest、Marseille）
- 嚴格 schema 通過：0 隊
- 保留 tier2 法甲：18 隊
- 新增球員：0
- 新增教練：0
- 已完成德甲 tier1：8 隊，保持不變
- 假隊：0

## 候選失敗原因
### Brest (Fra)
- 報告球員數：26
- 缺少欄位：shirt_number, source_urls
- 決定：不合併，保留 tier2

### Marseille (Fra)
- 報告球員數：20
- 缺少欄位：shirt_number, source_urls
- 決定：不合併，保留 tier2

## 硬欄位

`name`, `position`, `shirt_number`, `nationality`, `birth_year`, `source_transfermarkt`, `source_fbref`, `source_official`, `source_urls`, `season=2025/26`。

只有所有硬欄位齊全、來源可回溯及一隊人數達標，才可升級 tier1。
