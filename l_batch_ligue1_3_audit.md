# L批：法甲PSG／馬賽／里昂誠實Full審計報告

- 目標：3隊
- 成功Full：0隊
- 原有tier1：52隊
- 最終tier1：52隊
- 法甲Full：0/18 → 0/18（現有目錄法甲為18隊）
- players.csv：1,371人
- coaches.csv：52隊
- teams.csv：252隊，唯一252
- 假隊：0
- Al Ahli / Al Hilal 模糊匹配：PASS
- Streamlit 8501：待驗證
- 新增球員：0人

## canonical對位

- Paris Saint-Germain → PSG (Fra)
- Olympique de Marseille → Marseille (Fra)
- Olympique Lyonnais → Lyon (Fra)

## blocked原因

- PSG：官方/season/2025-26 URL實際回傳2026/27，不能用輔助資料拼接。
- 馬賽：官方現行一隊頁與ESPN/Transfermarkt 2025/26背號衝突。
- 里昂：官方季前公告沒有逐人背號，現行一隊頁已是2026/27。

本批沒有修改teams.csv、players.csv或coaches.csv。
