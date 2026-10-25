# 自動更新

## 每週一球員及教練更新

GitHub Actions workflow `Weekly squad and coach refresh` 會在每週一UTC 04:00執行，亦可從Actions頁面手動啟動。

流程分為兩步：

1. `scripts/wikipedia_squad_updater.py`只為目前沒有球員名冊的隊伍查詢Wikipedia Current Squad表格。已存在的球員資料、教練資料和FT賽果不會被刪除或覆蓋。
2. `scripts/enrich_coaches_for_436.py`更新已有球員資料隊伍的Wikipedia Manager/Head coach欄位。若本週查不到新資料，會保留既有教練記錄；只有明確核實的教練姓名才會寫入。

當`data/final_574_squads_with_sources.json`有變動時，workflow會以當日UTC日期建立commit：

```text
chore: weekly squad+coach refresh YYYY-MM-DD
```

沒有變動時不會產生空commit。更新器只使用免費公開來源；Wikipedia未提供的球員出場數會保持未提供標記，不會估算。
