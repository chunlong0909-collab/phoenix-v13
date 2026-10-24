# 2021-08-01 至 2023-07-31 歷史FT資料來源

Football-Data 的資料頁確認提供逐場 FT/HT CSV。英格蘭頁列出 2021/22 及 2022/23 的 E0 等檔案：[https://football-data.co.uk/englandm.php](https://football-data.co.uk/englandm.php)。歐洲整季 ZIP 位於：[https://football-data.co.uk/downloadm.php](https://football-data.co.uk/downloadm.php)，其中 `2122/data.zip` 與 `2223/data.zip` 已下載並解壓，包含 E0、SP1、I1、D1、F1、N1、P1、T1、B1 等聯賽檔案。

葡超資料頁直接列出 2021/22 `2122/P1.csv` 及 2022/23 `2223/P1.csv`，來源：[https://football-data.co.uk/portugalm.php](https://football-data.co.uk/portugalm.php)。Football-Data 欄位說明及資料來源說明：[https://football-data.co.uk/notes.txt](https://football-data.co.uk/notes.txt)。

J.League 官方2023賽季頁面可確認賽季隊伍及排名，但目前沒有取得可直接驗證的逐場歷史CSV，因此本階段不把J1歷史FT混入Catalog：[https://aboutj.jleague.jp/seasonreview2023/en/season-result/](https://aboutj.jleague.jp/seasonreview2023/en/season-result/)。

鐵律：新增歷史記錄只使用原始 `FTHG/FTAG`，不生成或估算HT；HT欄位保持null。
