# 367隊資料來源與可重現性

本版本使用 Football-Data.co.uk 的歷史CSV下載頁及逐季CSV。下載頁列出2021/22、2022/23、2023/24及2024/25的data.zip；本地 `data/raw/` 保存合併後的來源證據檔案。

- NED.csv：N1 Eredivisie
- POR.csv：P1 Primeira Liga
- BEL.csv：B1 Belgian First Division A
- TUR.csv：T1 Turkish Super Lig
- GRE.csv：G1 Greek Super League
- AUT.csv：奧超四季資料，來源為倉庫內已保存的Football-Data Austria歷史檔，按四個指定賽季篩選及標準化
- E1.csv、E2.csv、D2.csv：英冠、英甲、德乙，用於補足新增137隊

所有新增比賽均要求Date、HomeTeam、AwayTeam、FTHG、FTAG存在。新增資料的HT欄位固定寫為null；沒有使用FT推算HT。原有230隊及其真實HT不作刪改。

## 驗收數字

- 基礎Catalog：230隊
- 新增：137隊
- 最終：367隊
- Catalog行數：36,810
- FT無效行：0
- FT去重：至少22,000場
- 新增資料非空HT：0行

## References

[1]: https://football-data.co.uk/downloadm.php "Football-Data historical results download page"
[2]: https://football-data.co.uk/mmz4281/2324/data.zip "Football-Data 2023/2024 CSV archive"
[3]: https://football-data.co.uk/mmz4281/2425/data.zip "Football-Data 2024/2025 CSV archive"
