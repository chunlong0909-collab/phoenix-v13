"""ORBIFLOW adapter.

Valid ORBIFLOW JSON is optional. Missing/invalid data returns the original
expectations unchanged; mock data is only enabled explicitly for tests.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

MOCK_ORBIFLOW = {"team_flow": {"home": 1.1, "away": 1.8}, "press_intensity": {"home": 12, "away": 9}, "transition_score": 0.65}

def validate_orbiflow(data: Any) -> bool:
    try:
        return all(float(data["team_flow"][k]) >= 0 for k in ("home", "away")) and all(float(data["press_intensity"][k]) >= 0 for k in ("home", "away"))
    except (KeyError, TypeError, ValueError):
        return False

def load_orbiflow(path: str | Path | None = None, payload: dict | None = None, use_mock: bool = False) -> dict:
    data = payload
    source = "ORBIFLOW JSON"
    if data is None and path:
        try: data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError): data = None
    if data is None and use_mock:
        data, source = dict(MOCK_ORBIFLOW), "ORBIFLOW mock（測試）"
    if not validate_orbiflow(data):
        return {"available": False, "source": "未有有效ORBIFLOW資料", "data": None,
                "flow_correction": 0.0, "press_correction": 0.0}
    flow=(float(data["team_flow"]["away"])-float(data["team_flow"]["home"]))*0.15
    press=(float(data["press_intensity"]["home"])-float(data["press_intensity"]["away"]))*0.02
    return {"available": True, "source": source, "data": data,
            "flow_correction": flow, "press_correction": press}

def apply_orbiflow(home_exp: float, away_exp: float, orbiflow: dict, home_injury: float = 0.0, away_injury: float = 0.0) -> dict:
    """Return final expectations. No valid data means exact V1.0 passthrough."""
    if not orbiflow.get("available"):
        return {"home_exp_final": float(home_exp), "away_exp_final": float(away_exp), "total_exp_final": float(home_exp)+float(away_exp), "used": False}
    c=float(orbiflow.get("flow_correction",0))+float(orbiflow.get("press_correction",0))
    h=max(0.05,float(home_exp)+c+float(home_injury))
    a=max(0.05,float(away_exp)+c+float(away_injury))
    return {"home_exp_final": h, "away_exp_final": a, "total_exp_final": h+a, "used": True}

def orbiflow_summary(orbiflow: dict, result: dict) -> str:
    if not orbiflow.get("available"): return "ORBIFLOW流動：未有有效資料｜沿用V1.0原有預期"
    d=orbiflow["data"]
    return (f"ORBIFLOW流動：主隊 {float(d['team_flow']['home']):.1f} vs 客隊 {float(d['team_flow']['away']):.1f} | "
            f"壓迫指數 {float(d['press_intensity']['home']):.0f} vs {float(d['press_intensity']['away']):.0f} | "
            f"修正後預期：{result['home_exp_final']:.2f} - {result['away_exp_final']:.2f}")
