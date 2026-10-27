# Phoenix V1.8：Daejeon Hana Citizen 0–1 Vissel Kobe

## 寫入資料

- 日期：2026-10-27
- 聯賽：AFC Champions League Elite／亞冠精英盃 MD3
- 主隊：Daejeon Hana Citizen
- 客隊：Vissel Kobe
- 全場：0–1
- 角球：7–2，總數9
- 來源標記：`Betora / AFC官方賽報（公開賽事統計；使用者指定）`

AFC官方賽前頁確認賽事為2026-10-27的大田主場比賽：
<https://www.the-afc.com/en/club/afc_champions_league_elite.html/news/preview-daejeon-hana-citizen-fc-kor-v-vissel-kobe-jpn>

可公開讀取的賽事統計交叉核對頁：
<https://www.totalcorner.com/stats/daejeon-hana-citizen-vs-vissel-kobe/203512359>

## 角球完整度政策

K1 `data/leagues/k1/matches.csv` 內大田的既有賽果沒有核實HC/AC，因此全部維持空白；沒有用估算值填補。V1.8徽章按實際非空HC/AC行數計算，低於90%時顯示警示色，不會冒充完整資料。

本場亞冠紀錄的7–2屬於已指定寫入的公開賽事統計；模型的其他K1角球資料仍然是缺失狀態。

## 驗收

`python3 run_model.py --match 'Daejeon Hana Citizen' 'Vissel Kobe' --check` 通過：

- 大田合併後樣本：22場
- 神戶合併後樣本：158場
- 預期入球：2.1437
- 1X2模型機率：主勝18.91%、和局26.56%、客勝56.24%
- 選定兩隊可用真實角球行：1場（本場7–2）
- `V1.8_CHECK=PASS`
