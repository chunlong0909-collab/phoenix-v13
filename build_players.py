import pandas as pd, random
teams = pd.read_csv("teams_world.csv")
players = []
pid=1
for _, t in teams.iterrows():
    for i in range(24):
        players.append({
            "player_id": f"P{pid:06d}",
            "team_key": t['key'],
            "team_cn": t['cn_name'],
            "league": t['league'],
            "name": f"Player{i+1}_{t['cn_name'][:2]}",
            "pos": random.choice(["GK","CB","CM","LW","ST"]),
            "age": random.randint(19,34),
            "rating": round(random.uniform(65,85),1),
            "market_value_m": round(random.uniform(0.5,30),1),
            "is_injured": 1 if random.random()<0.08 else 0
        })
        pid+=1
df = pd.DataFrame(players)
df.to_csv("players_world.csv", index=False, encoding="utf-8-sig")
print(f"完成 {len(df)} 球員")
