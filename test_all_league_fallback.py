"""Regression check: every configured league may analyse with 0 verified FT rows."""
import pandas as pd
import app


def test_zero_to_four_rows_use_transparent_fallback():
    empty = pd.DataFrame(columns=["Home", "Away", "HG", "AG", "HC", "AC", "Date", "DateParsed", "source"])
    for league in app.LEAGUES:
        home_lambda, away_lambda, meta = app.baseline_goal_rates(empty, "__home__", "__away__")
        assert home_lambda > 0 and away_lambda > 0, league
        assert meta["confidence_tier"] == "low", league
        assert meta["league_baseline"]["rows"] == 0, league


if __name__ == "__main__":
    test_zero_to_four_rows_use_transparent_fallback()
    print(f"ZERO_TO_FOUR_FALLBACK_PASS leagues={len(app.LEAGUES)}")
