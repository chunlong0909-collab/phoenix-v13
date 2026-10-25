# App 整合審計報告

## 審計日期

2026-10-26。

## 1. App 類型及入口

Repo 內沒有 `lib/`、`pubspec.yaml`、React `src/` 或 `package.json`。實際入口是兩個 Streamlit Web App：

- `app.py`：主混合來源足球分析App。
- `app_poisson_v2.py`：獨立SQLite泊松分析App。

本次修正以主入口 `app.py` 為正式整合對象；它仍然保留原有`football_library.db`、Phoenix 63隊賽果及本地資料館流程。

## 2. 審計前發現

- `data/final_574_squads_with_sources.json` 原本只在 `data/`，主App沒有讀取它。
- App 原本只讀取 `assets/data/phoenix_FINAL_63teams.json` 作為63隊賽果資料。
- `predict_match.py` 原本沒有被 `app.py` import；主App使用自己內部的泊松函數。
- 原本每週workflow沒有把574隊名冊複製到App資產目錄。
- `app_poisson_v2.py`亦是獨立入口，使用自己的SQLite `predict_match`函數，不是主App的正式執行路徑。

## 3. 已完成Fix

### Squad檔

已複製並驗證：

```text
data/final_574_squads_with_sources.json
assets/data/final_574_squads_with_sources.json

兩者大小：5,998,672 bytes
隊伍容器：574
```

`app.py`現在會從`assets/data/final_574_squads_with_sources.json`讀取球員及教練資料，並以隊名配對。

### 預測模組

`app.py`現在明確import：

```python
from predict_match import apply_coach_factors, apply_weather_factor, load_squads
```

主App在傷停、ORBIFLOW及學習修正後，將新版`coach_factor`及`weather_factor`套用到預期入球，並將兩者寫入`st.session_state["last_prediction_factors"]`及畫面提示。

### 每週同步

`weekly_squad_refresh.yml`已加入：

```yaml
- name: Sync verified squads into App assets
  run: |
    mkdir -p assets/data
    cp data/final_574_squads_with_sources.json assets/data/final_574_squads_with_sources.json
```

workflow提交時會同時加入根資料及App資產檔，避免下週只更新後台而沒有更新App。

## 4. 測試結果

- `app.py`、`predict_match.py`及更新器均通過Python compile。
- App import檢查：PASS。
- 574隊資產檔JSON載入：PASS。
- Workflow複製步驟檢查：PASS。
- `coach_factor`測試：PASS。
- `weather_factor`測試：PASS。
- 模擬雨量20mm、氣溫3°C時，天氣總入球因子為`0.8075`（雨勢`0.85` × 低溫`0.95`），沒有使用外部估算比分。

詳細機器測試輸出見[`audit_app_integration_test.log`](audit_app_integration_test.log)。

## 結論

**主Streamlit App已完成574隊Squad檔及新版教練／天氣因子接入。**

需要注意：`app_poisson_v2.py`仍是另一個獨立SQLite入口，並非主`app.py`的同一條預測流程；如啟動它，會使用自己的SQLite泊松函數。正式使用574隊Squad、教練因子及天氣因子時，應啟動：

```bash
streamlit run app.py
```
