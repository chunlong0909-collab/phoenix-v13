# 世界聯賽擴充來源與可重現性（2026-10-25）

## 採用來源

本期只採用 Football-Data.co.uk 的公開 aggregate CSV，並把原始檔保存於 `data/raw/`：

- 阿根廷：<https://football-data.co.uk/new/ARG.csv>
- 巴西：<https://football-data.co.uk/new/BRA.csv>
- 美國 MLS：<https://football-data.co.uk/new/USA.csv>
- 墨西哥：<https://football-data.co.uk/new/MEX.csv>
- 日本 J1：<https://football-data.co.uk/new/JPN.csv>

這些檔案含 `Season`, `Home`, `Away`, `HG`, `AG` 欄位。程式只使用實際 `HG/AG` 作為 FT；HT 沒有可靠欄位時維持 `null`，不以 FT 推算。

## 完整賽季規則

只有同一隊在指定四個賽季均達到該聯賽合理的完整賽季場數門檻，才會加入新Catalog。當來源檔只包含部分賽季或正在更新的內容，該隊會被跳過。任何無法解析的FT列也不會寫入Catalog。

## 實際結果

基準為367隊。官方CSV驗證後，符合四季完整FT門檻且不與基準隊伍重複的新增隊伍為65隊：阿甲20、巴甲1、美職MLS27、墨西超17；J1已存在於基準Catalog，所以沒有重複新增。最終 `complete_world_500_catalog.json` 為432隊，而不是虛構宣稱500隊。

未達500的原因是：基準Catalog已包含完整J1及大部分巴甲隊伍；其餘候選聯賽的官方aggregate CSV雖有歷史FT，但部分聯賽/年份的隊伍更替、賽季檔案覆蓋或資料並不滿足「同一隊四季完整」門檻。韓職K1及澳職沒有在 Football-Data 的官方 extra-league CSV清單中提供相同四季完整檔案，本期不以未核實鏡像補數。

## 產出

- `catalog/complete_world_500_catalog.json`
- `catalog/expansion_500_report.json`
- `catalog/500_backtest_report.json`
- `scripts/expand_500.py`
- `scripts/validate_500.py`

驗收腳本會報告實際隊數、FT行數、去重場數、FT invalid rows，以及新增資料的HT null政策；它不會把432隊標成500隊。
