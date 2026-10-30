from team_registry_v2 import directory_for, resolve
import app


def check(league, home, away):
    directory = directory_for(league)
    assert home in directory, (league, home, directory[:10])
    assert away in directory, (league, away, directory[:10])
    h = resolve(league, home)
    a = resolve(league, away)
    assert h and a, (league, home, away)
    assert h["team_id"] != a["team_id"], (league, h, a)
    return len(directory), h["team_id"], a["team_id"]


def test_cross_league_registry():
    cases = [
        ("意大利甲組聯賽", "Frosinone Calcio", "US Lecce"),
        ("日本職業聯賽", "Gamba Osaka", "Vissel Kobe"),
        ("南韓職業聯賽", "FC Seoul", "Jeonbuk Hyundai Motors"),
        ("英格蘭超級聯賽", "Arsenal", "Liverpool"),
        ("沙特職業聯賽", "Al Hilal", "Al Ahli"),
    ]
    result = {league: check(league, home, away) for league, home, away in cases}
    assert all(count > 0 for count, _, _ in result.values())
    return result


def test_long_league_labels_and_history_aliases():
    cases = [
        ("日本職業聯賽", "Gamba Osaka", "Vissel Kobe"),
        ("南韓職業聯賽", "FC Seoul", "Jeonbuk Hyundai Motors"),
        ("日本乙組聯賽", "JEF United Chiba", "FC Imabari"),
        ("意大利甲組聯賽", "Frosinone Calcio", "US Lecce"),
    ]
    for league, home, away in cases:
        matches = app.all_saved_matches(league)
        assert len(matches) > 0, (league, "long label returned no FT rows")
        assert app.history_team_label(league, home, matches)
        assert app.history_team_label(league, away, matches)


if __name__ == "__main__":
    print(test_cross_league_registry())
