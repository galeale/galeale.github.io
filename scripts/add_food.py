"""Add the extra food each conference trip needed, beyond normal training, to cycling-data.json.

extra km   = trip km - (average daily km ridden in the 365 days before the trip) x riding days
kcal/km    = the trip's own Strava calories / km where every leg has them, else the median over all rides
food CO2e  = extra km x kcal/km x intensity of ride food: all extra calories counted as carbohydrates and sugar,
             an equal mix of wheat (pasta, bread), cane sugar and beet sugar (gummies), Poore & Nemecek 2018 via
             Our World in Data, kg CO2e per 1000 kcal: wheat & rye 0.59, cane sugar 0.91, beet sugar 0.52
Commuting needs no extra food (it replaces training), so it gets none.

Usage: python -I add_food.py <activities.csv> <cycling-data.json>
"""
import csv, json, sys, datetime, statistics

DIET_G_PER_KCAL = (0.59 + 0.91 + 0.52) / 3  # g CO2e per kcal (= kg per 1000 kcal)
MON = {'gen': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'mag': 5, 'giu': 6, 'lug': 7, 'ago': 8, 'set': 9, 'ott': 10, 'nov': 11, 'dic': 12}

rows = list(csv.reader(open(sys.argv[1], encoding="utf-8")))
col = {}
for i, c in enumerate(rows[0]):
    col.setdefault(c, []).append(i)

def num(s):
    s = s.strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return float(s.replace(".", "").replace(",", "."))

rides = []
for r in rows[1:]:
    if r[col["Tipo attività"][0]] not in ("Ciclismo", "Pedalata virtuale"):
        continue
    d, m, y = r[col["Data dell’attività"][0]].split(",")[0].split()
    rides.append(dict(date=datetime.date(int(y), MON[m], int(d)), name=r[col["Nome attività"][0]],
                      km=(num(r[col["Distanza"][1]]) or 0) / 1000, kcal=num(r[col["Calorie"][0]])))

kpk_all = statistics.median(x["kcal"] / x["km"] for x in rides if x["kcal"] and x["km"] > 20)

data = json.load(open(sys.argv[2]))
for t in data["trips"]:
    start = datetime.date.fromisoformat(t["start"])
    before = [x for x in rides if start - datetime.timedelta(days=365) <= x["date"] < start]
    base = sum(x["km"] for x in before) / 365
    legs = [x for x in rides if t["start"] <= x["date"].isoformat() <= t["end"] and "biking" in x["name"].lower()]
    if legs and all(x["kcal"] for x in legs):
        kpk, src = sum(x["kcal"] for x in legs) / sum(x["km"] for x in legs), "trip"
    else:
        kpk, src = kpk_all, "median"
    extra_km = max(0.0, t["km"] - base * t["days"])
    t.update(base_km_day=round(base, 1), extra_km=round(extra_km), kcal_per_km=round(kpk, 1), kcal_source=src,
             food_kcal=round(extra_km * kpk), food_kg=round(extra_km * kpk * DIET_G_PER_KCAL / 1000, 1))
    print(t["event"], {k: t[k] for k in ("km", "days", "base_km_day", "extra_km", "kcal_per_km", "kcal_source", "food_kcal", "food_kg")})
data["food"] = dict(diet_g_per_kcal=DIET_G_PER_KCAL, median_kcal_per_km=round(kpk_all, 1))
# EcoPassenger (UIC / ifeu), queried 2 Nov 2026, kg CO2 per passenger.
# Settings: car driven alone (1 passenger), flights "with climate factor", rail national production mix.
# Car figures are EcoPassenger's 1.5-passenger defaults x 1.5 (checked: Vienna 61.3 -> 91.9 at 1 passenger);
# plane = aircraft with climate factor + car to/from the airport, driven alone.
ECO = {"netsci2023": dict(train=15.9, car=91.9, plane=127.1 + 5.8),
       "cs2ita2025": dict(train=9.3 + 4.1, car=(15.3 + 11.0) * 1.5),   # Mestre-Trento + Trento-Verona
       "netsci2025": dict(train=38.0, car=100.4 * 1.5, plane=194.7 + 16.5 * 1.5),
       "c72h2026": dict(train=35.2, car=141.3 * 1.5, plane=242.6 + 5.0 * 1.5)}
for t in data["trips"]:
    t["eco"] = {k: round(v, 1) for k, v in ECO[t["id"]].items()}
data["commute"]["eco_leg"] = dict(train=1.4, car=round(4.3 * 1.5, 2))  # Venezia Mestre - Padova, one way
print("median kcal/km", round(kpk_all, 1))
json.dump(data, open(sys.argv[2], "w"), separators=(",", ":"))
