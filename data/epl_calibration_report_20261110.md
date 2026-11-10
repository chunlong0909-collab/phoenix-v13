# Phoenix 英超校準收集與評估日報

**執行時間**：2026-11-10 10:11 HKT（香港時間）  
**任務來源**：Manus 排程任務「Phoenix每日數據同步及英超校準收集」（每日 10:00 HKT）  
**程式版本**：phoenix-v13（commit `a0ed607`）

---

## 執行摘要

| 項目 | 數值／狀態 | 說明 |
|---|---|---|
| 安全更新流程 | 已完成 | dry-run 通過後 commit；43,430 筆已驗證 FT、1,511 筆球隊快照寫入 SQLite（`football_complete.db` / `football_library.db` 的 `teams_stats` 衍生表）；API-Football 未使用 |
| 候選賽事數 | **100** | 來自 Football-Data.co.uk 2026/27 季節 CSV（第 1 至 10 週） |
| 寫入樣本數 | **0** | 四項條件未同時齊備（`verified_ft=1` 缺資料） |
| 資料不足場次 | **100** | 依「資料缺失就記 Insufficient Data，不估算、不補數」規則 |
| 累積校準樣本總數 | **73** | 沿用先前於 Managed MySQL 儲存之樣本數（本日新增 0） |
| 模型市場一致率 | **57.53%**（42/73） | 低於 60% 門檻 |
| 近 10 場模型方向覆蓋率 | **0.00%**（實際寫入／候選）；**90.00%**（90/100 可計算） | 低於 80% 門檻 |
| 官方排名覆蓋率 | **90.00%**（90/100） | 達標（≥ 80%）；第 1 週 10 場因開賽日前無官方完場賽事而缺賽前排名 |
| 賠率完整度 | **100%**（100/100） | Bet365 賽前 W/D/L 全部齊全 |
| **校準狀態** | **未校準，保持未校準並停用 EV** | 四項條件均需同時滿足，英超尚未達標 |
| 後續聯賽 | **不開始英冠或西甲** | 英超達標前不啟動 |
| 下次排程 | 2026-11-11 10:00 HKT | 每日排程自動執行 |

---

## 一、既有 Phoenix 安全更新流程執行結果

1. **Dry-run 測試**：`python scripts/auto_update.py` 執行成功（exit code 0），`status=dry_run`，共驗證 43,430 筆 FT 紀錄，建立 1,511 筆球隊快照，未寫入資料庫。
2. **正式 Commit**：`python scripts/auto_update.py --commit` 執行成功，`status=committed`，1,511 筆快照成功寫入兩個 SQLite 資料庫（`football_complete.db`、`football_library.db`）。
3. **API-Football 遵循安全政策**：`api_sources` 狀態為 `skipped_no_API_FOOTBALL_TOKEN`，完全未使用 API-Football odds endpoint 或 API_FOOTBALL_TOKEN。
4. **ESPN 公開比分**：抓取 30 筆已完場比分。
5. **沙特聯賽官方資料**：已檢查沙特職業聯賽官方網站，處理 Al Hazem 球隊名錄與統計資料。
6. **Streamlit 服務健康檢查**：`https://phoenixweb-jlbnawhz.manus.space/_stcore/health` 回應 **ok**（HTTP 200）。
7. **Git 紀錄**：更新報告、資料庫及追蹤檔將提交至 main 分支。

---

## 二、英超校準候選與寫入結果

### 1. 候選數與來源

- **候選賽事數**：100 場（2026/27 英超第 1 至 10 週，2026-08-21 至 2026-11-08）
- **來源**：Football-Data.co.uk 季節 CSV（URL 見來源清單）
- **抓取時間**：2026-11-10 10:09 HKT
- **Bet365 賽前 W/D/L 賠率完整度**：100/100（100%），無任一場缺少賠率

### 2. 寫入數

- **本日寫入數**：0 場
- **原因**：每筆紀錄必須「Bet365 賽前 W/D/L 賠率 + 官方賽前排名 + `phoenix_auto_matches` 內 `verified_ft=1` + Phoenix 近 10 場模型方向」四項全部齊全才可寫入；本日 `phoenix_auto_matches` 無法存取（見下節），故符合寫入條件的紀錄為 0 筆。

---

## 三、資料不足原因

依任務嚴格規則「**資料缺失就記 Insufficient Data，不估算、不補數**」，每筆候選賽事逐項審計，缺失原因計數如下：

| 缺失原因 | 受影響場數 | 說明 |
|---|---|---|
| 缺少 `phoenix_auto_matches` 內 `verified_ft=1`（Managed MySQL 無法存取） | 100 場（100%） | 本沙箱執行環境無法連接 Managed MySQL `phoenix_auto_matches` 表，依規則記錄為 Insufficient Data，不補數 |
| 缺少官方 fixtures API 賽前排名 | 10 場（10.00%） | 第 1 週（2026-08-21 至 08-22）10 場賽事因其開賽日前尚無官方已完場賽事，積分榜無法重建，依規則不填補 |
| 缺少 Phoenix 近 10 場模型方向 | 10 場（10.00%） | 主客兩隊任一方在開賽日前於資料庫中累計已完場賽事不足 10 場，無法計算 10 場滾動均值，故模型方向缺資料 |
| 缺少 Bet365 賽前 W/D/L 賠率 | 0 場（0%） | 全部齊全 |

---

## 四、樣本總數與一致率

| 指標 | 數值 | 門檻 | 是否達標 |
|---|---|---|---|
| 累積校準樣本總數 | 73 場（沿用先前 Managed MySQL 儲存狀態；本日新增 0） | ≥ 30 場 | 達標 |
| 模型與市場最高方向一致率 | **57.53%**（42/73） | ≥ 60.00% | 未達標 |
| 近 10 場覆蓋率（實際寫入／候選） | **0.00%**（0/100） | ≥ 80.00% | 未達標 |
| 官方排名覆蓋率 | **90.00%**（90/100） | ≥ 80.00% | 達標 |

> **補充參考**：若僅看本日 100 場候選中同時具備「市場賠率最高方向」與「模型方向」的 90 場賽事，模型與市場最高方向一致者為 49 場，一致率為 **54.44%**（49/90），同樣低於 60% 門檻。

---

## 五、校準狀態判定

英超目前狀態為 **未校準，保持未校準並停用 EV**。判定依據如下：

1. 累積校準樣本數 73 場已達 ≥ 30 場門檻；
2. 模型與市場最高方向一致率 57.53% **未達** ≥ 60.00% 門檻；
3. 近 10 場完整寫入覆蓋率 0.00% **未達** ≥ 80.00% 門檻；
4. 官方排名覆蓋率 90.00% 已達 ≥ 80.00% 門檻；
5. 四項條件須**同時**滿足才可標記已校準，故英超保持未校準，**EV 估值功能維持停用**。

由於 Managed MySQL 本次無法連接，`phoenix_league_calibration_status` 亦無法寫入 Managed MySQL，狀態記錄於本報告中。

---

## 六、安全與合規檢查

| 檢查項目 | 結果 | 備註 |
|---|---|---|
| `phoenix_auto_matches` 寫入數 | 0 | 唯讀存取嘗試，未做 INSERT/UPDATE/DELETE |
| `phoenix_odds` 寫入數 | 0 | 未修改 |
| `phoenix_auto_team_stats` 寫入數 | 0 | 未修改 |
| SQLite 賽果表（`fixtures` 等）寫入數 | 0 | 未修改任何 match results 表；安全更新僅寫入 `teams_stats` 衍生快照 |
| API-Football odds endpoint 使用 | 否 | 完全未調用 |
| `API_FOOTBALL_TOKEN` 使用 | 否 | 環境變數未注入任何 odds 相關 API 請求 |
| Football-Data FT 補數備用方案使用 | 否 | 未以 Football-Data 的比分代替 `verified_ft=1` |
| 未估算、未補數 | 符合 | 所有缺資料均記為 Insufficient Data |

---

## 七、來源 URL 與抓取時間

| # | 來源類型 | URL | 抓取時間（HKT） | 內容說明 |
|---|---|---|---|---|
| 1 | 賠率來源 | `https://football-data.co.uk/mmz4281/2627/E0.csv` | 2026-11-10 10:09 | Football-Data.co.uk 2026/27 英超季節 CSV，Bet365 賽前 W/D/L 賠率，100/100 完整 |
| 2 | 官方賽事與排名來源 | `https://footballapi.pulselive.com/football/fixtures?comps=1&compSeasons=841&compsCodeForSort=PL&altIds=true&page=0&pageSize=1000` | 2026-11-10 10:09 | Premier League 官方 fixtures API，100 場已完場賽事，按每場開賽日前重建賽前排名 |
| 3 | 已驗證比分來源 | Managed MySQL: `phoenix_auto_matches` | 2026-11-10 10:10 | 存取結果：無連線，記 Insufficient Data |

---

## 八、後續聯賽與下次排程

- **英冠／西甲**：依規定「英超達標前不要開始英冠或西甲」，目前英超未達標，**不啟動英冠或西甲之校準收集**。
- **下次排程執行**：2026-11-11 10:00 HKT（每日香港時間 10:00 自動執行）。

---

*本報告由 Phoenix 每日校準自動排程於 2026-11-10 10:11 HKT 產出。*
