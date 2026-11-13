# Phoenix 英超校準每日報告（2026-11-13）

- 執行時間：2026-11-13 10:23 HKT
- 聯賽：英超（EPL）2026/27
- 執行範圍：先完成既有 Phoenix 安全更新流程；再做英超校準
- 結論：**未校準，保持未校準並停用 EV**。Managed MySQL 在本次排程任務不可存取，`phoenix_league_calibration_status` 未能更新。

## 1. 安全更新流程

| 項目 | 結果 |
|---|---:|
| 模式 | dry-run 後 commit |
| verified FT 總數 | 43,372 |
| 球隊快照 | 1,469 |
| 實際寫入衍生快照 | 1,469 |
| `football_complete.db` integrity | ok |
| `football_library.db` integrity | ok |
| 寫入 `phoenix_auto_matches` / `phoenix_odds` / `phoenix_auto_team_stats` | 0 |
| 寫入任何 SQLite 賽果表 | 0 |
| API-Football 來源 | `skipped_no_API_FOOTBALL_TOKEN` |

安全更新只寫入 `teams_stats` 衍生快照；沒有改動任何賽果原始表。兩個 SQLite 在寫入前已備份至 `backups/`，寫入後 `integrity_check=ok`。

## 2. 英超校準候選與寫入

| 指標 | 數值 |
|---|---:|
| 候選賽事（Football-Data E0.csv） | 100 |
| Bet365 賽前 W/D/L 完整 | 100 |
| 官方賽前排名可重建 | 90 |
| Phoenix 近 10 場模型方向可計算 | 90 |
| 四項齊全、可寫入樣本 | **0** |
| 資料不足 | 100 |

### 資料不足原因

| 原因 | 場數 |
|---|---:|
| 缺少 `phoenix_auto_matches` 內 `verified_ft=1`（Managed MySQL 無法存取） | 100 |
| 缺少官方 fixtures API 賽前排名（開賽日前無已完場賽事可重建） | 10 |
| 缺少 Phoenix 近 10 場模型方向 | 10 |

補充說明：

- 10 場缺少官方賽前排名的是**第一週**賽事；開賽日前沒有任何本季已完場賽事，按規則不能借用上季排名，記 Insufficient Data。
- 10 場缺少近 10 場模型方向的是**Coventry** 賽事。Coventry 是升班馬，既有 Phoenix 模型只有 7 場英超紀錄，不足 10 場；沒有借用英冠數據補數。
- 其餘 90 場的賠率、官方賽前排名及近 10 場模型方向齊全，但全部因 `verified_ft` 無法從 Managed MySQL 核實，仍記 Insufficient Data。沒有用 Football-Data 的 FT 補 `verified_ft`。

## 3. 覆蓋率與一致率

| 指標 | 數值 | 門檻 | 結果 |
|---|---:|---:|---|
| 近 10 場覆蓋率（可計算） | 90.00% | ≥80% | 通過 |
| 官方排名覆蓋率 | 90.00% | ≥80% | 通過 |
| 完整寫入覆蓋率 | 0.00% | — | 受 MySQL 阻塞 |
| 今日模型與市場最高方向一致率 | 54.44%（49/90） | — | 診斷值，非累積校準率 |
| 累積樣本總數（上次已知） | 73 | ≥30 | 通過 |
| 累積一致率（上次已知） | 57.53%（42/73） | ≥60% | **未通過** |

累積樣本總數與一致率來自 2026-11-11 報告的 Managed MySQL 狀態。本次無法重新查詢，已在 JSON 標記為 `last_known_from_20261111_report_not_re_queried`，沒有當成今日新查詢結果。

## 4. 狀態判定

| 門檻 | 結果 |
|---|---|
| 至少 30 場 | 通過（73，上次已知） |
| 模型與市場最高方向一致率至少 60% | **未通過（57.53%）** |
| 近 10 場覆蓋率至少 80% | 通過（90.00%） |
| 官方排名覆蓋率至少 80% | 通過（90.00%） |
| Managed MySQL 可更新狀態 | **否** |

因此：

- **英超未校準**。
- **EV 保持停用**。
- **不開始英冠或西甲**。
- `phoenix_league_calibration_status` 未更新；不是「已更新為未校準」，而是本次沒有連線可寫入。下次有 Managed MySQL 連線時，應先重新查詢 73 筆樣本及一致率，再寫入狀態。

## 5. 來源與抓取時間

| 來源 | URL | 抓取時間 | 用途 |
|---|---|---|---|
| Football-Data.co.uk 2026/27 E0.csv | https://football-data.co.uk/mmz4281/2627/E0.csv | 2026-11-13 10:20 HKT | Bet365 賽前 W/D/L 賠率（100/100 完整） |
| Premier League 官方 fixtures API | https://footballapi.pulselive.com/football/fixtures?comps=1&compSeasons=841&compsCodeForSort=PL&altIds=true&page=0&pageSize=1000 | 2026-11-13 10:20 HKT | 100 場已完場；按每場開賽日前重建積分榜 |
| Managed MySQL | `phoenix_auto_matches` / `phoenix_epl_calibration_samples` / `phoenix_league_calibration_status` | 2026-11-13 10:23 HKT | 無連線；`verified_ft` 記 Insufficient Data，未寫入樣本或狀態 |

## 6. 合規檢查

- 只使用 Football-Data.co.uk 季節 CSV 的 Bet365 賽前 W/D/L 賠率。
- 沒有使用 API-Football odds endpoint。
- 沒有使用 `API_FOOTBALL_TOKEN`。
- 沒有 INSERT/UPDATE/DELETE `phoenix_auto_matches`、`phoenix_odds`、`phoenix_auto_team_stats`。
- 沒有寫入任何 SQLite 賽果表。
- 沒有估算、沒有補數；缺資料一律記 Insufficient Data。
- 英超未達標，沒有開始英冠或西甲。

## 7. 附件

- 完整 JSON：`data/epl_calibration_report_20261113.json`
- 逐場稽核 CSV：`data/epl_calibration_candidates_20261113.csv`
- 原始賠率 CSV：`data/raw/e0_20261113.csv`
- 原始官方 fixtures JSON：`data/raw/pl_fixtures_20261113.json`
- 安全更新報告：`data/auto_update_last_report.json`
