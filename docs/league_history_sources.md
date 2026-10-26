# 全聯賽歷史賽果來源證據

本次補數只保存已完成賽果的全場比分；沒有從公開結果頁取得角球時，`home_corners`及`away_corners`保留空白，不以0代替。

## Flashscore公開結果頁

以下來源均為公開結果頁，補數程式只讀取已完場事件、日期、主隊、客隊及全場入球：

- 希超：[Flashscore Greece Super League results](https://www.flashscore.com/football/greece/super-league/results/)
- 意乙：[Flashscore Italy Serie B results](https://www.flashscore.com/football/italy/serie-b/results/)
- 意甲：[Flashscore Italy Serie A results](https://www.flashscore.com/football/italy/serie-a/results/)
- 法甲：[Flashscore France Ligue 1 results](https://www.flashscore.com/football/france/ligue-1/results/)
- 美職MLS：[Flashscore USA MLS results](https://www.flashscore.com/football/usa/mls/results/)
- 英甲：[Flashscore England League One results](https://www.flashscore.com/football/england/league-one/results/)
- 蘇冠：[Flashscore Scotland Championship results](https://www.flashscore.com/football/scotland/championship/results/)

試跑證據：墨西超、日職J2及沙特聯賽結果頁均返回HTTP 200，原始結果區塊分別為164、288及239個；這三項最終使用本地已存在的真實CSV，沒有重複寫入Flashscore資料。

## 本地已驗證CSV

其餘聯賽優先使用Repo內已有的本地真實CSV，避免不必要地重抓公開網站。實際來源及行數記錄在[`data/full_league_fill_report.json`](../data/full_league_fill_report.json)及[`full_league_fill.log`](../full_league_fill.log)。

## 固定格式

每個聯賽在`data/match_history/`及`assets/data/match_history/`各有一份CSV，固定9欄：

```text
date, home_team, away_team, home_goals, away_goals, home_corners, away_corners, league, season
```

角球來源未核實時留空。檔名對中文聯賽使用可重現的SHA-1短slug，避免不同中文名稱互相覆蓋；App會用相同規則讀取。
