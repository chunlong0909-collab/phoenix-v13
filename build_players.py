import pandas as pd, random
teams=[{"team":f"Team_{i}","team_cn":f"球隊{i}","league":"World","team_cn_full":f"FC悉尼_{i}" if i==0 else f"西悉尼流浪隊_{i}" if i==1 else f"球隊{i}"} for i in range(5000)]
# 特別加返你嗰兩隊等佢搜到
teams[0]={"team":"FC悉尼","team_cn":"FC悉尼","league":"澳職"}
teams[1]={"team":"西悉尼流浪隊","team_cn":"西悉尼流浪隊","league":"澳職"}
pd.DataFrame(teams).to_csv("teams_world.csv",index=False)

players=[]
for i in range(120000):
    t = "FC悉尼" if i%3==0 else "西悉尼流浪隊" if i%3==1 else f"Team_{i%5000}"
    players.append({"team":t,"team_cn":t,"name":f"P{i}","name_cn":f"球員{i}","pos":random.choice(["GK","CB","CM","ST"]),"rating":random.randint(65,88)})
pd.DataFrame(players).to_csv("players_world.csv",index=False)

coaches=[{"team":"FC悉尼","team_cn":"FC悉尼","name":"Talay","name_cn":"塔萊","tactic":"4-3-3","win_rate":62},{"team":"西悉尼流浪隊","team_cn":"西悉尼流浪隊","name":"Stajcic","name_cn":"斯塔伊契奇","tactic":"4-4-2","win_rate":51}]
for i in range(2,5000):
    coaches.append({"team":f"Team_{i}","team_cn":f"Team_{i}","name":f"C{i}","name_cn":f"教練{i}","tactic":"4-3-3","win_rate":random.randint(40,70)})
pd.DataFrame(coaches).to_csv("coaches_world.csv",index=False)

refs=[{"name_cn":f"球證{i}","yellow_avg":round(random.uniform(3.5,6.0),1),"red_avg":0.18,"penalty_tendency":random.choice(["鬆","中","嚴"])} for i in range(1000)]
pd.DataFrame(refs).to_csv("refs_world.csv",index=False)
print("完成 5000隊 12萬球員")
