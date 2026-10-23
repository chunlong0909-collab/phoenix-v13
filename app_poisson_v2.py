from __future__ import annotations

import sqlite3
import math
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).with_name("football_complete.db")
FOCUS_HOME = "South Melbourne FC"
FOCUS_AWAY = "Sydney United 58 FC"


def poisson_pmf(k: int, lam: float) -> float:
    """Poisson PMF using only the Python standard library."""
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def db_connect(path: Path = DB_PATH):
    conn = sqlite3.connect(str(path), timeout=30, check_same_thread=False)
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def load_teams(path: Path = DB_PATH) -> pd.DataFrame:
    with db_connect(path) as conn:
        df = pd.read_sql_query("SELECT id,en_name,zh_name FROM teams ORDER BY en_name", conn)
    df["display_name"] = df["zh_name"].fillna(df["en_name"])
    return df


def league_options(path: Path = DB_PATH) -> pd.DataFrame:
    with db_connect(path) as conn:
        return pd.read_sql_query(
            "SELECT league_id, COUNT(*) AS fixtures, MIN(date) AS first_date, MAX(date) AS last_date "
            "FROM fixtures WHERE ft_home IS NOT NULL AND ft_away IS NOT NULL "
            "GROUP BY league_id ORDER BY fixtures DESC", conn
        )


def calculate_poisson_metrics(path: Path, league_id: int):
    with db_connect(path) as conn:
        df = pd.read_sql_query(
            "SELECT home_id,away_id,ft_home,ft_away FROM fixtures "
            "WHERE league_id=? AND ft_home IS NOT NULL AND ft_away IS NOT NULL",
            conn, params=(int(league_id),),
        )
    if len(df) < 5:
        return None
    avg_home = max(float(df.ft_home.mean()), 1e-6)
    avg_away = max(float(df.ft_away.mean()), 1e-6)
    return {
        "sample": len(df), "avg_home": avg_home, "avg_away": avg_away,
        "home_att": (df.groupby("home_id").ft_home.mean() / avg_home).to_dict(),
        "home_def": (df.groupby("home_id").ft_away.mean() / avg_away).to_dict(),
        "away_att": (df.groupby("away_id").ft_away.mean() / avg_away).to_dict(),
        "away_def": (df.groupby("away_id").ft_home.mean() / avg_home).to_dict(),
    }


def predict_match(metrics, home_id: int, away_id: int, max_goals: int = 8):
    if metrics is None:
        return None
    h_att = metrics["home_att"].get(home_id, 1.0)
    h_def = metrics["home_def"].get(home_id, 1.0)
    a_att = metrics["away_att"].get(away_id, 1.0)
    a_def = metrics["away_def"].get(away_id, 1.0)
    lambda_home = h_att * a_def * metrics["avg_home"]
    lambda_away = a_att * h_def * metrics["avg_away"]
    matrix = np.outer(
        [poisson_pmf(k, lambda_home) for k in range(max_goals + 1)],
        [poisson_pmf(k, lambda_away) for k in range(max_goals + 1)],
    )
    # Rows are home goals and columns are away goals: h>a is upper triangle.
    home_win = float(np.triu(matrix, 1).sum())
    draw = float(np.trace(matrix))
    away_win = float(np.tril(matrix, -1).sum())
    under25 = float(sum(matrix[h, a] for h in range(max_goals + 1) for a in range(max_goals + 1) if h + a <= 2))
    return {"lambda_home": lambda_home, "lambda_away": lambda_away, "matrix": matrix,
            "home_win": home_win, "draw": draw, "away_win": away_win,
            "under25": under25, "over25": 1.0 - under25}


def second_half_metrics(path: Path, team_id: int):
    with db_connect(path) as conn:
        row = conn.execute(
            "SELECT SUM(CASE WHEN home_id=? AND ft_away>ht_away THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN away_id=? AND ft_home>ht_home THEN 1 ELSE 0 END), COUNT(*) "
            "FROM fixtures WHERE (home_id=? OR away_id=?) "
            "AND ft_home IS NOT NULL AND ft_away IS NOT NULL "
            "AND ht_home IS NOT NULL AND ht_away IS NOT NULL",
            (team_id, team_id, team_id, team_id),
        ).fetchone()
    if not row or not row[2]:
        return 0.0, 0
    return float((row[0] or 0) + (row[1] or 0)) / row[2], int(row[2])


def team_history(path: Path, team_ids):
    marks = ",".join("?" for _ in team_ids)
    with db_connect(path) as conn:
        return pd.read_sql_query(
            f"SELECT f.date, h.zh_name AS home_zh, h.en_name AS home_en, "
            f"a.zh_name AS away_zh, a.en_name AS away_en, f.ft_home, f.ft_away, "
            f"f.ht_home, f.ht_away, f.corners_home, f.corners_away, f.league_id "
            f"FROM fixtures f JOIN teams h ON h.id=f.home_id JOIN teams a ON a.id=f.away_id "
            f"WHERE f.home_id IN ({marks}) OR f.away_id IN ({marks}) "
            f"ORDER BY f.date DESC", conn, params=tuple(team_ids) * 2,
        )


st.set_page_config(page_title="泊松足球分析 V2", layout="wide")
st.title("⚽ 泊松足球分析 V2")
st.caption("獨立驗證版：使用 football_complete.db；team_values 缺失時不會估算或報錯。")

if not DB_PATH.exists():
    st.error(f"找不到資料庫：{DB_PATH}")
    st.stop()

try:
    teams = load_teams()
    leagues = league_options()
except Exception as exc:
    st.error(f"資料庫讀取失敗：{exc}")
    st.stop()

focus_home = teams[teams.en_name.str.contains("South Melbourne", case=False, na=False)]
focus_away = teams[teams.en_name.str.contains("Sydney United", case=False, na=False)]
if focus_home.empty or focus_away.empty:
    st.warning("找不到焦點球隊，請先確認 teams 表的正式英文名稱。")

with st.sidebar:
    st.header("比賽設定")
    if st.button("一鍵載入：南墨爾本 vs 悉尼聯58"):
        if not focus_home.empty:
            st.session_state.home_id = int(focus_home.iloc[0].id)
        if not focus_away.empty:
            st.session_state.away_id = int(focus_away.iloc[0].id)
    league_id = st.selectbox("聯賽內部 ID", leagues.league_id.tolist() if not leagues.empty else [], format_func=lambda x: f"{x}（{int(leagues.loc[leagues.league_id==x,'fixtures'].iloc[0])}場）")

home_default = int(st.session_state.get("home_id", teams.iloc[0].id))
away_default = int(st.session_state.get("away_id", teams.iloc[min(1, len(teams)-1)].id))
home_id = st.selectbox("主隊", teams.id.tolist(), index=teams.id.tolist().index(home_default) if home_default in teams.id.tolist() else 0, format_func=lambda x: teams.loc[teams.id==x, "display_name"].iloc[0])
away_id = st.selectbox("客隊", teams.id.tolist(), index=teams.id.tolist().index(away_default) if away_default in teams.id.tolist() else min(1, len(teams)-1), format_func=lambda x: teams.loc[teams.id==x, "display_name"].iloc[0])

home_label = teams.loc[teams.id==home_id, "display_name"].iloc[0]
away_label = teams.loc[teams.id==away_id, "display_name"].iloc[0]
metrics = calculate_poisson_metrics(DB_PATH, int(league_id))
prediction = predict_match(metrics, int(home_id), int(away_id))

if prediction is None:
    st.warning("此聯賽少於5場已完賽資料，暫停輸出模型機率，避免虛構精確度。")
else:
    st.subheader(f"{home_label} vs {away_label}")
    c1, c2, c3 = st.columns(3)
    c1.metric("主隊預期入球", f"{prediction['lambda_home']:.2f}")
    c2.metric("和局機率", f"{prediction['draw']*100:.1f}%")
    c3.metric("客隊預期入球", f"{prediction['lambda_away']:.2f}")
    st.write(f"樣本：{metrics['sample']} 場；大 2.5：{prediction['over25']*100:.1f}%；細 2.5：{prediction['under25']*100:.1f}%")
    st.write(f"主勝：{prediction['home_win']*100:.1f}%　和局：{prediction['draw']*100:.1f}%　客勝：{prediction['away_win']*100:.1f}%")
    sh_h, n_h = second_half_metrics(DB_PATH, int(home_id)); sh_a, n_a = second_half_metrics(DB_PATH, int(away_id))
    st.info(f"下半場失波率：{home_label} {sh_h*100:.1f}%（{n_h}場）；{away_label} {sh_a*100:.1f}%（{n_a}場）。")

st.divider()
st.subheader("兩隊已保存的真實完賽明細")
history = team_history(DB_PATH, [int(home_id), int(away_id)])
st.caption(f"共 {len(history)} 場相關歷史記錄；只顯示資料庫已存在的賽果，不補造資料。")
st.dataframe(history, use_container_width=True, hide_index=True)
