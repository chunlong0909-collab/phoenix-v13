# V1.8 Shabab Al Ahli vs Esteghlal 資料證據

本次只加入有完場比分的公開紀錄，沒有加入未開賽、預測或角球估算。兩隊跨賽季樣本保留 `season` 與 `source_url`。

- Shabab Al Ahli Club：2025/26 UAE Pro League 已完場紀錄，來源：[WorldFootball fixtures/results](https://www.worldfootball.net/teams/te18247/shabab-al-ahli-club/all-matches/)
- Esteghlal F.C.：2025/26 Persian Gulf Pro League 與 AFC Champions League Two 已完場紀錄，來源：[WorldFootball 2025/26](https://www.worldfootball.net/teams/te17473/esteghlal/vs2025-2026/all-matches/)
- 角球欄位維持空白，因為本批來源沒有逐場可核對 HC/AC；角球資料不足不會阻止入球及1X2模型。
- Dubai 天氣：指定 `2026-10-27T20:00:00`（GST），優先OpenWeatherMap，無Key時使用Open-Meteo免費後備並顯示來源與完整度；天氣只作參考，不修改 expected goals。
