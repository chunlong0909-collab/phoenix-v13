# F批：Wolves + Leverkusen + Leipzig 放寬Full審計報告

- 目標：3隊
- 已有 Full（重用）：Bayer Leverkusen、RB Leipzig
- 成功新增 Full：0隊
- 原有 tier1：50隊
- 最終 tier1：50隊
- players.csv：1,319人
- coaches.csv：50隊
- teams.csv：252隊，唯一252
- 假隊：0
- Al Ahli / Al Hilal 模糊匹配：PASS
- Streamlit 8501：待驗證

## 誠實結論

Leverkusen及RB Leipzig已在既有50隊Full基線內，沒有重複合併。Wolves未能完成官方2025/26背號閉環，因此沒有新增任何球員或教練。現有資料保持不變。

## 保留tier0

- Wolverhampton Wanderers (Eng)：The official 2025/26 squad photo and official announcement do not provide a complete official shirt-number register. The currently accessible official squad page is a later live roster, so using it would mix seasons. Under the requested rule, do not output an incomplete 18-35 player list.
- Bayer Leverkusen (Ger)：The official 2025/26-era squad page is preserved as an archive.org snapshot, but its player-card content is dynamically rendered and the retrieved snapshot does not expose a complete, verifiable set of official shirt numbers. The live Bayer 04 squad page has already rolled over to 2026/27. Transfermarkt and Bundesliga can corroborate candidate names, positions and some numbers, but under the requested rule they cannot substitute for official shirt-number evidence. Because official shirt-number coverage is incomplete, no partial or reconstructed player list is emitted.
- RB Leipzig (Ger)：官方 2025/26 季前集訓公告提供 35 名球員及背號，但其中包含其後在夏窗離隊或租借離隊者；官方 first-team 頁在可讀頁面未提供可核對的 2025/26 歷史完整名單，且官方夏窗總結僅確認最終為 24 名場上球員、3 名門將及 2 名 academy players，未在可讀內容中逐人列出最終名單與全部背號。Transfermarkt 可補國籍及位置，但其 25/26 頁顯示的是混合賽季後 current-club 狀態，不能單獨證明最終男子一隊歸屬。依 F 批規則，無法在每名球員同時滿足「最終 2025/26 男子一隊」「官方背號」「至少兩個公開 URL」前，不輸出不完整名單。

規則：不新增隊伍、不創作背號、不使用混合賽季名單。
