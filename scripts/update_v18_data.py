from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
paths = [
    ROOT / "data/match_history/league_12baad9e48.csv",
    ROOT / "assets/data/match_history/league_12baad9e48.csv",
]
row = {
    "date": "2026-10-27",
    "home_team": "Daejeon Hana Citizen",
    "away_team": "Vissel Kobe",
    "home_goals": 0,
    "away_goals": 1,
    "home_corners": 7,
    "away_corners": 2,
    "league": "亞冠精英盃",
    "season": 2026,
    "source": "Betora / AFC官方賽報（公開賽事統計；使用者指定）",
    "source_url": "https://www.totalcorner.com/stats/daejeon-hana-citizen-vs-vissel-kobe/203512359",
}
for path in paths:
    df = pd.read_csv(path)
    # 覆蓋同一場的舊行，避免同一比賽重複計算。
    key = (df["date"].astype(str).eq(row["date"]) &
           df["home_team"].astype(str).str.casefold().eq(row["home_team"].casefold()) &
           df["away_team"].astype(str).str.casefold().eq(row["away_team"].casefold()))
    df = df.loc[~key].copy()
    for col in row:
        if col not in df.columns:
            df[col] = pd.NA
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"UPDATED {path} rows={len(df)}")

# K1角球政策驗證：只報告，不補值、不估算。
k1 = pd.read_csv(ROOT / "data/leagues/k1/matches.csv")
daejeon = k1[k1["home_team"].astype(str).str.contains("Daejeon", case=False, na=False) |
             k1["away_team"].astype(str).str.contains("Daejeon", case=False, na=False)]
print(f"K1_DAEJEON_ROWS={len(daejeon)} K1_DAEJEON_CORNERS_COMPLETE={int(daejeon[['home_corners','away_corners']].notna().all(axis=1).sum())}")
print("POLICY=K1 missing HC/AC remain NULL; no estimates written")
